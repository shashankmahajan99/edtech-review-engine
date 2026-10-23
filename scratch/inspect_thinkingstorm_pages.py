import urllib.request
import re
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
pages = [
    'https://www.thinkingstorm.com/products.aspx',
    'https://www.thinkingstorm.com/anytime.aspx',
    'https://www.thinkingstorm.com/billing-policy.aspx',
    'https://www.thinkingstorm.com/highereducation.aspx',
    'https://www.thinkingstorm.com/individuals.aspx',
    'https://www.thinkingstorm.com/faqs.aspx'
]

summary = {}

for p in pages:
    try:
        req = urllib.request.Request(p, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as res:
            html = res.read().decode('utf-8', errors='ignore')
            # Extract plain text
            clean = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
            clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL)
            clean = re.sub(r'<[^>]+>', ' ', clean)
            lines = [l.strip() for l in clean.splitlines() if l.strip()]
            text = " ".join(lines)
            summary[p] = {
                "length": len(html),
                "text_snippet": text[:1200]
            }
    except Exception as e:
        summary[p] = {"error": str(e)}

import json
print(json.dumps(summary, indent=2))
