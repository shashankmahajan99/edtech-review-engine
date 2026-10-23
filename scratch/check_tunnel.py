import urllib.request, json, subprocess, re

# Check cloudflared process
out = subprocess.check_output('tasklist /FI "IMAGENAME eq cloudflared.exe" /NH', shell=True).decode()
print('Cloudflared tasklist:\n', out.strip())

# Check tunnel.log
with open(r'C:\Users\shashank\edtech-review-engine\output\tunnel.log', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', text)
if urls:
    print('Found Tunnel URL:', urls[-1])
    try:
        with urllib.request.urlopen(urls[-1] + '/api/health', timeout=6) as res:
            print('Global Tunnel URL Health:', res.status, res.read().decode())
    except Exception as e:
        print('Global Tunnel URL Err:', e)
else:
    print('No tunnel URL found in tunnel.log')
