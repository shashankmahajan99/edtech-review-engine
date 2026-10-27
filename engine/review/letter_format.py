"""Recognize reviewer letter structure without rewriting its prose."""
import re

PLAIN_HEADINGS = frozenset({
    'thesis', 'thesis statement', 'thesis and focus', 'thesis and overall focus',
    'introduction', 'introduction and thesis', 'abstract', 'evidence', 'analysis',
    'evidence and analysis', 'supporting evidence', 'paragraph focus and connections',
    'organisation', 'organization', 'organisation and flow', 'organization and flow',
    'conclusion', 'conclusion and implications', 'considering another perspective',
    'counterargument', 'counterarguments', 'counterargument and response',
    'sentence clarity', 'grammar and punctuation', 'language and style',
    'citation and document formatting', 'citations and formatting',
    'specific issues and links', 'opening and personal focus', 'programme fit', 'program fit',
})


def is_endnote_heading(text: str) -> bool:
    line = text.strip()
    if not line or '\n' in line or '\r' in line:
        return False
    if line.endswith(':'):
        return True
    normalized = re.sub(r'\s+', ' ', line.casefold().replace('&', ' and '))
    return normalized in PLAIN_HEADINGS


def parse_reviewer_letter(text: str) -> list[str]:
    """Split heading/body lines into native paragraphs; never invent punctuation."""
    paragraphs, pending = [], []

    def flush():
        if pending:
            paragraphs.append('\n'.join(pending).strip())
            pending.clear()

    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = line.strip()
        if not line:
            flush()
        elif is_endnote_heading(line) or (
            not paragraphs and not pending and re.match(r'^Dear\s+\S', line, re.I)
        ):
            flush()
            paragraphs.append(line)
        else:
            pending.append(line)
    flush()
    return paragraphs
