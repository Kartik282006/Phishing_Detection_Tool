// ╔══════════════════════════════════════════════════════════════╗
// ║  Phish Carnage — Content Script (Real-Time Page Inspector)   ║
// ╚══════════════════════════════════════════════════════════════╝
// Injected into every page. Detects in-page phishing signals and
// reports them back to background.js for score merge.

(function () {
    'use strict';

    const pageSignals = [];

    // ── Brand keywords we expect to match their real domains ──────
    const BRAND_DOMAIN_MAP = {
        paypal: 'paypal.com',
        apple: 'apple.com',
        microsoft: 'microsoft.com',
        google: 'google.com',
        amazon: 'amazon.com',
        netflix: 'netflix.com',
        facebook: 'facebook.com',
        instagram: 'instagram.com',
        linkedin: 'linkedin.com',
        twitter: 'twitter.com',
        ebay: 'ebay.com',
        yahoo: 'yahoo.com',
        chase: 'chase.com',
        wellsfargo: 'wellsfargo.com',
        hsbc: 'hsbc.com',
    };

    const hostname = window.location.hostname.toLowerCase();
    const pageTitle = document.title.toLowerCase();
    const bodyText = (document.body?.innerText || '').toLowerCase().slice(0, 4000);

    // ── Signal 1: Title/body brand mention but wrong domain ───────
    for (const [brand, realDomain] of Object.entries(BRAND_DOMAIN_MAP)) {
        const titleHit = pageTitle.includes(brand);
        const bodyHit = bodyText.includes(brand);
        const onRealDomain = hostname.endsWith(realDomain);

        if ((titleHit || bodyHit) && !onRealDomain) {
            pageSignals.push(`Brand impersonation in page: "${brand}" content on ${hostname}`);
        }
    }

    // ── Signal 2: Password field + suspicious action domain ───────
    const passwordFields = document.querySelectorAll('input[type="password"]');
    if (passwordFields.length > 0) {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const actionUrl = form.action || '';
            const actionHostname = (() => {
                try { return new URL(actionUrl).hostname; } catch { return hostname; }
            })();
            // If form submits to a different domain — suspicious
            if (actionHostname && actionHostname !== hostname) {
                pageSignals.push(`Password form submits to external domain: ${actionHostname}`);
            }
        });
        // Password field on HTTP page
        if (window.location.protocol === 'http:') {
            pageSignals.push('Password field on non-HTTPS page (credential theft risk)');
        }
    }

    // ── Signal 3: Fullscreen/large iframe overlay (fake login) ───
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
        const rect = iframe.getBoundingClientRect();
        const vpW = window.innerWidth;
        const vpH = window.innerHeight;
        // Covers >70% of viewport
        if (rect.width > vpW * 0.7 && rect.height > vpH * 0.7) {
            const src = iframe.src || iframe.getAttribute('srcdoc') || '';
            if (src && !src.startsWith(window.location.origin)) {
                pageSignals.push(`Fullscreen cross-origin iframe detected (possible fake login overlay)`);
            }
        }
    });

    // ── Signal 4: Suspicious form with urgency text ───────────────
    const urgencyWords = ['urgent', 'immediately', 'verify now', 'account suspended',
        'unusual activity', 'confirm your identity', 'update payment'];
    const pageHasUrgency = urgencyWords.some(w => bodyText.includes(w));
    if (pageHasUrgency && passwordFields.length > 0) {
        pageSignals.push('Urgency language combined with credential form detected');
    }

    // ── Signal 5: Hidden redirect / meta refresh ──────────────────
    const metaRefresh = document.querySelector('meta[http-equiv="refresh"]');
    if (metaRefresh) {
        const content = metaRefresh.getAttribute('content') || '';
        const urlMatch = content.match(/url=([^\s"']+)/i);
        if (urlMatch) {
            pageSignals.push(`Meta-refresh redirect to: ${urlMatch[1].slice(0, 80)}`);
        }
    }

    // ── Report signals to background ─────────────────────────────
    if (pageSignals.length > 0) {
        chrome.runtime.sendMessage({
            type: 'PAGE_SIGNALS',
            url: window.location.href,
            signals: pageSignals
        });
    }

    // ── Inject critical warning banner if told to ─────────────────
    chrome.runtime.onMessage.addListener((msg) => {
        if (msg.type === 'SHOW_WARNING' && msg.level === 'Critical') {
            showCriticalBanner(msg.score);
        }
    });

    function showCriticalBanner(score) {
        if (document.getElementById('phishcarnage-warning')) return; // already shown

        const banner = document.createElement('div');
        banner.id = 'phishcarnage-warning';
        banner.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 2147483647;
            background: linear-gradient(135deg, #7f0000, #c0392b);
            color: #fff;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
            animation: phishSlideDown 0.4s ease;
        `;

        const style = document.createElement('style');
        style.textContent = `
            @keyframes phishSlideDown {
                from { transform: translateY(-100%); opacity: 0; }
                to   { transform: translateY(0);    opacity: 1; }
            }
            #phishcarnage-warning button {
                margin-left: auto;
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.4);
                color: #fff;
                padding: 4px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 13px;
            }
            #phishcarnage-warning button:hover { background: rgba(255,255,255,0.35); }
        `;
        document.head.appendChild(style);

        banner.innerHTML = `
            <span style="font-size:20px;">🚨</span>
            <strong>PHISHING ALERT</strong>
            <span>— Risk Score: <strong>${score}/100</strong>. This page may be attempting to steal your credentials. Do NOT enter any information.</span>
            <button id="phishcarnage-dismiss">Dismiss</button>
        `;

        document.body.prepend(banner);

        document.getElementById('phishcarnage-dismiss').addEventListener('click', () => {
            banner.remove();
        });
    }
})();
