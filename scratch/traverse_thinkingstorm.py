import urllib.request
import re
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
urls_to_check = [
    'https://www.thinkingstorm.com',
    'https://www.thinkingstorm.com/services',
    'https://www.thinkingstorm.com/writing-center',
    'https://www.thinkingstorm.com/institutions',
    'https://www.thinkingstorm.com/robots.txt',
    'https://www.thinkingstorm.com/sitemap.xml'
]

results = {}

for url in urls_to_check:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as res:
            content = res.read().decode('utf-8', errors='ignore')
            links = list(set(re.findall(r'href=["\'](/[^"\']+)["\']', content)))
            results[url] = {
                "status": res.status,
                "length": len(content),
                "discovered_routes": sorted(links)[:15]
            }
    except Exception as e:
        results[url] = {"status": "error", "error": str(e)}

print(json.dumps(results, indent=2))
