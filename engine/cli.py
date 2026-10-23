"""
CLI tool for instant essay processing.
Usage:
  python -m engine.cli --input samples/sample_sop.txt --mode admissions
"""

import argparse
import sys
from pathlib import Path
from .processor import ReviewProcessor


def main():
    parser = argparse.ArgumentParser(description="AI-Augmented Editorial Review Engine")
    parser.add_argument("--input", "-i", required=True, help="Path to input text or docx file")
    parser.add_argument("--mode", "-m", choices=["academic", "admissions"], default="admissions", help="Review mode")
    parser.add_argument("--outdir", "-o", default="output", help="Directory to save generated reports")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] Error: File not found at {input_path}")
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Read input file
    if input_path.suffix.lower() == ".docx":
        import docx
        doc = docx.Document(input_path)
        text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    else:
        text = input_path.read_text(encoding="utf-8")

    print(f"[*] Processing document '{input_path.name}' ({len(text.split())} words) in '{args.mode}' mode...")
    
    processor = ReviewProcessor()
    review_data = processor.analyze_text(text, mode=args.mode)

    base_name = input_path.stem
    docx_out = outdir / f"{base_name}_annotated_review.docx"
    html_out = outdir / f"{base_name}_executive_report.html"

    processor.generate_annotated_docx(text, review_data, str(docx_out))
    processor.generate_html_report(review_data, str(html_out))

    print("\n[OK] Review completed successfully!")
    print(f"   * Overall Quality Score : {review_data.get('overall_score')}/100")
    print(f"   * Annotated Word Doc    : {docx_out.resolve()}")
    print(f"   * Executive HTML Report : {html_out.resolve()}")
    print("\nReviewer human QA check time: ~6 minutes (accepted / adjusted suggestions). Ready for delivery!")


if __name__ == "__main__":
    main()
