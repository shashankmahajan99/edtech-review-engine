from pathlib import Path
import re

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

# 1. Remove the accidental injection from login_page
login_injection = '''<script>
const AUDIT_SAMPLES = {
    stanford: "Ever since I was a child, I have always been deeply passionate about computers. Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum. In conclusion, it can be seen that my work is a testament to my dedication to broaden my horizons.",
    harvard: "I want to attend Harvard University to step out of my comfort zone and broaden my horizons. Ever since I was a child, public policy sparked my interest. In conclusion, it can be seen that my background makes me an ideal candidate for your government faculty.",
    wharton: "I am deeply passionate about finance and quantitative economics. The Wharton School has world-class faculty and cutting-edge curriculum that will spark my interest and allow me to step out of my comfort zone."
};

function loadSample(key) {
    if (AUDIT_SAMPLES[key]) {
        document.getElementById('auditInputText').value = AUDIT_SAMPLES[key];
        document.getElementById('auditInstitution').value = key === 'stanford' ? 'Stanford' : (key === 'harvard' ? 'Harvard' : 'Wharton');
        executeLiveAudit();
    }
}

async function executeLiveAudit() {
    const text = document.getElementById('auditInputText').value;
    const inst = document.getElementById('auditInstitution').value;
    const btn = document.getElementById('auditRunBtn');
    btn.innerText = 'Analyzing...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/audit/sample', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text, institution: inst})
        });
        const data = await resp.json();
        
        document.getElementById('scoreVoice').innerText = data.scores.voice_authenticity + ' / 100';
        document.getElementById('scoreFaculty').innerText = data.scores.faculty_alignment + ' / 100';
        document.getElementById('scoreMomentum').innerText = data.scores.narrative_momentum + ' / 100';
        document.getElementById('scoreAuth').innerText = data.scores.authenticity_integrity + ' / 100';
        
        document.getElementById('auditRedlineView').innerHTML = data.redlined_html;
    } catch (e) {
        console.error(e);
    } finally {
        btn.innerText = 'Run Pedagogical Voice Audit (0.4s) ⚡';
        btn.disabled = false;
    }
}
</script>
'''

if login_injection in content:
    content = content.replace(login_injection, "", 1)
    print("Removed misplaced script from login_page")

# 2. Add the JS into landing_page before the closing </body> of landing_page
landing_close = "document.getElementById('calcRetainer').innerText = students > 45 ? '$3,500/mo' : (students > 20 ? '$2,500/mo' : '$1,500/mo');\n    }}\n</script>"

audit_js_for_landing = """
<script>
const AUDIT_SAMPLES = {
    stanford: "Ever since I was a child, I have always been deeply passionate about computers. Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum. In conclusion, it can be seen that my work is a testament to my dedication to broaden my horizons.",
    harvard: "I want to attend Harvard University to step out of my comfort zone and broaden my horizons. Ever since I was a child, public policy sparked my interest. In conclusion, it can be seen that my background makes me an ideal candidate for your government faculty.",
    wharton: "I am deeply passionate about finance and quantitative economics. The Wharton School has world-class faculty and cutting-edge curriculum that will spark my interest and allow me to step out of my comfort zone."
};

function loadSample(key) {
    if (AUDIT_SAMPLES[key]) {
        document.getElementById('auditInputText').value = AUDIT_SAMPLES[key];
        document.getElementById('auditInstitution').value = key === 'stanford' ? 'Stanford' : (key === 'harvard' ? 'Harvard' : 'Wharton');
        executeLiveAudit();
    }
}

async function executeLiveAudit() {
    const text = document.getElementById('auditInputText').value;
    const inst = document.getElementById('auditInstitution').value;
    const btn = document.getElementById('auditRunBtn');
    btn.innerText = 'Analyzing...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/audit/sample', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text, institution: inst})
        });
        const data = await resp.json();
        
        document.getElementById('scoreVoice').innerText = data.scores.voice_authenticity + ' / 100';
        document.getElementById('scoreFaculty').innerText = data.scores.faculty_alignment + ' / 100';
        document.getElementById('scoreMomentum').innerText = data.scores.narrative_momentum + ' / 100';
        document.getElementById('scoreAuth').innerText = data.scores.authenticity_integrity + ' / 100';
        
        document.getElementById('auditRedlineView').innerHTML = data.redlined_html;
    } catch (e) {
        console.error(e);
    } finally {
        btn.innerText = 'Run Pedagogical Voice Audit (0.4s) ⚡';
        btn.disabled = false;
    }
}
</script>
""".replace("{", "{{").replace("}", "}}")

if landing_close in content:
    content = content.replace(landing_close, landing_close + "\n" + audit_js_for_landing, 1)
    print("Injected audit JS into landing_page with escaped curlies")

SERVER_PATH.write_text(content, encoding="utf-8")
print("Cleaned server.py written.")
