import io
from zipfile import ZipFile, ZIP_DEFLATED
from unittest.mock import patch

import docx
from fastapi.testclient import TestClient

from portal.feedback_extract import extract_original_feedback

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def package(paragraphs, comments=None, endnotes=None):
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    original = io.BytesIO()
    document.save(original)
    result = io.BytesIO()
    with ZipFile(original) as source, ZipFile(result, 'w', ZIP_DEFLATED) as target:
        for name in source.namelist():
            target.writestr(name, source.read(name))
        if comments:
            target.writestr('word/comments.xml', comments)
        if endnotes:
            target.writestr('word/endnotes.xml', endnotes)
    return result.getvalue()


def test_original_comments_exclude_headings_and_document_anchors():
    comments = f'''<w:comments xmlns:w="{W}"><w:comment w:id="2"><w:p>
    <w:hyperlink><w:r><w:t>THESIS STATEMENT</w:t></w:r></w:hyperlink>
    <w:r><w:t>Clarify what “these changes” means.</w:t><w:br/><w:t>Explain your reason.</w:t></w:r>
    </w:p><w:p><w:r><w:t>Keep the example.</w:t></w:r></w:p></w:comment>
    <w:comment w:id="3"><w:p><w:r><w:t>APA (References): Use a hanging indent.</w:t></w:r></w:p></w:comment></w:comments>'''
    data = package(['The selected student passage is not feedback.'], comments=comments)
    feedback = extract_original_feedback(data)
    assert feedback['comments_text'] == 'Clarify what “these changes” means.\nExplain your reason.\n\nKeep the example.\n\nUse a hanging indent.'
    assert feedback['comment_count'] == 2
    assert 'selected student passage' not in feedback['comments_text']


def test_native_endnotes_include_positive_ids_and_skip_separators():
    notes = f'''<w:endnotes xmlns:w="{W}">
    <w:endnote w:id="-1" w:type="separator"><w:p><w:r><w:t>Separator</w:t></w:r></w:p></w:endnote>
    <w:endnote w:id="5"><w:p><w:r><w:t>Dear Avery,</w:t></w:r></w:p>
    <w:p><w:r><w:t>Develop the comparison.</w:t></w:r></w:p></w:endnote></w:endnotes>'''
    feedback = extract_original_feedback(package(['Student text.'], endnotes=notes))
    assert feedback['endnote_text'] == 'Dear Avery,\n\nDevelop the comparison.'
    assert feedback['endnote_source'] == 'native_endnotes'


def test_appended_review_letter_is_copied_without_manuscript_or_appendix():
    feedback = extract_original_feedback(package([
        'Student manuscript.', 'Hi Avery,', 'You have done a good job introducing the topic.',
        'There are a few areas to develop in your next draft.', 'Best wishes,', 'Reviewer', 'Formatting appendix.']))
    assert feedback['endnote_text'].startswith('Hi Avery,')
    assert feedback['endnote_text'].endswith('Reviewer')
    assert 'Student manuscript' not in feedback['endnote_text']
    assert 'Formatting appendix' not in feedback['endnote_text']


def test_student_letter_is_not_mistaken_for_reviewer_feedback():
    feedback = extract_original_feedback(package(['Dear Professor,', 'I enjoyed the class discussion.', 'Best wishes,', 'Avery']))
    assert feedback['endnote_text'] == ''
    assert feedback['comments_text'] == ''


def test_embedded_feedback_link_is_preserved():
    comments = f'''<w:comments xmlns:w="{W}"><w:comment w:id="1"><w:p>
    <w:r><w:t>Check the </w:t></w:r><w:hyperlink><w:r><w:t>MLA guide</w:t></w:r></w:hyperlink>
    <w:r><w:t> for this example.</w:t></w:r></w:p></w:comment></w:comments>'''
    feedback = extract_original_feedback(package(['Student text.'], comments=comments))
    assert feedback['comments_text'] == 'Check the MLA guide for this example.'


def test_extraction_endpoint_does_not_require_or_run_a_review():
    from portal.server import app
    client = TestClient(app)
    data = package(['Short document.'])
    with patch('engine.review.pipeline.review_document') as review:
        result = client.post('/api/thinkingstorm/original-feedback', files={'file': ('original.docx', data)})
        assert result.status_code == 200
        assert result.json()['comment_count'] == 0
        assert result.json()['endnote_text'] == ''
        review.assert_not_called()
    invalid = client.post('/api/thinkingstorm/original-feedback', files={'file': ('original.txt', b'text')})
    assert invalid.status_code == 400
