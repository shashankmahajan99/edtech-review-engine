"""
Submits enterprise consultation to ChatGPT via CDP and streams response.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

LOGS_DIR = Path(__file__).resolve().parent / "consultation_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = """You are acting as the Chief Business Architect & Advisory Board for our new venture: Apex Academic & Admissions Review Desk.

CONTEXT:
We are disintermediating the legacy educational process outsourcing (EPO) supply chain—specifically ThinkingStorm (US front) and Trivium Education (India backend).
ThinkingStorm charges US universities $25-$48 per essay review or $50k-$250k annual retainers. They subcontract to Trivium in India at ~$8-$14/review. Trivium pays Indian freelance English reviewers ₹150-₹350/hr (~$1.80-$4.20/review). The middle chain pockets 85%+ margin while delivering slow 24-48hr turnaround.

OUR CURRENT ASSETS:
1. An existing pool of vetted freelance English reviewers and SMEs.
2. A 24/7 server base running locally with an AI-augmented review engine producing annotated Word documents (.docx) with tracked changes and a 4-pillar rubric report.
3. Reviewer velocity: 7 minutes per paper (AI pre-annotates, reviewer conducts sanity/voice calibration). We pay reviewers ₹300 ($3.60) per 7-minute review (effective ₹2,400/hr, 8x Trivium rate), retaining 85%+ margin.

YOUR SUPERVISORY MANDATE:
Critique and refine our enterprise strategy:
1. High-Ticket B2B Wedge: During this Oct-Jan college application rush, how do we best structure white-label retainers ($1,500-$3,500/mo) for Independent Educational Consultants (IECA/HECA) and boutique admissions firms?
2. Defensible Moat: What prevents clients from simply using raw ChatGPT or a competitor? How do we build an institutional moat?
3. 5-Pass QA Assembly Line: What specific verification gates must be enforced to ensure 0% hallucination and voice preservation?
4. Scaling Trajectory: What are the concrete milestones to scale from $10k/mo MRR to $100k+/mo MRR over the next 12 months?

Provide an unvarnished, high-rigor enterprise blueprint.
"""


def main():
    print("Connecting to browser on port 9222...")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        chatgpt_page = None
        for page in context.pages:
            if "chatgpt.com" in page.url:
                chatgpt_page = page
                break
                
        if not chatgpt_page:
            print("[!] ChatGPT page not found.")
            return

        print("[*] Found ChatGPT tab. Focusing...")
        chatgpt_page.bring_to_front()
        time.sleep(1)

        input_box = chatgpt_page.locator("textarea").first
        if not input_box.is_visible():
            print("[!] Prompt input not visible.")
            return

        print("[*] Typing strategic brief into ChatGPT...")
        input_box.click()
        input_box.fill(PROMPT)
        time.sleep(1)
        chatgpt_page.keyboard.press("Enter")
        print("[*] Brief dispatched! Waiting for generation to complete...")

        # Wait for assistant response to stream
        time.sleep(15)
        for i in range(12):
            # Check if streaming is still in progress (presence of stop button)
            stop_btn = chatgpt_page.locator("button[data-testid='stop-button'], button[aria-label='Stop streaming'], button[aria-label='Stop generating']")
            if stop_btn.count() > 0 and stop_btn.first.is_visible():
                print(f"[*] Generation in progress... ({i*5}s)")
                time.sleep(5)
            else:
                break

        time.sleep(3)
        # Extract assistant responses
        articles = chatgpt_page.locator("article, [data-message-author-role='assistant'], .markdown").all()
        if articles:
            latest_text = articles[-1].inner_text()
            out_file = LOGS_DIR / "chatgpt_strategic_guidance.md"
            out_file.write_text(latest_text, encoding="utf-8")
            print(f"\n[OK] Strategic guidance from ChatGPT successfully captured!")
            print(f"Saved to: {out_file}")
            print(f"Response length: {len(latest_text)} characters")
            print("\nPreview of guidance:")
            print(latest_text[:800] + "...\n")
        else:
            print("[!] Could not extract response text.")


if __name__ == "__main__":
    main()
