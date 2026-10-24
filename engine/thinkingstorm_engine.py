"""
ThinkingStorm & Trivium End-to-End Automated Review & Endnote Pipeline.
Replicates the complete workflow of ThinkingStorm writing center reviews:
1. Native Microsoft Word margin comments (<w:comment>) anchored strictly to quoted words/sentences.
2. Category links in ALL CAPS linked to matching ThinkingStorm Knowledge Base URLs.
3. Native Microsoft Word endnote letter in word/endnotes.xml (<w:endnote w:id="1">) with:
   - Font: Times New Roman
   - Size: 12-point (<w:sz w:val="24"/><w:szCs w:val="24"/>)
   - Line Spacing: 2.0 double-spaced (<w:spacing w:line="480" w:lineRule="auto"/>)
   - Color: Red (<w:color w:val="FF0000"/>)
   - Dynamic greeting (<Student first name>) and signature ("Raunak Banga").
   - Duplicate prevention (updates existing endnote rather than duplicating IDs).
4. Dual Mode: Autonomous Socratic AI generation OR exact custom input injection from prompt.
5. Zero tampering of original student text, preserving 100% academic formatting.
6. Legacy generator, superseded by engine/review (deterministic persona pipeline).
"""

import re
import os
import copy
import zipfile
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional, Union

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
    "THESIS STATEMENTS": "https://knowledge.thinkingstorm.com/PlanningOrganizing/ThesisStatements.aspx",
    "INTRODUCTION": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Introductions.aspx",
    "INTRODUCTIONS": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Introductions.aspx",
    "ORGANISATION": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "ORGANIZATION": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "PLANNING & ORGANIZING": "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx",
    "TOPIC SENTENCE": "https://knowledge.thinkingstorm.com/PlanningOrganizing/TopicSentences.aspx",
    "TOPIC SENTENCES": "https://knowledge.thinkingstorm.com/PlanningOrganizing/TopicSentences.aspx",
    "TRANSITION": "https://knowledge.thinkingstorm.com/ArgumentClarity/Transitions.aspx",
    "TRANSITIONS": "https://knowledge.thinkingstorm.com/ArgumentClarity/Transitions.aspx",
    "ANALYSIS OF EVIDENCE": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx",
    "EVIDENCE": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx",
    "SOURCES & EVIDENCE": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx",
    "ANALYSIS": "https://knowledge.thinkingstorm.com/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "COUNTER-ARGUMENT": "https://knowledge.thinkingstorm.com/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "COUNTERARGUMENT": "https://knowledge.thinkingstorm.com/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "CONCLUSION": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Conclusions.aspx",
    "CONCLUSIONS": "https://knowledge.thinkingstorm.com/PlanningOrganizing/Conclusions.aspx",
    "SUBJECT-VERB AGREEMENT": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation/SubjectVerbAgreement.aspx",
    "PUNCTUATION": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation/Commas.aspx",
    "COMMAS": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation/Commas.aspx",
    "SENTENCE CLARITY": "https://knowledge.thinkingstorm.com/ArgumentClarity/SentenceClarity.aspx",
    "FRAGMENTS": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation.aspx",
    "RUN-ON SENTENCES": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation.aspx",
    "RUN-ONS": "https://knowledge.thinkingstorm.com/GrammarMechanicsandPunctuation.aspx",
    "MLA": "https://knowledge.thinkingstorm.com/APAMLAandChicagoTurabianFormatting.aspx",
    "APA": "https://knowledge.thinkingstorm.com/APAMLAandChicagoTurabianFormatting.aspx",
    "FORMATTING": "https://knowledge.thinkingstorm.com/APAMLAandChicagoTurabianFormatting.aspx",
    "FORMAL WRITING": "https://knowledge.thinkingstorm.com/WritingGuides/FormalWriting.aspx",
    "ABSTRACT": "https://knowledge.thinkingstorm.com/WritingGuides/WritinganAbstract.aspx",
    "STATISTICS": "https://knowledge.thinkingstorm.com/SourcesEvidence.aspx"
}


def extract_student_first_name(text_or_paragraphs: Union[str, List[str]], default: str = "Student") -> str:
    """
    Detects the student's first name from the manuscript header (MLA/APA format).
    """
    if isinstance(text_or_paragraphs, str):
        lines = [l.strip() for l in text_or_paragraphs.splitlines() if l.strip()]
    else:
        lines = [p.strip() for p in text_or_paragraphs if p.strip()]

    if not lines:
        return default

    disallowed = {
        "abstract", "essay", "introduction", "title", "department", "university",
        "college", "professor", "dr.", "dr", "table", "running", "head", "target", "prompt"
    }

    # Inspect first 4 non-empty lines
    for line in lines[:4]:
        words = line.split()
        if 1 <= len(words) <= 4:
            first_w_clean = re.sub(r'[^a-zA-Z]', '', words[0])
            if first_w_clean.lower() not in disallowed and len(first_w_clean) >= 2:
                # Check that second word (if present) also doesn't violate
                if len(words) > 1 and words[1].lower() in disallowed:
                    continue
                return first_w_clean.capitalize()

    return default


def parse_custom_comments_text(raw_text: str) -> List[Dict[str, str]]:
    """
    Parses flexible custom comment specifications matching the SOP helper prompt:
    e.g.:
    Quote: "Eliminating tuition would have a huge..."
    Feedback: THESIS STATEMENT Your thesis outlines your broad topic...

    Or:
    "Quoted sentence" -> Feedback text
    """
    comments = []
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    current_quote = None
    current_feedback = None

    for line in lines:
        if line.upper().startswith("COMMENTS TO ADD"):
            continue

        q_match = re.match(r'^(?:Quote|Quoted|Target|Text)\s*:\s*["\']?(.*?)["\']?$', line, re.IGNORECASE)
        f_match = re.match(r'^(?:Feedback|Comment|Note)\s*:\s*(.*)$', line, re.IGNORECASE)

        if q_match:
            if current_quote and current_feedback:
                comments.append((current_quote, current_feedback))
                current_feedback = None
            current_quote = q_match.group(1).strip().strip('"').strip("'")
        elif f_match:
            current_feedback = f_match.group(1).strip()
            if current_quote and current_feedback:
                comments.append((current_quote, current_feedback))
                current_quote = None
                current_feedback = None
        elif "->" in line:
            parts = line.split("->", 1)
            q = parts[0].strip().strip('"').strip("'")
            fb = parts[1].strip()
            if q and fb:
                comments.append((q, fb))
        elif line.startswith('"') and '"' in line[1:]:
            parts = line.split('"', 2)
            q = parts[1].strip()
            fb = parts[2].strip(" :->")
            if q and fb:
                comments.append((q, fb))

    if current_quote and current_feedback:
        comments.append((current_quote, current_feedback))

    # Normalize category, link, and comment text
    structured = []
    for q, fb in comments:
        matched_cat = None
        fb_clean = fb

        # 1. Check if comment begins with an ALL CAPS category
        for cat in sorted(THINKINGSTORM_KNOWLEDGE_BASE.keys(), key=len, reverse=True):
            if fb.upper().startswith(cat):
                matched_cat = cat
                fb_clean = fb[len(cat):].strip(" :->")
                break

        # 2. Check if category was specified in parentheses or brackets
        if not matched_cat:
            m = re.match(r'^\[([A-Z\s\-&]+)\]\s*(.*)$', fb)
            if m and m.group(1).strip() in THINKINGSTORM_KNOWLEDGE_BASE:
                matched_cat = m.group(1).strip()
                fb_clean = m.group(2).strip()

        # 3. Fallback inference based on diagnostic content
        if not matched_cat:
            fb_low = fb.lower()
            if "thesis" in fb_low:
                matched_cat = "THESIS STATEMENT"
            elif "intro" in fb_low or "hook" in fb_low:
                matched_cat = "INTRODUCTION"
            elif "conclu" in fb_low:
                matched_cat = "CONCLUSION"
            elif "comma" in fb_low or "punctuation" in fb_low:
                matched_cat = "COMMAS"
            elif "run-on" in fb_low:
                matched_cat = "RUN-ON SENTENCES"
            elif "fragment" in fb_low:
                matched_cat = "FRAGMENTS"
            elif "evidence" in fb_low or "statistic" in fb_low or "data" in fb_low or "study" in fb_low:
                matched_cat = "ANALYSIS OF EVIDENCE"
            elif "transition" in fb_low:
                matched_cat = "TRANSITION"
            elif "topic sentence" in fb_low:
                matched_cat = "TOPIC SENTENCE"
            elif "mla" in fb_low:
                matched_cat = "MLA"
            elif "apa" in fb_low:
                matched_cat = "APA"
            elif "subject-verb" in fb_low or "agreement" in fb_low:
                matched_cat = "SUBJECT-VERB AGREEMENT"
            else:
                matched_cat = "SENTENCE CLARITY"

        link = THINKINGSTORM_KNOWLEDGE_BASE.get(
            matched_cat,
            "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx"
        )

        structured.append({
            "target_text": q,
            "category": matched_cat,
            "comment_text": fb_clean,
            "link_url": link
        })

    return structured


def parse_custom_endnote_text(raw_endnote: str, student_first_name: str = "Student", reviewer_name: str = "Raunak Banga") -> List[str]:
    """
    Cleans and structures an endnote text, replacing placeholders and ensuring signature.
    """
    text = raw_endnote.strip()
    if text.upper().startswith("ENDNOTE TO ADD:"):
        text = text[len("ENDNOTE TO ADD:"):].strip()

    # Dynamic replacement of student first name
    text = re.sub(r'<\s*Student\s+first\s+name\s*>', student_first_name, text, flags=re.IGNORECASE)

    # Split into clean paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    # Ensure reviewer signature is at the end
    if paragraphs and not paragraphs[-1].lower().endswith(reviewer_name.lower()):
        paragraphs.append(reviewer_name)

    return paragraphs


class ThinkingStormAutomator:
    def __init__(self, reviewer_name: str = "Raunak Banga", initials: str = "RB"):
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

        first_name = extract_student_first_name(paragraphs, default=student_name.split()[0] if student_name else "Student")
        comments = []

        # 1. Introduction & Thesis Check
        if len(paragraphs) >= 1:
            p0 = paragraphs[0]
            # Opening hook
            if any(w in p0.lower() for w in ["everyone", "throughout history", "since the beginning", "in today's society", "all people"]):
                comments.append({
                    "target_text": p0[:80],
                    "category": "INTRODUCTION",
                    "comment_text": "The opening is too general to engage readers. What personal experience or concrete realization drew you to this topic, and how can you use it to create a more focused hook?",
                    "link_url": THINKINGSTORM_KNOWLEDGE_BASE["INTRODUCTION"]
                })
            # Thesis statement
            comments.append({
                "target_text": p0[-120:] if len(p0) > 120 else p0,
                "category": "THESIS STATEMENT",
                "comment_text": "Your thesis outlines your broad topic, but could be tighter. Make sure your thesis explicitly previews the major analytical points your body paragraphs will explore.",
                "link_url": THINKINGSTORM_KNOWLEDGE_BASE["THESIS STATEMENT"]
            })

        # 2. Body Paragraph Diagnostics
        for idx, p in enumerate(paragraphs[1:-1], start=1):
            p_low = p.lower()
            # Evidence without analysis
            if any(k in p_low for k in ["study", "found that", "percent", "%", "according to", "stated", "statistics", "data"]):
                if not any(c["category"] == "ANALYSIS OF EVIDENCE" for c in comments):
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
            # Sentence Clarity / Colloquialisms
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

        # 4. 3 Pedagogical Domains for word/endnotes.xml
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

    def _anchor_comment_to_runs(self, p: ET.Element, cid_str: str, target_text: str) -> bool:
        """
        Anchors commentRangeStart and commentRangeEnd strictly around target_text
        by splitting runs in paragraph <w:p> so ONLY the quoted words are highlighted,
        never the full paragraph.
        """
        # Build list of text-bearing runs and their character spans
        children = list(p)
        full_text = ""
        for child in children:
            if child.tag == f"{{{W_NS}}}r":
                t_elem = child.find(f"{{{W_NS}}}t")
                if t_elem is not None and t_elem.text:
                    full_text += t_elem.text

        if not full_text:
            return False

        # Locate target in paragraph
        target_pos = full_text.find(target_text)
        if target_pos == -1:
            target_lower = target_text.lower()
            full_lower = full_text.lower()
            target_pos = full_lower.find(target_lower)
            if target_pos == -1:
                # Substring fallback (first 35 chars)
                sub_target = target_lower[:35].strip()
                target_pos = full_lower.find(sub_target)
                if target_pos != -1:
                    target_len = len(sub_target)
                else:
                    return False
            else:
                target_len = len(target_text)
        else:
            target_len = len(target_text)

        match_start = target_pos
        match_end = target_pos + target_len

        # Reconstruct children with exact run splits
        new_children = []
        curr_offset = 0
        start_anchor_inserted = False
        end_anchor_inserted = False

        for child in children:
            if child.tag != f"{{{W_NS}}}r":
                new_children.append(child)
                continue

            t_elem = child.find(f"{{{W_NS}}}t")
            if t_elem is None or not t_elem.text:
                new_children.append(child)
                continue

            r_text = t_elem.text
            r_start = curr_offset
            r_end = curr_offset + len(r_text)
            curr_offset = r_end

            # Run is entirely before match
            if r_end <= match_start:
                new_children.append(child)
                continue

            # Run is entirely after match
            if r_start >= match_end:
                new_children.append(child)
                continue

            # Determine splits within this run
            splits = []
            if r_start < match_start < r_end:
                splits.append(match_start - r_start)
            if r_start < match_end < r_end:
                splits.append(match_end - r_start)
            splits = sorted(list(set(splits)))

            slices = []
            last_s = 0
            for s in splits:
                slices.append((r_text[last_s:s], r_start + last_s, r_start + s))
                last_s = s
            slices.append((r_text[last_s:], r_start + last_s, r_end))

            for sub_text, sub_start, sub_end in slices:
                if not sub_text:
                    continue

                if sub_start == match_start and not start_anchor_inserted:
                    c_start = ET.Element(f"{{{W_NS}}}commentRangeStart", {f"{{{W_NS}}}id": cid_str})
                    new_children.append(c_start)
                    start_anchor_inserted = True

                new_r = copy.deepcopy(child)
                new_t = new_r.find(f"{{{W_NS}}}t")
                new_t.text = sub_text
                new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                new_children.append(new_r)

                if sub_end == match_end and not end_anchor_inserted:
                    c_end = ET.Element(f"{{{W_NS}}}commentRangeEnd", {f"{{{W_NS}}}id": cid_str})
                    new_children.append(c_end)

                    ref_run = ET.Element(f"{{{W_NS}}}r")
                    rPr = ET.SubElement(ref_run, f"{{{W_NS}}}rPr")
                    ET.SubElement(rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "CommentReference"})
                    ET.SubElement(ref_run, f"{{{W_NS}}}commentReference", {f"{{{W_NS}}}id": cid_str})
                    new_children.append(ref_run)
                    end_anchor_inserted = True

        p.clear()
        for c in new_children:
            p.append(c)

        return start_anchor_inserted and end_anchor_inserted

    def generate_reviewed_docx(
        self,
        input_docx: str,
        output_docx: str,
        student_name: str = "Student",
        custom_comments: Optional[List[Dict[str, str]]] = None,
        custom_domains: Optional[Dict[str, str]] = None,
        custom_endnote_text: Optional[str] = None
    ) -> str:
        """
        Takes an input docx, analyzes it (or uses custom comments & endnotes), and generates
        a complete ThinkingStorm/Trivium deliverable with native comments and endnotes.
        """
        # Read text for analysis and student name detection
        doc = docx.Document(input_docx)
        paras_text = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paras_text)

        detected_first_name = extract_student_first_name(paras_text, default=student_name.split()[0] if student_name else "Student")

        if custom_comments is not None:
            comments = custom_comments
        else:
            comments, _ = self.analyze_manuscript(full_text, student_name=detected_first_name)

        # Prepare endnote paragraphs
        if custom_endnote_text:
            endnote_paragraphs = parse_custom_endnote_text(
                custom_endnote_text,
                student_first_name=detected_first_name,
                reviewer_name=self.reviewer_name
            )
        elif custom_domains is not None:
            endnote_paragraphs = [
                f"Dear {detected_first_name},",
                "Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:"
            ]
            for domain_title, domain_body in custom_domains.items():
                endnote_paragraphs.append(f"{domain_title}:")
                endnote_paragraphs.append(sanitize_ai_vocabulary(domain_body))
            endnote_paragraphs.extend([
                "I hope you find the feedback helpful.",
                "All the best.",
                self.reviewer_name
            ])
        else:
            _, default_domains = self.analyze_manuscript(full_text, student_name=detected_first_name)
            endnote_paragraphs = [
                f"Dear {detected_first_name},",
                "Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:"
            ]
            for domain_title, domain_body in default_domains.items():
                endnote_paragraphs.append(f"{domain_title}:")
                endnote_paragraphs.append(sanitize_ai_vocabulary(domain_body))
            endnote_paragraphs.extend([
                "I hope you find the feedback helpful.",
                "All the best.",
                self.reviewer_name
            ])

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

            # 1. Parse document.xml and apply sentence-level comment anchors
            tree = ET.parse(doc_xml_p)
            root = tree.getroot()

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            created_comments = []
            rel_hyperlinks = []

            # Preserve existing comments if present and avoid ID collisions
            if comments_xml_p.exists():
                try:
                    c_tree = ET.parse(str(comments_xml_p))
                    c_root = c_tree.getroot()
                except Exception:
                    c_root = ET.Element(f"{{{W_NS}}}comments")
            else:
                c_root = ET.Element(f"{{{W_NS}}}comments")

            existing_ids = []
            for c in c_root.findall(f"{{{W_NS}}}comment"):
                cid_val = c.get(f"{{{W_NS}}}id")
                if cid_val is not None and cid_val.isdigit():
                    existing_ids.append(int(cid_val))
            for cr in root.findall(f".//{{{W_NS}}}commentRangeStart"):
                cid_val = cr.get(f"{{{W_NS}}}id")
                if cid_val is not None and cid_val.isdigit():
                    existing_ids.append(int(cid_val))

            comment_id = max(existing_ids) + 1 if existing_ids else 0

            for item in comments:
                target = item.get("target_text", "").strip()
                cat = item.get("category", "FEEDBACK").strip().upper()
                msg = sanitize_ai_vocabulary(item.get("comment_text", "").strip())
                link = item.get("link_url", THINKINGSTORM_KNOWLEDGE_BASE.get(cat, "https://knowledge.thinkingstorm.com/PlanningOrganizing.aspx"))

                anchored = False
                for p in root.findall(f".//{{{W_NS}}}p"):
                    p_text = "".join(p.itertext()).strip()
                    if target and (target in p_text or target[:30] in p_text):
                        cid_str = str(comment_id)
                        anchored = self._anchor_comment_to_runs(p, cid_str, target)
                        if anchored:
                            break

                # Fallback if exact run split could not locate target: anchor to first non-empty paragraph
                if not anchored:
                    cid_str = str(comment_id)
                    all_ps = root.findall(f".//{{{W_NS}}}p")
                    for p in all_ps:
                        p_t = "".join(p.itertext()).strip()
                        if p_t:
                            # Split around first sentence
                            first_sentence = p_t.split(".")[0]
                            if first_sentence:
                                self._anchor_comment_to_runs(p, cid_str, first_sentence)
                            break

                # Build native comment XML node
                cid_str = str(comment_id)
                r_id_str = f"rIdCommLink{comment_id}"

                c_elem = ET.Element(f"{{{W_NS}}}comment", {
                    f"{{{W_NS}}}id": cid_str,
                    f"{{{W_NS}}}author": self.reviewer_name,
                    f"{{{W_NS}}}date": now_iso,
                    f"{{{W_NS}}}initials": self.initials
                })
                cp = ET.SubElement(c_elem, f"{{{W_NS}}}p")
                cpPr = ET.SubElement(cp, f"{{{W_NS}}}pPr")
                ET.SubElement(cpPr, f"{{{W_NS}}}pStyle", {f"{{{W_NS}}}val": "CommentText"})

                # Annotation reference run
                ref_r = ET.SubElement(cp, f"{{{W_NS}}}r")
                ref_rPr = ET.SubElement(ref_r, f"{{{W_NS}}}rPr")
                ET.SubElement(ref_rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "CommentReference"})
                ET.SubElement(ref_r, f"{{{W_NS}}}annotationRef")

                # Clickable category hyperlink
                chlink = ET.SubElement(cp, f"{{{W_NS}}}hyperlink", {f"{{{R_NS}}}id": r_id_str, f"{{{W_NS}}}history": "1"})
                chr_node = ET.SubElement(chlink, f"{{{W_NS}}}r")
                chrPr = ET.SubElement(chr_node, f"{{{W_NS}}}rPr")
                ET.SubElement(chrPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "Hyperlink"})
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

            # 2. Check if endnoteReference already exists in document.xml; if not, insert at document end
            body = root.find(f"{{{W_NS}}}body")
            existing_en_ref = root.find(f".//{{{W_NS}}}endnoteReference")
            if existing_en_ref is None:
                endnote_p = ET.SubElement(body, f"{{{W_NS}}}p")
                endnote_r = ET.SubElement(endnote_p, f"{{{W_NS}}}r")
                endnote_rPr = ET.SubElement(endnote_r, f"{{{W_NS}}}rPr")
                ET.SubElement(endnote_rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "EndnoteReference"})
                ET.SubElement(endnote_r, f"{{{W_NS}}}lastRenderedPageBreak")
                ET.SubElement(endnote_r, f"{{{W_NS}}}endnoteReference", {f"{{{W_NS}}}id": "1"})

            # Save modified document.xml
            tree.write(str(doc_xml_p), encoding="utf-8", xml_declaration=True)

            # 3. Append to word/comments.xml
            for c in created_comments:
                c_root.append(c)
            ET.ElementTree(c_root).write(str(comments_xml_p), encoding="utf-8", xml_declaration=True)

            # 4. Append to word/_rels/comments.xml.rels
            if comments_rels_p.exists():
                try:
                    crels_tree = ET.parse(str(comments_rels_p))
                    crels_root = crels_tree.getroot()
                except Exception:
                    crels_root = ET.Element(f"{{{PKG_REL_NS}}}Relationships")
            else:
                crels_root = ET.Element(f"{{{PKG_REL_NS}}}Relationships")

            existing_rel_ids = {r.get("Id") for r in crels_root.findall(f"{{{PKG_REL_NS}}}Relationship")}
            for rid, url in rel_hyperlinks:
                if rid not in existing_rel_ids:
                    ET.SubElement(crels_root, f"{{{PKG_REL_NS}}}Relationship", {
                        "Id": rid,
                        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                        "Target": url,
                        "TargetMode": "External"
                    })
                    existing_rel_ids.add(rid)
            ET.ElementTree(crels_root).write(str(comments_rels_p), encoding="utf-8", xml_declaration=True)

            # 5. Build/Update word/endnotes.xml with EXACT Typography (Times New Roman, 12pt, 2.0 Spacing, Red text)
            if endnotes_xml_p.exists():
                try:
                    en_tree = ET.parse(str(endnotes_xml_p))
                    en_root = en_tree.getroot()
                except Exception:
                    en_root = ET.Element(f"{{{W_NS}}}endnotes")
            else:
                en_root = ET.Element(f"{{{W_NS}}}endnotes")
                # Separators
                en_sep = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}type": "separator", f"{{{W_NS}}}id": "-1"})
                sep_p = ET.SubElement(en_sep, f"{{{W_NS}}}p")
                ET.SubElement(ET.SubElement(sep_p, f"{{{W_NS}}}r"), f"{{{W_NS}}}separator")

                en_cont = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}type": "continuationSeparator", f"{{{W_NS}}}id": "0"})
                cont_p = ET.SubElement(en_cont, f"{{{W_NS}}}p")
                ET.SubElement(ET.SubElement(cont_p, f"{{{W_NS}}}r"), f"{{{W_NS}}}continuationSeparator")

            # Check if Endnote 1 already exists: update it to avoid duplicate IDs
            en1 = None
            for en in en_root.findall(f"{{{W_NS}}}endnote"):
                if en.get(f"{{{W_NS}}}id") == "1":
                    en1 = en
                    break

            if en1 is not None:
                # Clear existing content of endnote 1
                en1.clear()
                en1.set(f"{{{W_NS}}}id", "1")
            else:
                en1 = ET.SubElement(en_root, f"{{{W_NS}}}endnote", {f"{{{W_NS}}}id": "1"})

            # Populate paragraphs with Times New Roman, 12pt, 2.0 line spacing, and red text
            for idx, p_text in enumerate(endnote_paragraphs):
                p_elem = ET.SubElement(en1, f"{{{W_NS}}}p")
                pPr = ET.SubElement(p_elem, f"{{{W_NS}}}pPr")
                ET.SubElement(pPr, f"{{{W_NS}}}pStyle", {f"{{{W_NS}}}val": "EndnoteText"})
                # 2.0 Line Spacing (480)
                ET.SubElement(pPr, f"{{{W_NS}}}spacing", {f"{{{W_NS}}}line": "480", f"{{{W_NS}}}lineRule": "auto"})

                # Default paragraph run properties: Times New Roman, 12pt, Red (FF0000)
                p_rPr = ET.SubElement(pPr, f"{{{W_NS}}}rPr")
                ET.SubElement(p_rPr, f"{{{W_NS}}}rFonts", {
                    f"{{{W_NS}}}ascii": "Times New Roman",
                    f"{{{W_NS}}}hAnsi": "Times New Roman",
                    f"{{{W_NS}}}cs": "Times New Roman"
                })
                ET.SubElement(p_rPr, f"{{{W_NS}}}color", {f"{{{W_NS}}}val": "FF0000"})
                ET.SubElement(p_rPr, f"{{{W_NS}}}sz", {f"{{{W_NS}}}val": "24"})
                ET.SubElement(p_rPr, f"{{{W_NS}}}szCs", {f"{{{W_NS}}}val": "24"})

                # First paragraph gets native endnoteRef
                if idx == 0:
                    ref_r = ET.SubElement(p_elem, f"{{{W_NS}}}r")
                    ref_rPr = ET.SubElement(ref_r, f"{{{W_NS}}}rPr")
                    ET.SubElement(ref_rPr, f"{{{W_NS}}}rStyle", {f"{{{W_NS}}}val": "EndnoteReference"})
                    ET.SubElement(ref_r, f"{{{W_NS}}}endnoteRef")

                # Determine if bold (greeting, domain titles, or signature)
                is_bold = (
                    idx == 0 or
                    p_text.endswith(":") or
                    p_text.lower() == self.reviewer_name.lower() or
                    p_text.startswith("Dear ")
                )

                text_r = ET.SubElement(p_elem, f"{{{W_NS}}}r")
                text_rPr = ET.SubElement(text_r, f"{{{W_NS}}}rPr")
                ET.SubElement(text_rPr, f"{{{W_NS}}}rFonts", {
                    f"{{{W_NS}}}ascii": "Times New Roman",
                    f"{{{W_NS}}}hAnsi": "Times New Roman",
                    f"{{{W_NS}}}cs": "Times New Roman"
                })
                ET.SubElement(text_rPr, f"{{{W_NS}}}color", {f"{{{W_NS}}}val": "FF0000"})
                ET.SubElement(text_rPr, f"{{{W_NS}}}sz", {f"{{{W_NS}}}val": "24"})
                ET.SubElement(text_rPr, f"{{{W_NS}}}szCs", {f"{{{W_NS}}}val": "24"})
                if is_bold:
                    ET.SubElement(text_rPr, f"{{{W_NS}}}b")
                    ET.SubElement(text_rPr, f"{{{W_NS}}}bCs")

                t_node = ET.SubElement(text_r, f"{{{W_NS}}}t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
                t_node.text = f" {p_text}" if idx == 0 else p_text

            ET.ElementTree(en_root).write(str(endnotes_xml_p), encoding="utf-8", xml_declaration=True)

            # 6. Update word/_rels/document.xml.rels
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

            # 7. Update [Content_Types].xml
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

            # 8. Repack docx
            output_p = Path(output_docx)
            output_p.parent.mkdir(parents=True, exist_ok=True)
            if output_p.exists():
                output_p.unlink()

            shutil.make_archive(str(temp_dir / "res"), 'zip', temp_dir)
            shutil.move(str(temp_dir / "res.zip"), str(output_p))
            return str(output_p)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
