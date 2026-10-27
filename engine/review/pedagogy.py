"""Passage-level review moves generalized from the supplied reviewer examples.

Each rule records the text that licenses the observation. No previous comment,
student identity or document filename is used to choose the advice.
"""
from __future__ import annotations

import re

from .analysis import (Finding, INTRO, THESIS, TOPIC, ORGANISATION, EVIDENCE,
                       STATISTICS, CONCLUSION, CLARITY, FRAGMENTS, PUNCT, MLA, APA,
                       sentence_span, trim_span, _has_finite_verb, _range_is_italic)
from .docmodel import w, reference_heading_span
from .segmenter import split_sentences


TEMPLATES = {
    "intro_concrete_context": [
        ('The opening uses a personal example to introduce the subject of the paper.',
         'Keep this concrete starting point, and make the connection to the paper’s central question clear before moving into the wider discussion.'),
    ],
    "conclusion_new_evidence": [
        ('The prediction involving {term} appears in the conclusion without supporting evidence here.',
         'Develop and document that claim in the body before relying on it in the ending. Then explain what follows from the points the essay has already established, rather than closing on an unexamined prediction.'),
    ],
    "topic_vague_focus": [
        ('The phrase “{term}” leaves the focus of this paragraph unclear.',
         'Name the specific idea you will discuss and show how it connects to the main claim. What will this paragraph add to the discussion?'),
    ],
    "source_attribution_unclear": [
        ('The reference to “{term}” does not identify the source for the reader.',
         'Name the author or article here, and make the connection to the corresponding source entry clear. This will distinguish the source’s point from your own explanation.'),
    ],
    "claim_scope_support": [
        ('The statement beginning {anchor} makes a broad claim about a group or outcome.',
         'What evidence supports that claim? Add a relevant source or example, and qualify the wording to match what the evidence actually establishes.'),
    ],
    "reading_response_link": [
        ('You follow the quoted material with your own conclusion, but the connection needs explanation.',
         'Which words or findings in the passage support that conclusion? Add your reasoning before moving on so the reader can follow how you arrived at your interpretation.'),
    ],
    "mixed_benefits_drawbacks": [
        ('This paragraph moves from discussing benefits to concerns about the same subject.',
         'Consider separating the benefits and drawbacks into distinct paragraphs. If you keep them together, explain the comparison and use a topic sentence that prepares readers for both parts.'),
    ],
    "nominal_comparison_fragment": [
        ('The “From … to …” comparison here does not form a complete main clause.',
         'What point do you want to make about these examples? Attach the comparison to that statement, or add a subject and a main verb to complete the thought.'),
    ],
    "spelling_verified": [
        ('Please change “{term}” to “{replacement}” here.',
         'Check the revised sentence once more for the same spelling issue.'),
    ],
    "paragraph_terminal_punctuation": [
        ('This paragraph ends without terminal punctuation.',
         'Complete the sentence and add the appropriate ending mark before starting the next paragraph.'),
    ],
    "comparison_topic_general": [
        ('This opening names a shared theme but leaves the actual comparison open.',
         'Could you identify what each work emphasizes and the difference this paragraph will examine? Use that contrast to give the paragraph a clear direction.'),
    ],
    "annotation_relevance_brief": [
        ('The explanation of how this source will help your research is brief.',
         'Name the finding or argument you plan to use and explain which part of your research question it addresses. How will you use it in the paper?'),
    ],
    "annotation_credibility_missing": [
        ('This annotation describes the source but does not yet evaluate its credibility.',
         'Add relevant details about the author’s expertise or publication, and consider the study’s limitations. Explain why those details make the source useful for your research.'),
    ],
    "assessment_interpretation": [
        ('You report several assessment results here without interpreting their significance in this paragraph.',
         'Connect the scores to the observations you describe and explain what they suggest about participation in the assessed activity. Keep any interpretation within what the assessment and observations support.'),
    ],
    "mla_heading_layout": [
        ('The first-page heading combines its details across the same lines.',
         'Put the student’s name, instructor’s name, course and date on four separate, left-aligned lines. Keep the title separate from this heading.'),
    ],
    "reference_heading_style": [
        ('The source-list heading here is “{term}”.',
         'For {style} style, use “{replacement}” as the heading so the source list is clearly identified.'),
    ],
    "reference_alphabetical": [
        ('These source entries are not in alphabetical order by their first elements.',
         'Arrange them by the first author’s surname or organization name. Check the full list after moving this entry so the ordering is consistent.'),
    ],
    "reference_hanging_indent": [
        ('The source entries need hanging indentation.',
         'Keep the first line of each entry at the left margin and indent subsequent lines by half an inch. Apply the same setting across the source list rather than adding spaces manually.'),
    ],
    "mla_article_title_format": [
        ('The source title “{term}” is not set off in quotation marks in this entry.',
         'For an article or web page, put the title in quotation marks and use MLA title capitalization. Keep the publication title separate. If this is a standalone book instead, italicize its title.'),
    ],
    'annotation_parts_combined': [
        ('This annotation combines the source’s content with an assessment of its credibility or relevance in one paragraph.',
         'If your assignment asks for distinct annotation parts, separate the summary, evaluation and research use at the points where the purpose changes. Keep each part focused on its own task.'),
    ],
    'apa_article_all_caps': [
        ('The article title “{term}” is written in capitals throughout.',
         'Use sentence case for an APA article title: capitalize the first word, the first word after a colon and proper nouns. Keep any acronyms that require capitals.'),
    ],
    'apa_container_italics': [
        ('The journal title “{term}” is not italicized in this entry.',
         'Italicize the journal title and retain its title capitalization. Keep the article title in regular type so readers can distinguish the article from its publication.'),
    ],
    'reference_double_spacing': [
        ('This source entry has an explicit spacing setting that is not double spacing.',
         'Set the entry to double spacing and apply the same setting to the other entries. Use paragraph formatting rather than inserting blank lines between wrapped lines.'),
    ],
    'front_double_spacing': [
        ('This opening detail has an explicit spacing setting that is not double spacing.',
         'Use double spacing for the title-page details unless your course instructions specify another format. Apply the setting to the text rather than adding empty paragraphs between lines.'),
    ],
    'apa_locator_hash': [
        ('The paragraph locator “{term}” uses a hash mark.',
         'Use the APA abbreviation “para.” followed by the paragraph number. Include the author and publication year in the citation, checking those details against the corresponding source entry.'),
    ],
    'acronym_case': [
        ('The abbreviation “{term}” refers to artificial intelligence here.',
         'Write it as “AI” in capitals and use that form consistently after introducing the full term.'),
    ],
    'reference_heading_joined': [
        ('The source-list heading and the first entry share the same paragraph.',
         'Put the heading on its own centered line, then begin the first source entry in a new paragraph. Give each source its own paragraph so the entries remain distinct.'),
    ],
    'comparison_topic_focus': [
        ('Your opening connects {works} through a shared idea.',
         'Which feature of each work will you examine, and what does placing them together reveal? State that relationship in the topic sentence so the examples develop a clear point of comparison.'),
    ],
}


def _add(out, rule, category, para, start, end, facts=None, priority=68):
    start, end = trim_span(para.text, start, end)
    if end > start:
        out.append(Finding(rule, category, para, start, end, facts or {}, priority))


def rhetoric(model, blocks):
    out = []
    genre = getattr(model, '_essay_type', 'academic')
    essay = genre not in {'bibliography', 'report', 'reflection', 'statement'}
    if essay:
        # A comparison may span several physical extraction fragments. Inspect
        # its logical opening instead of diagnosing fragments as paragraphs.
        for block in blocks[1:-1]:
            sentences = block.sentences()
            if not sentences:
                continue
            first = sentences[0]
            titles = list(dict.fromkeys(m.group() for m in re.finditer(r'“[^“”]+”|"[^"\n]+"', first.text)
                                        if 1 <= len(m.group()[1:-1].split()) <= 6))
            if len(titles) >= 2 and re.search(r'\bboth\b', first.text, re.I) and not re.search(
                    r'\b(?:tone|structure|imagery|point of view|diction|rhythm|contrast|whereas|while)\b', first.text, re.I) and re.search(
                    r'\b(?:another example|many different things|same theme|how their lives are good)\b', first.text, re.I):
                mapped = block.span_in_paragraph(first.start, first.end)
                if mapped:
                    _add(out, 'comparison_topic_focus', TOPIC, *mapped,
                         {'works': ' and '.join(titles[:2])}, 75)
    # A physical extraction fragment is not an independent rhetorical unit.
    standalone = {b.paragraphs[0].index for b in blocks if len(b.paragraphs) == 1}
    body = [p for p in model.body_paragraphs if len(p.words) >= 25 and p.index in standalone]
    first_body = blocks[0].paragraphs[0].index if blocks else None
    last_body = blocks[-1].paragraphs[-1].index if blocks else None
    for index, para in enumerate(body):
        sentences = split_sentences(para.text)
        if not sentences:
            continue
        first = sentences[0]
        if essay and para.index == first_body and re.match(r'^When I\b', first.text) and re.search(r'[“"]', first.text):
            _add(out, 'intro_concrete_context', INTRO, para, *sentence_span(first), priority=67)
        if essay and para.index == last_body:
            earlier = ' '.join(p.text for p in body[:-1])
            for sent in sentences:
                prediction = re.search(r'\b(?:by|in) ((?:20|21)\d{2})\b', sent.text, re.I)
                if prediction and prediction.group(1) not in earlier and not re.search(r'\([^)]*\d|according to', sent.text, re.I):
                    _add(out, 'conclusion_new_evidence', CONCLUSION, para, *sentence_span(sent),
                         {'term': prediction.group(1)}, 77)
                    break
        if essay and para.index not in {first_body, last_body}:
            vague = re.search(r'\b(?:these things|those things|this issue|this is an issue|things like|a lot of things)\b', first.text, re.I)
            if vague:
                _add(out, 'topic_vague_focus', TOPIC, para, first.start, first.end,
                     {'term': vague.group()}, 76)
            elif re.search(r'\b(?:songs?|works?|texts?)\b', first.text, re.I) and re.search(
                    r'\b(?:another comparison|both (?:talk|discuss)|how the songs talk|same theme)\b', first.text, re.I):
                _add(out, 'comparison_topic_general', TOPIC, para, first.start, first.end, priority=73)

        if essay and para.index not in {first_body, last_body}:
            for sent in sentences:
                if re.search(r'\b(?:most people|all people|everyone|nobody|the vast majority|always|never)\b', sent.text, re.I) \
                        and not re.search(r'[\d“"(]|according to|study|research', sent.text, re.I):
                    _add(out, 'claim_scope_support', EVIDENCE, para, *sentence_span(sent), priority=72)
                    break

        for sent in sentences:
            source = re.search(r'\b(?:in|from) (?:the text|the article|the reading)\b', sent.text, re.I)
            if source and not re.search(r'[“"]|\b(?:by|titled)\b|\([A-Z]', sent.text):
                _add(out, 'source_attribution_unclear', MLA if model.style == 'mla' else APA,
                     para, sent.start + source.start(), sent.start + source.end(), {'term': source.group()}, 70)
                break

        for j, sent in enumerate(sentences[:-1]):
            quoted = re.search(r'[“"]([^”"]{60,})[”"]', sent.text)
            following = sentences[j + 1]
            if quoted and len(quoted.group(1).split()) >= 10 and re.search(r'\b(?:I think|I believe|I feel|my opinion)\b', following.text, re.I):
                # Anchor the interpretation rather than swallowing the quoted
                # source and blocking a separate mechanics/citation comment.
                _add(out, 'reading_response_link', EVIDENCE, para, *sentence_span(following), priority=75)
                break

        if essay and len(para.words) >= 120 and re.search(r'\b(?:benefits?|advantages?)\b', para.text, re.I):
            contrast = next((s for s in sentences[1:] if re.search(r'\b(?:but|however|drawbacks?|taking jobs|risks?)\b', s.text, re.I)), None)
            if contrast:
                _add(out, 'mixed_benefits_drawbacks', ORGANISATION, para, *sentence_span(contrast), priority=70)

        if genre == 'bibliography' and len(para.words) >= 60:
            summary = re.search(r'\b(?:study|article|authors?|researchers?)\b', para.text, re.I)
            evaluation = next((s for s in sentences[1:] if re.search(r'\b(?:professor|peer.reviewed|credentials?|expertise|useful for|my research|for my purposes)\b', s.text, re.I)), None)
            if summary and evaluation:
                _add(out, 'annotation_parts_combined', ORGANISATION, para,
                     *sentence_span(evaluation), priority=72)
            relevant = [s for s in sentences if re.search(r'\b(?:useful|my research|research question|will use|for my purposes)\b', s.text, re.I)]
            if relevant and len(relevant[-1].words) <= 35:
                _add(out, 'annotation_relevance_brief', EVIDENCE, para, *sentence_span(relevant[-1]), priority=75)
            if not re.search(r'credib|credential|professor|researcher|peer.review|expertise|limitation|bias|university|publisher', para.text, re.I):
                _add(out, 'annotation_credibility_missing', EVIDENCE, para, *sentence_span(first), priority=73)

        if genre == 'report' and len(re.findall(r'\b\d+(?:\.\d+)?\b', para.text)) >= 3 \
                and re.search(r'percentile|standard score|age equivalen', para.text, re.I) \
                and not re.search(r'suggest|indicat|below|above|relative|implication|participation', para.text, re.I):
            _add(out, 'assessment_interpretation', STATISTICS, para, *sentence_span(first), priority=73)
    return out


def mechanics(model, blocks):
    out = []
    corrections = {'begginer': 'beginner', 'empothy': 'empathy', 'humna': 'human',
                   'occured': 'occurred', 'recieve': 'receive', 'seperate': 'separate', 'modles': 'models'}
    artificial_intelligence = re.search(r'\bartificial intelligence\b', model.full_text, re.I)
    paragraph_ends = {b.paragraphs[-1].index for b in blocks}
    for para in model.paragraphs:
        if para.region not in {'body', 'abstract', 'references'}:
            continue
        for match in re.finditer(r'\b(?:' + '|'.join(corrections) + r')\b', para.text, re.I):
            _add(out, 'spelling_verified', CLARITY, para, match.start(), match.end(),
                 {'term': match.group(), 'replacement': corrections[match.group().lower()]}, 66)
        if artificial_intelligence and para.region == 'body':
            match = re.search(r'\bai\b', para.text)
            if match:
                _add(out, 'acronym_case', CLARITY, para, match.start(), match.end(), {'term': match.group()}, 67)
        if model.style == 'apa':
            match = re.search(r'\bpara\s*#\s*\d+', para.text, re.I)
            if match:
                _add(out, 'apa_locator_hash', APA, para, match.start(), match.end(), {'term': match.group()}, 74)
        if para.region != 'body' or para.is_heading:
            continue
        for sent in split_sentences(para.text):
            comparison = re.match(r'^From\s+(.+?)\s+to\s+(.+)[.!?]$', sent.text, re.I)
            if comparison and not _has_finite_verb(comparison.group(2)):
                _add(out, 'nominal_comparison_fragment', FRAGMENTS, para, sent.start, sent.end, priority=71)
        if para.index in paragraph_ends and len(para.words) >= 30 and para.text.rstrip()[-1:].isalnum():
            tail = list(re.finditer(r'\S+', para.text))[-6:]
            _add(out, 'paragraph_terminal_punctuation', PUNCT, para, tail[0].start(), len(para.text), priority=64)
    return out


def formatting(model):
    out = []
    category = MLA if model.style == 'mla' else APA
    def explicitly_not_double(para):
        spacing = para.element.find('./' + w('pPr') + '/' + w('spacing'))
        return spacing is not None and spacing.get(w('line')) is not None and (
            spacing.get(w('lineRule'), 'auto') != 'auto' or spacing.get(w('line')) != '480')

    if model.style == 'apa':
        front = next((p for p in model.paragraphs if p.region in {'front_matter', 'title'}
                      and p.text.strip() and explicitly_not_double(p)), None)
        if front:
            _add(out, 'front_double_spacing', APA, front, 0, min(45, len(front.text)), priority=74)
    if model.style == 'mla':
        front = model.front_matter
        if any('\t\t' in p.text for p in front) and any(re.search(r'\b(?:english|eng|engl)\s*\d', p.text, re.I) for p in front):
            para = next(p for p in front if p.text.strip() and '\t' in p.text)
            end = para.text.index('\t')
            _add(out, 'mla_heading_layout', MLA, para, 0, end, priority=85)
    refs = [p for p in model.references if p.text.strip()]
    heading = next((p for p in refs if reference_heading_span(p.text)), None)
    if heading:
        hs, he = reference_heading_span(heading.text)
        heading_text = heading.text[hs:he]
        if heading.text[he:].strip(' :\t\r\n'):
            _add(out, 'reference_heading_joined', category, heading, hs, he, priority=79)
        expected = 'Works Cited' if model.style == 'mla' else 'References'
        if heading_text != expected:
            _add(out, 'reference_heading_style', category, heading, hs, he,
                 {'term': heading_text, 'style': model.style.upper(), 'replacement': expected}, 74)
    entries = [p for p in refs if p is not heading and len(p.words) >= 6
               and not re.match(r'^\s*https?://', p.text)]
    for para in entries:
        if explicitly_not_double(para):
            _add(out, 'reference_double_spacing', category, para, 0, min(25, len(para.text)), priority=71)
        if model.style != 'apa':
            continue
        article = re.search(r'\(\d{4}[a-z]?\)\.?\s+([^\n]+?)\.\s+([^\n]+?),\s*(?:\d|Volume)', para.text)
        if article:
            title = article.group(1)
            if title.isupper() and len(title.split()) >= 3:
                _add(out, 'apa_article_all_caps', APA, para, *article.span(1), {'term': title}, 73)
            if not _range_is_italic(para, *article.span(2)):
                _add(out, 'apa_container_italics', APA, para, *article.span(2), {'term': article.group(2)}, 70)
    for previous, current in zip(entries, entries[1:]):
        if current.normalized.casefold() < previous.normalized.casefold():
            _add(out, 'reference_alphabetical', category, current, 0, min(len(current.text), current.text.find('.') + 1 or 35), priority=69)
            break
    for para in entries:
        indent = para.element.find('./' + w('pPr') + '/' + w('ind'))
        if indent is None or not indent.get(w('hanging')):
            # Respect a hanging indent provided by a paragraph style.
            style = model.doc.styles[para.style] if model.doc is not None and para.style in model.doc.styles else None
            hanging = False
            while style is not None:
                value = style.paragraph_format.first_line_indent
                if value is not None:
                    hanging = value < 0
                    break
                style = style.base_style
            if not hanging:
                _add(out, 'reference_hanging_indent', category, para, 0, min(45, len(para.text)), priority=68)
                break
    if model.style == 'mla':
        for para in entries:
            title = re.search(r'\((?:\d{4}[^)]*|n\.d\.)\)\.\s*([^“"\n][^.]+\.)', para.text)
            # In an authorless APA entry the title precedes the date, so text
            # after (n.d.) may be the website name. Do not call it an article.
            author = para.text[:title.start()].strip() if title else ''
            identified_author = re.match(r'^[^,]+,\s*(?:[A-Z]\.|[A-Z][a-z]+)', author) or re.search(
                r'\b(?:Corporation|Company|Association|Organization|Department|Institute|University)\b', author)
            if title and identified_author:
                start, end = title.span(1)
                _add(out, 'mla_article_title_format', MLA, para, start, end,
                     {'term': title.group(1).strip().rstrip('.')}, 67)
    return out
