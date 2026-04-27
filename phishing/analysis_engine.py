"""
Heuristic URL analysis engine for phishing detection — v2.0
Assigns risk score and maps to Cyber Kill Chain techniques.
New in v2: punycode/IDN, excessive subdomains, long URL,
           HTTP-only, hyphen abuse, numeric domain, page_signals.
"""

import ipaddress
import re
from urllib.parse import urlparse

# ---------- Heuristic Rule Tables ----------

SUSPICIOUS_TLDS = {
    'tk', 'ml', 'ga', 'cf', 'click', 'download', 'review', 'work', 'date',
    'faith', 'men', 'loan', 'win', 'bid', 'trade', 'webcam', 'science',
    'gq', 'pw', 'top', 'buzz', 'info', 'xyz', 'biz', 'online', 'site',
}

URL_SHORTENERS = {
    'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
    'tiny.cc', 'tr.im', 'cli.gs', 'v.gd', 'short.link', 'lnkd.in',
    't.co', 'rb.gy', 'cutt.ly', 'shorturl.at',
}

BRAND_KEYWORDS = {
    'paypal', 'apple', 'microsoft', 'google', 'amazon', 'netflix',
    'facebook', 'instagram', 'whatsapp', 'linkedin', 'twitter',
    'ebay', 'yahoo', 'bank', 'wellsfargo', 'chase', 'hsbc',
    'dropbox', 'icloud', 'outlook', 'office365', 'docusign',
}

SOCIAL_ENG_KEYWORDS = {
    'urgent', 'verify', 'login', 'signin', 'update', 'confirm',
    'account', 'secure', 'unusual', 'suspended', 'blocked', 'alert',
    'restore', 'validate', 'reactivate', 'security', 'required',
    'expire', 'limited', 'access', 'password', 'credential',
}

# Mapping rule categories → Kill Chain techniques
KILL_CHAIN_MAP = {
    'ip_based':           'Evasion',
    'suspicious_tld':     'Evasion',
    'url_shortener':      'Evasion',
    'punycode':           'Evasion / Domain Spoofing',
    'brand_spoofing':     'Impersonation / Brand Spoofing',
    'social_engineering': 'Credential Harvesting',
    'page_signal':        'Active Reconnaissance / Credential Harvesting',
}

# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def is_ip_address(hostname: str) -> bool:
    """Return True if hostname is a bare IP address."""
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def strip_port(netloc: str) -> str:
    """Remove port number from netloc string."""
    if ':' in netloc and not netloc.startswith('['):
        return netloc.rsplit(':', 1)[0]
    return netloc


# ────────────────────────────────────────────────────────────────────
# Main analysis function
# ────────────────────────────────────────────────────────────────────

def analyze_url(url: str, page_signals: list = None) -> dict:
    """
    Analyse a URL and optional in-page signals (from the content script).

    Returns:
        dict with keys: url, score, level, indicators, kill_chain
    """
    if page_signals is None:
        page_signals = []

    parsed   = urlparse(url if '://' in url else 'https://' + url)
    netloc   = parsed.netloc or parsed.path
    hostname = strip_port(netloc).lower()
    lower_url = url.lower()

    indicators     = []
    kill_chain_set = set()
    score          = 0

    # ── Rule 1: IP-based URL (+30) ───────────────────────────────
    if is_ip_address(hostname):
        indicators.append('IP-based hostname (no domain)')
        kill_chain_set.add(KILL_CHAIN_MAP['ip_based'])
        score += 30

    # ── Rule 2: Suspicious TLD (+20) ─────────────────────────────
    tld = hostname.split('.')[-1] if '.' in hostname else ''
    if tld in SUSPICIOUS_TLDS:
        indicators.append(f'Suspicious TLD: .{tld}')
        kill_chain_set.add(KILL_CHAIN_MAP['suspicious_tld'])
        score += 20

    # ── Rule 3: URL shortener (+15) ──────────────────────────────
    domain_parts = hostname.split('.')
    root_domain  = '.'.join(domain_parts[-2:]) if len(domain_parts) >= 2 else hostname
    if root_domain in URL_SHORTENERS:
        indicators.append(f'URL shortener detected: {root_domain}')
        kill_chain_set.add(KILL_CHAIN_MAP['url_shortener'])
        score += 15

    # ── Rule 4: Brand spoofing keywords (+25) ────────────────────
    found_brands = [kw for kw in BRAND_KEYWORDS if kw in lower_url]
    if found_brands:
        indicators.append(f'Brand spoofing keywords: {", ".join(found_brands)}')
        kill_chain_set.add(KILL_CHAIN_MAP['brand_spoofing'])
        score += 25

    # ── Rule 5: Social engineering keywords (+20) ─────────────────
    found_social = [kw for kw in SOCIAL_ENG_KEYWORDS if kw in lower_url]
    if found_social:
        indicators.append(f'Social engineering keywords: {", ".join(found_social[:5])}')
        kill_chain_set.add(KILL_CHAIN_MAP['social_engineering'])
        score += 20

    # ── Rule 6: Punycode / IDN homograph (+25) ────────────────────
    if 'xn--' in hostname:
        indicators.append(f'Punycode/IDN hostname detected (homograph attack risk): {hostname}')
        kill_chain_set.add(KILL_CHAIN_MAP['punycode'])
        score += 25

    # ── Rule 7: Excessive subdomain depth (+15) ───────────────────
    subdomain_depth = len(domain_parts) - 2  # subtract SLD + TLD
    if subdomain_depth > 3:
        indicators.append(f'Excessive subdomain depth: {subdomain_depth} levels ({hostname})')
        kill_chain_set.add(KILL_CHAIN_MAP['ip_based'])  # Evasion
        score += 15

    # ── Rule 8: Long URL obfuscation (+10) ────────────────────────
    if len(url) > 100:
        indicators.append(f'Unusually long URL: {len(url)} characters')
        score += 10

    # ── Rule 9: HTTP (not HTTPS) (+10) ───────────────────────────
    if parsed.scheme == 'http':
        indicators.append('Non-secure HTTP connection (no SSL/TLS)')
        score += 10

    # ── Rule 10: Hyphen abuse in domain (+10) ─────────────────────
    hyphen_count = root_domain.count('-')
    if hyphen_count >= 3:
        indicators.append(f'Hyphen abuse in domain: {hyphen_count} hyphens in "{root_domain}"')
        score += 10

    # ── Rule 11: Numeric-heavy hostname (+10) ─────────────────────
    digits_in_host = sum(c.isdigit() for c in hostname)
    if digits_in_host > 4:
        indicators.append(f'Numeric-heavy domain: {digits_in_host} digits in hostname')
        score += 10

    # ── Rule 12: Page-level signals from content script (+20 each) ─
    if page_signals:
        for signal in page_signals:
            indicators.append(f'[PAGE] {signal}')
            score += 20
        kill_chain_set.add(KILL_CHAIN_MAP['page_signal'])

    # ── Cap at 100 ────────────────────────────────────────────────
    score = min(score, 100)

    # ── Risk level ────────────────────────────────────────────────
    if score <= 20:
        level = 'Low'
    elif score <= 50:
        level = 'Medium'
    elif score <= 79:
        level = 'High'
    else:
        level = 'Critical'

    return {
        'url':        url,
        'score':      score,
        'level':      level,
        'indicators': indicators,
        'kill_chain': sorted(kill_chain_set),
    }