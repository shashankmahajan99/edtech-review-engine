with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_call = 'log_compliance_event(tx_id, "CAPACITY_COMMERCIAL_BOOKED", f"Firm {company_name} locked {pkg[\'name\']} for ${amount_dollars:.2f} USD")'
new_call = 'log_compliance_event(tx_id, email, "CAPACITY_COMMERCIAL_BOOKED", f"Firm {company_name} locked {pkg[\'name\']} for ${amount_dollars:.2f} USD")'

text = text.replace(old_call, new_call)

with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed log_compliance_event call in portal/server.py")
