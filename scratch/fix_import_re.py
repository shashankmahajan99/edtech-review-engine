with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("import os\nimport sys", "import os\nimport sys\nimport re", 1)

with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Added import re to portal/server.py")
