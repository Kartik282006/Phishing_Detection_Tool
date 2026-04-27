// ╔══════════════════════════════════════════════════════════════╗
// ║  Phish Carnage — Popup Script v2.0                           ║
// ╚══════════════════════════════════════════════════════════════╝

// ── DOM refs ──────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const loadingState   = $('loadingState');
const errorState     = $('errorState');
const resultCard     = $('resultCard');
const offlineBanner  = $('offlineBanner');
const statusDot      = $('statusDot');
const statusLabel    = $('statusLabel');
const currentUrlEl   = $('currentUrl');
const urlLockEl      = $('urlLock');
const scoreRow       = $('scoreRow');
const scoreValue     = $('scoreValue');
const levelBadge     = $('levelBadge');
const ringCircle     = $('ringCircle');
const scanDomain     = $('scanDomain');
const scanTime       = $('scanTime');
const indicatorList  = $('indicatorList');
const pageSignalsWrap = $('pageSignalsWrap');
const signalList     = $('signalList');
const killChainWrap  = $('killChainWrap');
const kcTags         = $('kcTags');

// ── Constants ─────────────────────────────────────────────────────
const API_BASE   = 'http://127.0.0.1:5000';
const RING_CIRC  = 163;   // 2π × r(26) ≈ 163

// ══════════════════════════════════════════════════════════════════
// On load
// ══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initBackendStatus();
    loadCurrentTab();
});

// ── Backend status ────────────────────────────────────────────────
function initBackendStatus() {
    chrome.storage.local.get(['backendOnline'], ({ backendOnline }) => {
        setBackendStatus(backendOnline !== false);
    });
    // Also listen for live updates from background
    chrome.storage.onChanged.addListener((changes) => {
        if ('backendOnline' in changes) {
            setBackendStatus(changes.backendOnline.newValue);
        }
    });
}

function setBackendStatus(online) {
    if (online) {
        statusDot.classList.remove('offline');
        statusLabel.textContent = 'Live';
        statusLabel.style.color = '#3fb950';
        offlineBanner.classList.remove('show');
    } else {
        statusDot.classList.add('offline');
        statusLabel.textContent = 'Offline';
        statusLabel.style.color = '#8b949e';
        offlineBanner.classList.add('show');
    }
}

// ── Load current tab ──────────────────────────────────────────────
function loadCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tab = tabs[0];
        if (!tab) { showError('No active tab found'); return; }

        // Show URL in bar
        displayUrl(tab.url);

        // Try cached result first
        chrome.storage.local.get([`scan_${tab.id}`], (result) => {
            const data = result[`scan_${tab.id}`];
            if (data) {
                showResult(data, tab.url);
            } else {
                // Nothing cached yet — live scan
                doScan(tab.url, tab.id);
            }
        });
    });
}

// ── Display URL in bar ────────────────────────────────────────────
function displayUrl(url) {
    try {
        const u = new URL(url);
        currentUrlEl.textContent = u.hostname + (u.pathname !== '/' ? u.pathname : '');
        urlLockEl.textContent = u.protocol === 'https:' ? '🔒' : '🔓';
    } catch {
        currentUrlEl.textContent = url.slice(0, 50);
    }
}

// ── Live scan ─────────────────────────────────────────────────────
function doScan(url, tabId) {
    showLoading();
    fetch(`${API_BASE}/api/analyze`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ url })
    })
    .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })
    .then(data => {
        data.scannedAt = Date.now();
        // Merge any page signals from cache
        chrome.storage.local.get([`scan_${tabId}`], (stored) => {
            const prev = stored[`scan_${tabId}`] || {};
            data.pageSignals = data.pageSignals || prev.pageSignals || [];
            chrome.storage.local.set({ [`scan_${tabId}`]: data });
            showResult(data, url);
        });
    })
    .catch(err => {
        showError(err.message);
    });
}

// ── Show result ───────────────────────────────────────────────────
function showResult(data, url) {
    loadingState.style.display = 'none';
    errorState.style.display   = 'none';
    resultCard.style.display   = 'block';

    const level = (data.level || 'low').toLowerCase();
    const score = data.score ?? 0;

    // Score ring
    const offset = RING_CIRC - (score / 100) * RING_CIRC;
    ringCircle.style.strokeDashoffset = offset;
    ringCircle.className = `fg-circle ring-${level}`;
    scoreValue.textContent = score;

    // Score card border/bg
    scoreRow.className = `score-row ${level}`;

    // Badge
    levelBadge.textContent = data.level;
    levelBadge.className = `level-badge badge-${level}`;

    // Domain + time
    try {
        scanDomain.textContent = new URL(url || data.url).hostname;
    } catch {
        scanDomain.textContent = data.url || url || '';
    }
    scanTime.textContent = data.scannedAt
        ? `Scanned ${timeAgo(data.scannedAt)}`
        : 'Just now';

    // URL Indicators
    buildIndicators(data.indicators || []);

    // Page signals
    buildPageSignals(data.pageSignals || []);

    // Kill chain
    buildKillChain(data.kill_chain || []);
}

// ── UI builder helpers ────────────────────────────────────────────
function buildIndicators(indicators) {
    if (indicators.length === 0) {
        indicatorList.innerHTML =
            `<div class="safe-msg">✅ No suspicious URL indicators found.</div>`;
    } else {
        const ul = document.createElement('ul');
        indicators.forEach(ind => {
            const li = document.createElement('li');
            li.innerHTML = `<span>⚠️</span><span>${esc(ind)}</span>`;
            ul.appendChild(li);
        });
        indicatorList.innerHTML = '';
        indicatorList.appendChild(ul);
    }
}

function buildPageSignals(signals) {
    if (!signals || signals.length === 0) {
        pageSignalsWrap.style.display = 'none';
        return;
    }
    pageSignalsWrap.style.display = 'block';
    signalList.innerHTML = '';
    signals.forEach(sig => {
        const li = document.createElement('li');
        li.innerHTML = `<span>🔍</span><span>${esc(sig)}</span>`;
        signalList.appendChild(li);
    });
}

function buildKillChain(chain) {
    if (!chain || chain.length === 0) {
        killChainWrap.style.display = 'none';
        return;
    }
    killChainWrap.style.display = 'block';
    kcTags.innerHTML = '';
    chain.forEach(technique => {
        const tag = document.createElement('span');
        tag.className = 'kc-tag';
        tag.textContent = technique;
        kcTags.appendChild(tag);
    });
}

// ── State helpers ─────────────────────────────────────────────────
function showLoading() {
    loadingState.style.display = 'flex';
    errorState.style.display   = 'none';
    resultCard.style.display   = 'none';
}

function showError(msg) {
    loadingState.style.display = 'none';
    errorState.style.display   = 'block';
    resultCard.style.display   = 'none';
    $('errMsg').textContent = msg || 'Unknown error';
}

// ── Time helper ───────────────────────────────────────────────────
function timeAgo(ts) {
    const sec = Math.floor((Date.now() - ts) / 1000);
    if (sec < 5)  return 'just now';
    if (sec < 60) return `${sec}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    return `${Math.floor(sec / 3600)}h ago`;
}

// ── XSS-safe escape ───────────────────────────────────────────────
function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ══════════════════════════════════════════════════════════════════
// Button actions
// ══════════════════════════════════════════════════════════════════
$('scanButton').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tab = tabs[0];
        if (!tab) return;
        // Clear cached result so we get a fresh scan
        chrome.storage.local.remove(`scan_${tab.id}`, () => {
            doScan(tab.url, tab.id);
        });
    });
});

$('dashboardButton').addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://127.0.0.1:5000' });
});
