// ╔══════════════════════════════════════════════════════════════╗
// ║  Phish Carnage — Background Service Worker v2.0              ║
// ║  Smart caching · Push notifications · Health probe           ║
// ╚══════════════════════════════════════════════════════════════╝

// ── Config ────────────────────────────────────────────────────────
const API_BASE   = 'http://127.0.0.1:5000';
const CACHE_TTL  = 30_000;   // ms — don't re-scan same URL within 30 s
const HEALTH_INT = 15_000;   // ms — probe backend every 15 s

// ── In-memory state ───────────────────────────────────────────────
const resultCache  = new Map();   // url → { data, timestamp }
const pageSignalMap = new Map();  // url → [signals]
let backendOnline  = true;

// ══════════════════════════════════════════════════════════════════
// Backend health probe
// ══════════════════════════════════════════════════════════════════
async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`, { method: 'GET' });
        backendOnline = res.ok;
    } catch {
        backendOnline = false;
    }
    // Notify popup if it's open
    chrome.storage.local.set({ backendOnline });
}

checkBackendHealth();
setInterval(checkBackendHealth, HEALTH_INT);

// ══════════════════════════════════════════════════════════════════
// Listen for page signals from content.js
// ══════════════════════════════════════════════════════════════════
chrome.runtime.onMessage.addListener((msg, sender) => {
    if (msg.type !== 'PAGE_SIGNALS') return;

    const url = msg.url;
    const existing = pageSignalMap.get(url) || [];
    const merged   = [...new Set([...existing, ...msg.signals])];
    pageSignalMap.set(url, merged);

    // Invalidate cache so next scan picks up the new signals
    resultCache.delete(url);

    // Kick off a fresh scan with the new signals if tab is known
    if (sender.tab?.id) {
        scanUrl(url, sender.tab.id);
    }
});

// ══════════════════════════════════════════════════════════════════
// Tab event hooks
// ══════════════════════════════════════════════════════════════════
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        if (isInternalUrl(tab.url)) return;
        scanUrl(tab.url, tabId);
    }
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
    chrome.tabs.get(tabId, (tab) => {
        if (tab.url && !isInternalUrl(tab.url)) {
            scanUrl(tab.url, tabId);
        }
    });
});

chrome.tabs.onRemoved.addListener((tabId) => {
    chrome.storage.local.remove(`scan_${tabId}`);
});

// ══════════════════════════════════════════════════════════════════
// Core scan function
// ══════════════════════════════════════════════════════════════════
async function scanUrl(url, tabId) {
    if (!backendOnline) {
        setOfflineBadge(tabId);
        return;
    }

    // ── Cache hit ────────────────────────────────────────────────
    const cached = resultCache.get(url);
    if (cached && (Date.now() - cached.timestamp) < CACHE_TTL) {
        applyResult(tabId, url, cached.data);
        return;
    }

    // ── Loading badge ────────────────────────────────────────────
    chrome.action.setBadgeText({ text: '···', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#3a3a3a', tabId });

    // ── Merge any page signals collected by content.js ───────────
    const pageSignals = pageSignalMap.get(url) || [];

    try {
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ url, page_signals: pageSignals })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Attach extra metadata for popup
        data.scannedAt    = Date.now();
        data.pageSignals  = pageSignals;

        // Cache the result
        resultCache.set(url, { data, timestamp: Date.now() });

        applyResult(tabId, url, data);

    } catch (err) {
        console.error('[PhishCarnage] Scan error:', err);
        chrome.action.setBadgeText({ text: '!', tabId });
        chrome.action.setBadgeBackgroundColor({ color: '#e74c3c', tabId });
    }
}

// ══════════════════════════════════════════════════════════════════
// Apply scan result: badge + storage + notifications
// ══════════════════════════════════════════════════════════════════
function applyResult(tabId, url, data) {
    updateBadge(tabId, data);

    chrome.storage.local.set({ [`scan_${tabId}`]: data });

    // Critical notification
    if (data.level === 'Critical') {
        sendCriticalNotification(url, data.score);
        // Tell content script to show in-page banner
        chrome.tabs.sendMessage(tabId, {
            type:  'SHOW_WARNING',
            level: 'Critical',
            score: data.score
        }).catch(() => {}); // tab may not have content script yet
    }
}

// ══════════════════════════════════════════════════════════════════
// Badge helpers
// ══════════════════════════════════════════════════════════════════
function updateBadge(tabId, data) {
    const level = (data.level || '').toLowerCase();
    const score = data.score ?? 0;

    const colorMap = {
        low:      '#27ae60',
        medium:   '#e67e22',
        high:     '#c0392b',
        critical: '#7f0000',
    };

    const color = colorMap[level] || '#555';
    const text  = score === 0 ? 'OK' : score.toString();

    chrome.action.setBadgeText({ text, tabId });
    chrome.action.setBadgeBackgroundColor({ color, tabId });
}

function setOfflineBadge(tabId) {
    chrome.action.setBadgeText({ text: 'OFF', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#555555', tabId });
}

// ══════════════════════════════════════════════════════════════════
// Push notification for Critical threats
// ══════════════════════════════════════════════════════════════════
function sendCriticalNotification(url, score) {
    // Throttle: don't spam same domain
    const domain = (() => {
        try { return new URL(url).hostname; } catch { return url; }
    })();

    const key = `notif_${domain}`;
    chrome.storage.local.get([key], (result) => {
        const lastSent = result[key] || 0;
        if (Date.now() - lastSent < 60_000) return; // once per minute per domain

        chrome.storage.local.set({ [key]: Date.now() });

        chrome.notifications.create({
            type:    'basic',
            iconUrl: 'icons/icon128.png',
            title:   '🚨 CRITICAL PHISHING THREAT',
            message: `Risk Score: ${score}/100\n${domain}\nDo NOT enter any credentials on this page!`,
            priority: 2,
            requireInteraction: true
        });
    });
}

// ══════════════════════════════════════════════════════════════════
// Utility
// ══════════════════════════════════════════════════════════════════
function isInternalUrl(url) {
    return url.startsWith('chrome://') ||
           url.startsWith('chrome-extension://') ||
           url.startsWith('about:') ||
           url.startsWith('edge://');
}
