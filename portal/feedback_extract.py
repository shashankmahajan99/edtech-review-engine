"""Read original feedback before Studio removes it from its working copy."""
from __future__ import annotations

import io
import re
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from types import SimpleNamespace

from tools.endnote_extract import body_letter
from engine.review.source_material import previous_letter_start

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
LABEL = (r'THESIS(?: STATEMENT)?|INTRODUCTION|ABSTRACT|CONCLUSION|TOPIC SENTENCES?|TRANSITIONS?|'
         r'ANALYSIS(?: OF EVIDENCE)?|IDEA DEVELOPMENT|ORGANISATION|ORGANIZATION|STRUCTURING|'
         r'ANNOTATED BIBLIOGRAPHY|ANNOTATION|APA|MLA|CHICAGO|FORMATTING|CITATIONS?|IN-TEXT CITATION|'
         r'GRAMMAR|PUNCTUATION|FRAGMENTS|SUBJECT-VERB AGREEMENT|SENTENCE CLARITY|'
         r'CAPITALIZATION|(?:IN)?FORMAL WRITING|REPETITION|STATISTICS?|COUNTER-ARGUMENTS?|'
         r'HOOK STATEMENT|CLARITY|QUOTATIONS?|SENTENCE CONSTRUCTION|PARAGRAPH DEVELOPMENT|'
         r'SUPPORTING EVIDENCE|COMMAS?|PERIOD|RUN-ON SENTENCES?')
HEADING = re.compile(r'^(?:' + LABEL + r')(?:\s*\([^)]*\))?$', re.I)
PREFIX = re.compile(r'^\s*(?:' + LABEL + r')(?:\s*\([^)]*\))?\s*(?::\s*|[-–—]\s*|\n+|$)', re.I)


def paragraph_text(paragraph) -> str:
    return ''.join((node.text or '') if node.tag == W + 't' else
                   '\n' if node.tag in {W + 'br', W + 'cr'} else '\t' if node.tag == W + 'tab' else ''
                   for node in paragraph.iter()).strip()


def paragraphs_text(parent) -> str:
    return '\n\n'.join(text for p in parent.iter(W + 'p') if (text := paragraph_text(p)))


def comment_text(comment) -> str:
    for paragraph in comment.iter(W + 'p'):
        # Strip a linked category at the beginning; keep links inside the advice.
        for child in list(paragraph):
            if child.tag == W + 'pPr':
                continue
            text = paragraph_text(child)
            if not text:
                continue
            if child.tag == W + 'hyperlink' and HEADING.fullmatch(text.strip(' :–—-')):
                paragraph.remove(child)
                continue
            break
    text = paragraphs_text(comment).lstrip(' :–—-\t\r\n')
    return PREFIX.sub('', text, count=1).strip()


def extract_original_feedback(data: bytes, filename: str = '') -> dict:
    with ZipFile(io.BytesIO(data)) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
        comments = []
        count = 0
        if 'word/comments.xml' in archive.namelist():
            root = ET.fromstring(archive.read('word/comments.xml'))
            for comment in root.findall(W + 'comment'):
                count += 1
                if text := comment_text(comment):
                    comments.append(text)

        body = document.find(W + 'body')
        paragraphs = [paragraph_text(p) for p in body.findall(W + 'p') if paragraph_text(p)] if body is not None else []
        candidates = [SimpleNamespace(index=i, text=text, normalized=re.sub(r'\s+', ' ', text))
                      for i, text in enumerate(paragraphs)]
        start = previous_letter_start(candidates)
        letter = body_letter(paragraphs[start:]) if start is not None else ''
        source = 'body_letter' if letter else 'none'
        if not letter and 'word/endnotes.xml' in archive.namelist():
            root = ET.fromstring(archive.read('word/endnotes.xml'))
            notes = [paragraphs_text(note) for note in root.findall(W + 'endnote')
                     if int(note.get(W + 'id', '0')) > 0 and note.get(W + 'type') not in {'separator', 'continuationSeparator'}]
            letter = '\n\n'.join(note for note in notes if note)
            if letter:
                source = 'native_endnotes'
    return {'source_filename': filename, 'comment_count': count,
            'comments_text': '\n\n'.join(comments), 'endnote_text': letter,
            'endnote_source': source}
