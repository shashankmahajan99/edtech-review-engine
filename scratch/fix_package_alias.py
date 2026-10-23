with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace PACKAGES["pilot"] with proper alias lookup
old_line = 'pkg = PACKAGES.get(package_id, PACKAGES["pilot"])'
new_line = '''PACKAGE_ALIASES = {"pilot": "paid_pilot", "paid_pilot": "paid_pilot", "starter": "starter", "pro": "pro", "enterprise": "enterprise"}
    pkg_key = PACKAGE_ALIASES.get(package_id, "paid_pilot")
    pkg = PACKAGES.get(pkg_key, PACKAGES["paid_pilot"])'''

text = text.replace(old_line, new_line)

with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated package alias lookup in portal/server.py")
