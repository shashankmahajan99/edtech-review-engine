import urllib.request
import re
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
urls = [
    'https://www.thinkingstorm.com/login.aspx',
    'https://www.thinkingstorm.com/availableSubjects.aspx',
    'https://www.thinkingstorm.com/ourapproach.aspx',
    'https://www.thinkingstorm.com/ourtutors.aspx',
    'https://www.thinkingstorm.com/institutionalregistration.aspx'
]

summary = {}
for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as res:
            html = res.read().decode('utf-8', errors='ignore')
            # Extract forms and inputs
            forms = re.findall(r'<form.*?</form>', html, flags=re.DOTALL)
            inputs = re.findall(r'<input[^>]+>', html)
            summary[u] = {
                "status": res.status,
                "input_fields": [re.search(r'name=["\']([^"\']+)["\']', inp).group(1) for inp in inputs if re.search(r'name=["\']([^"\']+)["\']', inp)],
                "snippet": re.sub(r'<[^>]+>', ' ', html)[:400]
            }
    except Exception as e:
        summary[u] = {"error": str(e)}

print(json.dumps(summary, indent=2))
