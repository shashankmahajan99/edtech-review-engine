"""Studio accessibility and rendering boundaries; behavior is also browser-tested."""
import sys
import unittest
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portal.thinkingstorm_view import get_thinkingstorm_studio_html


class TestStudioLayout(unittest.TestCase):
    def setUp(self):
        self.source = get_thinkingstorm_studio_html()
        self.page = html.fromstring(self.source)

    def test_student_input_has_an_accessible_name(self):
        labels = {label.get("for") for label in self.page.xpath('//label[@for]')}
        for control in self.page.xpath('//input | //select | //textarea'):
            self.assertTrue(control.get("id") in labels or control.get("aria-label"), control.get("id"))

    def test_tabs_point_to_existing_panels_and_have_one_initial_selection(self):
        ids = {node.get("id") for node in self.page.xpath('//*[@id]')}
        self.assertEqual(len(ids), len(self.page.xpath('//*[@id]')), "duplicate element ids")
        for tabs in self.page.xpath('//*[@role="tablist"]'):
            buttons = tabs.xpath('.//*[@role="tab"]')
            self.assertEqual(sum(b.get("aria-selected") == "true" for b in buttons), 1)
            for button in buttons:
                self.assertIn(button.get("aria-controls"), ids)
                self.assertEqual(button.get("type"), "button")

    def test_user_identity_is_escaped_and_not_inserted_as_markup(self):
        markup = get_thinkingstorm_studio_html({"email": '<img src=x onerror="alert(1)">', "full_name": '<script>alert(1)</script>'})
        self.assertNotIn('<img src=x', markup)
        self.assertNotIn('<script>alert(1)</script>', markup)
        self.assertIn('&lt;script&gt;', markup)

    def test_keyboard_navigation_and_error_announcements_exist(self):
        self.assertTrue(self.page.xpath('//a[@href="#mainContent"]'))
        self.assertTrue(self.page.xpath('//*[@id="navToggle"][@aria-expanded="false"]'))
        self.assertTrue(self.page.xpath('//*[@id="inputError"][@role="alert"]'))
        self.assertTrue(self.page.xpath('//*[@id="statusLine"][@aria-live="polite"]'))
        self.assertNotIn('cdn.tailwindcss.com', self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
