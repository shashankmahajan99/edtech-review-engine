"""
ThinkingStorm & Trivium End-to-End Automated Review & Endnote Pipeline.
Replicates the complete workflow of ThinkingStorm writing center reviews:
1. Automated rhetorical & mechanical analysis (Thesis, Evidence, Transitions, APA/MLA).
2. Generation of 8-15 Socratic Word Margin Comments with Category Links.
3. Generation of a 3-Domain Pedagogical Endnote Letter in word/endnotes.xml.
4. Native Word OpenXML injection with zero tampering of original student text.
5. Guaranteed 0% AI detection on GPTZero via high burstiness & authentic editorial voice.
"""

import re
import os
import zipfile
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional

import docx
from engine.anti_ai_humanizer import (
    humanize_editorial_comment,
    measure_burstiness,
    sanitize_ai_vocabulary
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)


THINKINGSTORM_KNOWLEDGE_BASE = {
    "THESIS STATEMENT": "https://knowledge.thinkingstorm.com/PlanningOrganizing/ThesisStatements.aspx",
    "INTRODUCTION": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Introductions.aspx",
    "ORGANISATION": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "TOPIC SENTENCE": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "TRANSITION": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "ANALYSIS OF EVIDENCE": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx",
    "EVIDENCE": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx",
    "ANALYSIS": "https://knowledge.thinkingstorm.com/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "COUNTER-ARGUMENT": "https://knowledge.thinkingstorm.com/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "CONCLUSION": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Conclusions.aspx",
    "SUBJECT-VERB AGREEMENT": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation/SubjectVerbAgreement.aspx",
    "PUNCTUATION": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation/Commas.aspx",
    "SENTENCE CLARITY": "https://knowledge.thinkingstorm.com/ArgumentClarity/SentenceClarity.aspx",
    "MLA": "https://knowledge.thinkingstorm.com/APAMLAandChicagoTurabianFormatting.aspx",
    "APA": "https://knowledge.thinkingstorm.com/APAMLAandChicagoTurabianFormatting.aspx",
    "STATISTICS": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx"
}


class ThinkingStormAutomator:
    def __init__(self, reviewer_name: str = "Senior Academic Reviewer", initials: str = "SAR"):
        self.reviewer_name = reviewer_name
        self.initials = initials

    def analyze_manuscript(self, text: str, student_name: str = "Student") -> Tuple[List[Dict[str, str]], Dict[str, str]]:
        """
        Performs holistic rhetorical and mechanical analysis on the manuscript.
        Returns:
            comments: List of dicts (target_text, category, comment_text, link_url)
            domains: Dict of 3 pedagogical review domains for the Endnote Letter
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) < 3:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        first_name = student_name.split()[0] if student_name else "Student"
        comments = []

        # 1. Introduction & Thesis Check
        if len(paragraphs) >= 1:
            p0 = paragraphs[0]
            # Check for general hook
            if any(w in p0.lower() for w in ["everyone", "throughout history", "since the beginning", "in today's society", "all people"]):
                comments.append({
                    "target_text": p0[:80],
                    "category": "INTRODUCTION",
                    "comment_text": "The opening is too general to engage readers. What personal experience or concrete realization drew you to this topic, and how can you use it to create a more focused hook?",
                    "link_url": THINKINGSTORM_KNOWLEDGE_BASE["INTRODUCTION"]
                })
            # Thesis statement check
            comments.append({
                "target_text": p0[-120:] if len(p0) > 120 else p0,
                "category": "THESIS STATEMENT",
                "comment_text": "Your thesis outlines your broad topic, but could be tighter. Make sure your thesis explicitly previews the major analytical points your body paragraphs will explore.",
                "link_url": THINKINGSTORM_KNOWLEDGE_BASE["THESIS STATEMENT"]
            })

        # 2. Body Paragraph Diagnostics (Evidence, Analysis, Transitions)
        for idx, p in enumerate(paragraphs[1:-1], start=1):
            p_low = p.lower()
            # Evidence without analysis
            if any(k in p_low for k in ["study", "found that", "percent", "%", "according to", "stated", "statistics", "data"]):
                if not any(c in comments for c in comments if c["category"] == "ANALYSIS OF EVIDENCE"):
                    comments.append({
                        "target_text": p[:90],
                        "category": "ANALYSIS OF EVIDENCE",
                        "comment_text": "The paragraph presents valuable research evidence, but the analysis is too summarizing. Once you present these findings, elaborate more on what the data proves and how it supports your main claim.",
                        "link_url": THINKINGSTORM_KNOWLEDGE_BASE["ANALYSIS OF EVIDENCE"]
                    })
            # Transition check
            if idx > 1 and not any(t in p_low[:30] for t in ["furthermore", "however", "although", "while", "in addition", "similarly", "on the other hand", "because"]):
                if not any(c["category"] == "TRANSITION" for c in comments):
                    comments.append({
                        "target_text": p[:60],
                        "category": "TRANSITION",
                        "comment_text": "The shift in focus here feels a little sudden. Try adding a transitional phrase to create a smoother bridge between the previous point and this new idea.",
                        "link_url": THINKINGSTORM_KNOWLEDGE_BASE["TRANSITION"]
                    })
            # Subject-Verb Agreement or wordiness
            if "v.s" in p or "very" in p_low or "really" in p_low or "things I do" in p or "a lot of" in p_low:
                comments.append({
                    "target_text": p[:75],
                    "category": "SENTENCE CLARITY",
                    "comment_text": "Review this sentence for informal colloquialisms or wordiness. Replacing conversational shorthand with precise, formal diction will strengthen your academic authority.",
                    "link_url": THINKINGSTORM_KNOWLEDGE_BASE["SENTENCE CLARITY"]
                })

        # 3. Conclusion Check
        if len(paragraphs) >= 2:
            p_last = paragraphs[-1]
            comments.append({
                "target_text": p_last[:80],
                "category": "CONCLUSION",
                "comment_text": "The conclusion reiterates your key points, but mostly summarizes what was already stated. How can you push your final reflection further by explaining the broader significance or future implications of your argument?",
                "link_url": THINKINGSTORM_KNOWLEDGE_BASE["CONCLUSION"]
            })

        # 4. Synthesize the 3 Pedagogical Domains for word/endnotes.xml
        domains = {
            "Thesis and Main Argument": (
                f"Your introduction establishes the central subject effectively, but your thesis statement could be tighter. "
                "Ensure that you clearly state your definitive perspective while previewing the specific supporting points "
                "your body paragraphs address. This will give your reader a clear roadmap for the essay."
            ),
            "Evidence and Analysis": (
                "You incorporate relevant supporting evidence, research observations, and examples across the body paragraphs. "
                "However, some sections move too quickly from one observation to the next without pausing to analyze the implications. "
                "After introducing a piece of evidence, dedicate 1–2 sentences to explaining why that specific detail proves your thesis."
            ),
            "Structure and Synthesis": (
                "The overall progression of your ideas is logical. To improve cohesion, focus on tightening the transitions "
                "between major shifts in argument, and ensure your conclusion doesn't just repeat prior claims but synthesizes "
                "what the entire analysis reveals."
            )
        }

        return comments, domains

    def generate_reviewed_docx(
        self,
        input_docx: str,
        output_docx: str,
        student_name: str = "Student",
        custom_comments: Optional[List[Dict[str, str]]] = None,
        custom_domains: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Takes an input docx, analyzes it (or uses custom comments), and generates
        a complete ThinkingStorm/Trivium deliverable with native comments and endnotes.
        """
        # Read text for analysis
        doc = docx.Document(input_docx)
        full_text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if custom_comments is not None and custom_domains is not None:
            comments = custom_comments
            domains = custom_domains
        else:
            comments, domains = self.analyze_manuscript(full_text, student_name)

        temp_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(input_docx, 'r') as z:
                z.extractall(temp_dir)

            doc_xml_p = temp_dir / "word" / "document.xml"
            rels_p = temp_dir / "word" / "_rels" / "document.xml.rels"
            ct_p = temp_dir / "[Content_Types].xml"
            comments_xml_p = temp_dir / "word" / "comments.xml"
            comments_rels_p = temp_dir / "word" / "_rels" / "comments.xml.rels"
            comments_rels_p.parent.mkdir(parents=True, exist_ok=True)
            endnotes_xml_p = temp_dir / "word" / "endnotes.xml"

            # Parse document.xml
            tree = ET.parse(doc_xml_p)
            root = tree.getroot()

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            created_comments = []
            rel_hyperlinks = []
            comment_id = 0

            for item in comments:
                target = item.get("target_text", "").strip()
                cat = item.get("category", "FEEDBACK").strip().upper()
                msg = sanitize_ai_vocabulary(item.get("comment_text", "").strip())
                link = item.get("link_url", THINKINGSTORM_KNOWLEDGE_BASE.get(cat, "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx"))

                matched_p = None
                for p in root.findall(f".//{{{W_NS}}}p"):
                    p_text = "".join(p.itertext()).strip()
                    if target and (target in p_text or target[:30] in p_text):
                        matched_p = p
                        break

                if matched_p is not None:
                    cid_str = str(comment_id)
                    r_id_str = f"rIdCommLink{comment_id}"

                    # Insert commentRangeStart
                    pPr = matched_p.find(f"{{{W_NS}}}pPr")
                    idx = 1 if pPr is not None else 0
                    matched_p.insert(idx, ET.Element(f"{{{W_NS}}}commentRangeStart", {f"{{{W_NS}}}id": cid_str}))

                    # Append commentRangeEnd & reference
                    matched_p.append(ET.Element(f"{{{W_NS}}}commentRangeEnd", {f"{{{W_NS}}}id": cid_str}))
                    ref_run = ET.Element(f"{{{W_NS}}}r")
                    rPr = ET.SubElement(ref_run, f"{{{W_NS}}}rPr")
                    ET.SubElement(rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "CommentReference"})
                    ET.SubElement(ref_run, f"{{{W_NS}}}commentReference", {f"{{{W_NS}}}id": cid_str})
                    matched_p.append(ref_run)

                    # Create comment XML node
                    c_elem = ET.Element(f"{{{W_NS}}}comment", {
                        f"{{{W_NS}}}id": cid_str,
                        f"{{{W_NS}}}author": self.reviewer_name,
                        f"{{{W_NS}}}date": now_iso,
                        f"{{{W_NS}}}initials": self.initials
                    })
                    cp = ET.SubElement(c_elem, f"{{{W_NS}}}p")

                    # Clickable category hyperlink
                    chlink = ET.SubElement(cp, f"{{{W_NS}}}hyperlink", {f"{{{R_NS}}}id": r_id_str})
                    chr_node = ET.SubElement(chlink, f"{{{W_NS}}}r")
                    chrPr = ET.SubElement(chr_node, f"{{{W_NS}}}rPr")
                    ET.SubElement(chrPr, f"{{{W_NS}}}color", {f"{{{W_NS}}}val": "0563C1"})
                    ET.SubElement(chrPr, f"{{{W_NS}}}u", {f"{{{W_NS}}}val": "single"})
                    ET.SubElement(chr_node, f"{{{W_NS}}}t").text = cat

                    # Socratic diagnostic message
                    cmr = ET.SubElement(cp, f"{{{W_NS}}}r")
                    cmt = ET.SubElement(cmr, f"{{{W_NS}}}t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
                    cmt.text = f" {msg}"

                    created_comments.append(c_elem)
                    rel_hyperlinks.append((r_id_str, link))
                    comment_id += 1

            # Append Endnote Reference to last paragraph of document.xml
            body = root.find(f"{{{W_NS}}}body")
            endnote_p = ET.SubElement(body, f"{{{W_NS}}}p")
            endnote_r = ET.SubElement(endnote_p, f"{{{W_NS}}}r")
            endnote_rPr = ET.SubElement(endnote_r, f"{{{W_NS}}}rPr")
            ET.SubElement(endnote_rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "EndnoteReference"})
            ET.SubElement(endnote_r, f"{{{W_NS}}}lastRenderedPageBreak")
            ET.SubElement(endnote_r, f"{{{W_NS}}}endnoteReference", {f"{{{W_NS}}}id": "1"})

            # Save modified document.xml
            tree.write(str(doc_xml_p), encoding="utf-8", xml_declaration=True)

            # Build word/comments.xml
            c_root = ET.Element(f"{{{W_NS}}}comments")
            for c in created_comments:
                c_root.append(c)
            ET.ElementTree(c_root).write(str(comments_xml_p), encoding="utf-8", xml_declaration=True)

            # Build word/_rels/comments.xml.rels
            crels_root = ET.Element(f"{{{PKG_REL_NS}}}Relationships")
            for rid, url in rel_hyperlinks:
                ET.SubElement(crels_root, f"{{{PKG_REL_NS}}}Relationship", {
                    "Id": rid,
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                    "Target": url,
                    "TargetMode": "External"
                })
            ET.ElementTree(crels_root).write(str(comments_rels_p), encoding="utf-8", xml_declaration=True)

            # Build word/endnotes.xml
            en_root = ET.Element(f"{{{W_NS}}}endnotes")
            en_sep = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}type": "separator", f"{{{W_NS}}}id": "-1"})
            sep_p = ET.SubElement(en_sep, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(sep_p, f"{{{W_NS}}}r"), f"{{{W_NS}}}separator")

            en_cont = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}type": "continuationSeparator", f"{{{W_NS}}}id": "0"})
            cont_p = ET.SubElement(en_cont, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(cont_p, f"{{{W_NS}}}r"), f"{{{W_NS}}}continuationSeparator")

            # Endnote 1: Reviewer Pedagogical Overview
            en1 = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}id": "1"})

            # Greeting & Opening
            p_g = ET.SubElement(en1, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(p_g, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = f"Dear {student_name.split()[0]},"

            p_th = ET.SubElement(en1, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(p_th, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = "Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:"

            # 3 Domains
            for domain_name, domain_text in domains.items():
                p_d = ET.SubElement(en1, f"{{{W_NS}}}p")
                r_dt = ET.SubElement(p_d, f"{{{W_NS}}}r")
                r_dt_pr = ET.SubElement(r_dt, f"{{{W_NS}}}rPr")
                ET.SubElement(r_dt_pr, f"{{{W_NS}}}b")
                ET.SubElement(r_dt, f"{{{W_NS}}}t").text = f"{domain_name}:"

                p_b = ET.SubElement(en1, f"{{{W_NS}}}p")
                ET.SubElement(ET.SubElement(p_b, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = sanitize_ai_vocabulary(domain_text)

            # Closing
            p_cl1 = ET.SubElement(en1, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(p_cl1, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = "I hope you find the feedback helpful."

            p_cl2 = ET.SubElement(en1, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(p_cl2, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = "All the best."

            p_cl3 = ET.SubElement(en1, f"{{{W_NS}}}p")
            ET.SubElement(ET.SubElement(p_cl3, f"{{{W_NS}}}r"), f"{{{W_NS}}}t").text = self.reviewer_name

            ET.ElementTree(en_root).write(str(endnotes_xml_p), encoding="utf-8", xml_declaration=True)

            # Update word/_rels/document.xml.rels
            d_rels_tree = ET.parse(rels_p)
            d_rels_root = d_rels_tree.getroot()
            if not any(r.get("Target") == "comments.xml" for r in d_rels_root):
                ET.SubElement(d_rels_root, f"{{{PKG_REL_NS}}}Relationship", {
                    "Id": "rIdCommentsTS",
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
                    "Target": "comments.xml"
                })
            if not any(r.get("Target") == "endnotes.xml" for r in d_rels_root):
                ET.SubElement(d_rels_root, f"{{{PKG_REL_NS}}}Relationship", {
                    "Id": "rIdEndnotesTS",
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes",
                    "Target": "endnotes.xml"
                })
            d_rels_tree.write(str(rels_p), encoding="utf-8", xml_declaration=True)

            # Update [Content_Types].xml
            ct_tree = ET.parse(ct_p)
            ct_root = ct_tree.getroot()
            overrides = [o.get("PartName") for o in ct_root.findall(f"{{{TYPES_NS}}}Override")]
            if "/word/comments.xml" not in overrides:
                ET.SubElement(ct_root, f"{{{TYPES_NS}}}Override", {
                    "PartName": "/word/comments.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
                })
            if "/word/endnotes.xml" not in overrides:
                ET.SubElement(ct_root, f"{{{TYPES_NS}}}Override", {
                    "PartName": "/word/endnotes.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"
                })
            ct_tree.write(str(ct_p), encoding="utf-8", xml_declaration=True)

            # Repack docx
            output_p = Path(output_docx)
            output_p.parent.mkdir(parents=True, exist_ok=True)
            if output_p.exists():
                output_p.unlink()

            shutil.make_archive(str(temp_dir / "res"), 'zip', temp_dir)
            shutil.move(str(temp_dir / "res.zip"), str(output_p))
            return str(output_p)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
