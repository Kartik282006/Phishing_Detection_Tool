import re
from urllib.parse import urlparse

class HistoryAnalyzer:
    def __init__(self):
        # Basic heuristic lists
        self.suspicious_tlds = {'.xyz', '.top', '.club', '.info', '.ru', '.cn', '.tk', '.ml', '.ga', '.cf', '.gq'}
        self.suspicious_keywords = {'login', 'verify', 'update', 'secure', 'account', 'banking', 'service', 'confirm', 'wallet', 'crypto'}
        self.brand_keywords = {'paypal', 'google', 'apple', 'microsoft', 'amazon', 'facebook', 'netflix', 'chase', 'wellsfargo', 'boa'}
        self.blacklisted_domains = {'example-phish.com', 'malicious-site.net'} # Example blacklist

    def parse_history(self, text):
        """
        Parses raw text into list of entries.
        Expected formats:
        - timestamp,url,title
        - url only
        - [timestamp] url (title)
        """
        entries = []
        lines = text.strip().split('\n')
        
        url_pattern = re.compile(r'(https?://[^\s]+)')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try CSV format first
            parts = line.split(',')
            if len(parts) >= 2 and url_pattern.search(parts[1]):
                entries.append({
                    'timestamp': parts[0].strip(),
                    'url': parts[1].strip(),
                    'title': parts[2].strip() if len(parts) > 2 else ''
                })
                continue
            
            # Search for URL in line
            match = url_pattern.search(line)
            if match:
                url = match.group(1)
                # Try to extract title (simple heuristic: text after URL)
                title = line.replace(url, '').strip(' ()[]')
                entries.append({
                    'timestamp': '', # Could imply from position if needed
                    'url': url,
                    'title': title
                })
        
        return entries

    def analyze_entry(self, entry):
        url = entry['url']
        title = entry['title'].lower()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        score = 0
        reasons = []
        
        # Check 1: Suspicious TLD
        if any(domain.endswith(tld) for tld in self.suspicious_tlds):
            score += 3
            reasons.append(f"Suspicious TLD detected ({domain})")
            
        # Check 2: IP Address as domain
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            score += 4
            reasons.append("URL uses IP address instead of domain name")
            
        # Check 3: Brand Spoofing (Keyword in domain but not the official domain)
        # This is simple; production needs better whitelisting
        for brand in self.brand_keywords:
            if brand in domain and f"{brand}.com" not in domain:
                # Naive check
                score += 2
                reasons.append(f"Possible brand spoofing detected for '{brand}'")

        # Check 4: Title Keywords
        if any(kw in title for kw in self.suspicious_keywords):
            score += 2
            reasons.append(f"Title contains sensitive keyword '{title}'")
            
        # Check 5: Length
        if len(url) > 70:
            score += 1
            reasons.append("Unusually long URL")

        return score, reasons

    def analyze_history(self, text):
        entries = self.parse_history(text)
        if not entries:
            return {
                "risk_level": "Unknown",
                "summary": "No valid URLs found in the input.",
                "detailed_analysis": [],
                "recommendations": ["Please paste valid browsing history logs containing URLs."]
            }
            
        total_score = 0
        details = []
        high_risk_entries = 0
        
        for entry in entries:
            score, reasons = self.analyze_entry(entry)
            risk = "Low"
            if score >= 5:
                risk = "Critical"
                high_risk_entries += 1
            elif score >= 3:
                risk = "High"
                high_risk_entries += 1
            elif score >= 1:
                risk = "Medium"
            
            total_score += score
            
            if reasons: # Only report interesting findings
                details.append({
                    "entry": entry['url'],
                    "risk": risk,
                    "reasons": reasons
                })
        
        # Determine overall risk
        overall_risk = "Low"
        if high_risk_entries > 0:
            overall_risk = "Critical" if high_risk_entries > 2 else "High"
        elif total_score > 5:
            overall_risk = "Medium"
            
        summary = f"Analyzed {len(entries)} entries. Found {len(details)} potential issues."
        recommendations = []
        
        if overall_risk in ["High", "Critical"]:
            recommendations.append("Immediate Action: Reset passwords for accounts accessed on flagged sites.")
            recommendations.append("Run a full system malware scan.")
            recommendations.append("Clear browser cache and cookies.")
        elif overall_risk == "Medium":
             recommendations.append("Review the flagged URLs manually.")
             recommendations.append("Be cautious with links from unknown sources.")
        else:
            recommendations.append("No significant threats detected, but always stay vigilant.")

        return {
            "risk_level": overall_risk,
            "summary": summary,
            "detailed_analysis": details,
            "recommendations": recommendations
        }
