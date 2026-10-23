with open(r'C:\Users\shashank\edtech-review-engine\outbound\dispatch_campaign.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'PUBLIC_URL = ".*?"', 'PUBLIC_URL = "https://typing-accomplish-scheduled-promotional.trycloudflare.com"', text)

with open(r'C:\Users\shashank\edtech-review-engine\outbound\dispatch_campaign.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated dispatch_campaign.py with new live public edge URL!")
