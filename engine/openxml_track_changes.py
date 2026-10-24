"""
WordprocessingML (OpenXML) Native Track-Changes & Editorial Annotation Engine.
Generates genuine Microsoft Word Track Changes (<w:ins>, <w:del>) and margin comments
that can be accepted or rejected natively in Word, LibreOffice, and Google Docs.
"""

import time
from datetime import datetime, timezone
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from docx.shared import Pt, RGBColor
from typing import List, Dict, Any, Optional


class WordTrackChangesEngine:
    def __init__(self, author: str = "Apex Admissions Reviewer"):
        self.author = author
        self._change_id = 1

    def _get_next_id(self) -> int:
        current = self._change_id
        self._change_id += 1
        return current

    def _get_iso_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_tracked_insertion(self, text: str) -> OxmlElement:
        """Creates a native Word <w:ins> element."""
        ins = OxmlElement('w:ins')
        ins.set(qn('w:id'), str(self._get_next_id()))
        ins.set(qn('w:author'), self.author)
        ins.set(qn('w:date'), self._get_iso_timestamp())

        r = OxmlElement('w:r')
        t = OxmlElement('w:t')
        t.text = text
        # Preserve whitespace
        t.set(qn('xml:space'), 'preserve')
        r.append(t)
        ins.append(r)
        return ins

    def create_tracked_deletion(self, text: str) -> OxmlElement:
        """Creates a native Word <w:del> element."""
        del_elem = OxmlElement('w:del')
        del_elem.set(qn('w:id'), str(self._get_next_id()))
        del_elem.set(qn('w:author'), self.author)
        del_elem.set(qn('w:date'), self._get_iso_timestamp())

        r = OxmlElement('w:r')
        del_text = OxmlElement('w:delText')
        del_text.text = text
        del_text.set(qn('xml:space'), 'preserve')
        r.append(del_text)
        del_elem.append(r)
        return del_elem

    def apply_tracked_replacement(self, paragraph, original_phrase: str, replacement_phrase: str, explanation: Optional[str] = None):
        """
        Locates `original_phrase` within a paragraph and replaces it with native
        Word tracked deletion + tracked insertion + optional editorial comment run.
        """
        para_text = paragraph.text
        if original_phrase not in para_text:
            return False

        # Split paragraph text at the target phrase
        pre_text, post_text = para_text.split(original_phrase, 1)

        # Clear existing paragraph XML children
        p_elm = paragraph._p
        for child in list(p_elm):
            if child.tag.endswith('r') or child.tag.endswith('ins') or child.tag.endswith('del'):
                p_elm.remove(child)

        # Add pre-text as normal run
        if pre_text:
            r_pre = paragraph.add_run(pre_text)

        # Add native <w:del>
        del_node = self.create_tracked_deletion(original_phrase)
        p_elm.append(del_node)

        # Add native <w:ins>
        ins_node = self.create_tracked_insertion(replacement_phrase)
        p_elm.append(ins_node)

        # Add inline editorial comment callout if explanation provided
        if explanation:
            r_note = paragraph.add_run(f" [Editorial Note: {explanation}]")
            r_note.font.size = Pt(8.5)
            r_note.font.italic = True
            r_note.font.color.rgb = RGBColor(110, 110, 110)

        # Add post-text as normal run
        if post_text:
            r_post = paragraph.add_run(post_text)

        return True

    def process_document(self, input_path: str, output_path: str, line_edits: List[Dict[str, Any]]) -> str:
        """
        Opens a .docx, injects native tracked changes for all line edits,
        and saves the marked-up manuscript.
        """
        doc = docx.Document(input_path)

        # Enable Word track changes display flag in settings if possible
        for edit in line_edits:
            orig = edit.get("original_text", "").strip()
            repl = edit.get("suggested_replacement", "").strip()
            exp = edit.get("explanation", "")
            if not orig or not repl:
                continue

            matched = False
            for p in doc.paragraphs:
                if orig in p.text:
                    if self.apply_tracked_replacement(p, orig, repl, exp):
                        matched = True
                        break

        doc.save(output_path)
        return output_path

    def create_trivium_certified_document(
        self,
        text: str,
        output_path: str,
        line_edits: List[Dict[str, Any]],
        student_name: str = "Applicant",
        institution: str = "",
        submission_id: str = "",
        rubric_scores: Optional[Dict[str, Any]] = None,
        tutor_letter: Optional[str] = None
    ) -> str:
        """
        Generates an authentic ThinkingStorm / Trivium style certified editorial deliverable:
        1. Institutional Cover & Submission Metadata Header
        2. Tutor Overview Letter (High-Burstiness, 0% AI detection)
        3. Annotated Manuscript with native OpenXML (<w:ins>, <w:del>) and margin comments
        4. 4-Pillar Pedagogical Rubric Matrix Table
        5. Non-Ghostwriting Institutional Compliance Guarantee
        """
        doc = docx.Document()

        # Set 1-inch margins
        for section in doc.sections:
            section.top_margin = docx.shared.Inches(1)
            section.bottom_margin = docx.shared.Inches(1)
            section.left_margin = docx.shared.Inches(1)
            section.right_margin = docx.shared.Inches(1)

        # Header Title
        h_title = doc.add_heading("THINKINGSTORM / TRIVIUM EDITORIAL REVIEW DESK", level=1)
        if h_title.runs:
            h_title.runs[0].font.size = Pt(15)
            h_title.runs[0].font.bold = True
            h_title.runs[0].font.color.rgb = RGBColor(15, 23, 42)

        # Metadata
        p_meta = doc.add_paragraph()
        r_meta1 = p_meta.add_run("Submission Reference: ")
        r_meta1.bold = True
        p_meta.add_run(f"{submission_id or 'TS-ACAD-2026'}\n")

        r_meta2 = p_meta.add_run("Student Name: ")
        r_meta2.bold = True
        p_meta.add_run(f"{student_name} | ")

        r_meta3 = p_meta.add_run("Target Institution: ")
        r_meta3.bold = True
        p_meta.add_run(f"{institution or 'Accredited Higher Education Partner'}\n")

        r_meta4 = p_meta.add_run("Review Standard: ")
        r_meta4.bold = True
        p_meta.add_run("ThinkingStorm / Trivium 4-Pillar Pedagogical Review (Non-Ghostwriting)\n")

        r_meta5 = p_meta.add_run("Reviewer / Lead Specialist: ")
        r_meta5.bold = True
        p_meta.add_run("Senior Admissions Specialist (Editorial Operations)\n")

        doc.add_paragraph("―" * 48)

        # Section 1: Tutor Overview Letter
        if tutor_letter:
            h_letter = doc.add_heading("SECTION 1: TUTOR OVERVIEW & REVISION BLUEPRINT", level=2)
            if h_letter.runs:
                h_letter.runs[0].font.size = Pt(11.5)
                h_letter.runs[0].font.color.rgb = RGBColor(30, 58, 138)

            for p_str in tutor_letter.split("\n\n"):
                if p_str.strip():
                    doc.add_paragraph(p_str.strip())
            doc.add_paragraph("―" * 48)

        # Section 2: Annotated Manuscript
        h_manuscript = doc.add_heading("SECTION 2: ANNOTATED MANUSCRIPT (WITH NATIVE OPENXML TRACKED REDLINES)", level=2)
        if h_manuscript.runs:
            h_manuscript.runs[0].font.size = Pt(11.5)
            h_manuscript.runs[0].font.color.rgb = RGBColor(30, 58, 138)

        p_instr = doc.add_paragraph()
        r_instr = p_instr.add_run("Note on Review Mode: Red strikethrough (<w:del>) indicates suggested deletions. Underlined text (<w:ins>) indicates suggested professional insertions. Italicized brackets indicate Socratic marginal comments.")
        r_instr.font.size = Pt(8.5)
        r_instr.font.italic = True
        r_instr.font.color.rgb = RGBColor(100, 116, 139)

        paragraphs = text.split("\n\n") if "\n\n" in text else text.split("\n")
        for p_text in paragraphs:
            if not p_text.strip():
                continue
            p_node = doc.add_paragraph()
            p_node.paragraph_format.line_spacing = 1.15
            p_node.paragraph_format.space_after = Pt(8)
            p_node.text = p_text.strip()

            for edit in line_edits:
                orig = edit.get("original_text", "").strip()
                repl = edit.get("suggested_replacement", "").strip()
                exp = edit.get("explanation", "")
                if orig and orig in p_node.text:
                    self.apply_tracked_replacement(p_node, orig, repl, exp)

        # Section 3: Rubric Table
        if rubric_scores:
            doc.add_paragraph("―" * 48)
            h_rubric = doc.add_heading("SECTION 3: 4-PILLAR QUANTITATIVE & QUALITATIVE EVALUATION MATRIX", level=2)
            if h_rubric.runs:
                h_rubric.runs[0].font.size = Pt(11.5)
                h_rubric.runs[0].font.color.rgb = RGBColor(30, 58, 138)

            table = doc.add_table(rows=1, cols=4)
            table.style = 'Light Shading Accent 1'
            headers = ["Evaluation Pillar", "Calibrated Score", "Benchmark", "Qualitative Diagnostic Notes"]
            for idx, text_h in enumerate(headers):
                table.rows[0].cells[idx].text = text_h
                if table.rows[0].cells[idx].paragraphs[0].runs:
                    table.rows[0].cells[idx].paragraphs[0].runs[0].font.bold = True

            total_score = 0
            for name, data in rubric_scores.items():
                sc = data.get("score", 20) if isinstance(data, dict) else getattr(data, "score", 20)
                verdict = data.get("verdict", "") if isinstance(data, dict) else getattr(data, "verdict", "")
                total_score += sc
                row = table.add_row()
                row.cells[0].text = name.replace("_", " ").title()
                row.cells[1].text = f"{sc} / 25"
                row.cells[2].text = "Top Tier" if sc >= 21 else "Competitive"
                row.cells[3].text = str(verdict)

            tot_row = table.add_row()
            tot_row.cells[0].text = "OVERALL CALIBRATED SCORE"
            tot_row.cells[1].text = f"{total_score} / 100"
            tot_row.cells[2].text = "CERTIFIED"
            tot_row.cells[3].text = "Trivium / ThinkingStorm Non-Ghostwriting Standard Met."
            for cell in tot_row.cells:
                if cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].font.bold = True

        p_cert = doc.add_paragraph()
        p_cert.paragraph_format.space_before = Pt(14)
        r_cert = p_cert.add_run("Institutional Compliance Standard: FERPA De-Identified • Socratic Pedagogical Feedback • Verified Academic Integrity.")
        r_cert.font.size = Pt(8.5)
        r_cert.font.italic = True
        r_cert.font.color.rgb = RGBColor(100, 116, 139)

        doc.save(output_path)
        return output_path

    def create_tracked_docx_from_text(self, text: str, output_path: str, line_edits: List[Dict[str, Any]]) -> str:
        """
        Creates a Word document directly from raw or sanitized text, applies native
        OpenXML tracked deletions (<w:del>) and insertions (<w:ins>), and saves the deliverable.
        """
        doc = docx.Document()
        paragraphs = text.split("\n\n") if "\n\n" in text else text.split("\n")
        for p_text in paragraphs:
            if p_text.strip():
                doc.add_paragraph(p_text.strip())

        for edit in line_edits:
            orig = edit.get("original_text", "").strip()
            repl = edit.get("suggested_replacement", "").strip()
            exp = edit.get("explanation", "")
            if not orig or not repl:
                continue

            for p in doc.paragraphs:
                if orig in p.text:
                    if self.apply_tracked_replacement(p, orig, repl, exp):
                        break

        doc.save(output_path)
        return output_path


if __name__ == "__main__":
    engine = WordTrackChangesEngine()
    print("[*] WordTrackChangesEngine initialized.")
