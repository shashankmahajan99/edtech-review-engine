with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("if MONITOR_LOG.exists():", "monitor_log_path = OUTPUT_DIR / 'apex_monitor.log'\n    if monitor_log_path.exists():\n        try:\n            lines = monitor_log_path.read_text(encoding='utf-8', errors='ignore').splitlines()\n            recent_logs = '\\n'.join(lines[-25:])\n        except Exception:\n            pass")

# Remove redundant block if present
old_block = """    if MONITOR_LOG.exists():
        try:
            lines = MONITOR_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
            recent_logs = "\\n".join(lines[-25:])
        except Exception:
            pass"""

if old_block in text:
    text = text.replace(old_block, """    monitor_log_path = OUTPUT_DIR / 'apex_monitor.log'
    if monitor_log_path.exists():
        try:
            lines = monitor_log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
            recent_logs = '\\n'.join(lines[-25:])
        except Exception:
            pass""")

with open(r'C:\Users\shashank\edtech-review-engine\portal\server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed monitor_log_path in portal/server.py")
