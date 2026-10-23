"""
Automated PII De-identification & Re-identification Engine.
Ensures FERPA-compliant anonymization before text is exposed to LLM pipelines or external reviewers.
"""

import re
from typing import Tuple, Dict


class PIIScrubber:
    def __init__(self):
        # Regular expressions for identifying PII
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
        self.phone_pattern = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
        self.gpa_pattern = re.compile(r'\b(?:GPA\s*(?:of|:)?\s*)(\d\.\d{1,2})\b', re.IGNORECASE)
        self.school_pattern = re.compile(
            r'\b(?:at|from|attending)\s+([A-Z][a-zA-Z\s]+(?:High\s+School|Academy|Collegiate|Grammar\s+School|Institute))\b'
        )

    def deidentify(self, text: str, student_name: str = "") -> Tuple[str, Dict[str, str]]:
        """
        Replaces personal identifiable information with standard placeholder tokens.
        Returns the sanitized text and a reversible restoration map.
        """
        sanitized = text
        token_map = {}
        token_counter = 1

        # 1. Scrub Student Name if provided
        if student_name and len(student_name.strip()) > 2:
            name_parts = student_name.strip().split()
            # Full name
            placeholder = f"[APPLICANT_NAME]"
            sanitized = re.sub(re.escape(student_name.strip()), placeholder, sanitized, flags=re.IGNORECASE)
            token_map[placeholder] = student_name.strip()
            # First and Last names individually if longer than 3 chars
            for part in name_parts:
                if len(part) > 3 and part.lower() not in {"john", "jane", "will", "may", "rose"}:
                    part_placeholder = f"[APPLICANT_{part.upper()}]"
                    sanitized = re.sub(r'\b' + re.escape(part) + r'\b', part_placeholder, sanitized)
                    token_map[part_placeholder] = part

        # 2. Scrub Emails
        for email in self.email_pattern.findall(sanitized):
            placeholder = f"[EMAIL_{token_counter}]"
            token_map[placeholder] = email
            sanitized = sanitized.replace(email, placeholder)
            token_counter += 1

        # 3. Scrub Phone Numbers
        for phone in self.phone_pattern.findall(sanitized):
            placeholder = f"[PHONE_{token_counter}]"
            token_map[placeholder] = phone
            sanitized = sanitized.replace(phone, placeholder)
            token_counter += 1

        # 4. Scrub High School Names
        for match in self.school_pattern.findall(sanitized):
            placeholder = f"[SECONDARY_SCHOOL_{token_counter}]"
            token_map[placeholder] = match
            sanitized = sanitized.replace(match, placeholder)
            token_counter += 1

        return sanitized, token_map

    def reidentify(self, sanitized_text: str, token_map: Dict[str, str]) -> str:
        """Restores original student information before delivering final document to client."""
        restored = sanitized_text
        for placeholder, original in token_map.items():
            restored = restored.replace(placeholder, original)
        return restored


if __name__ == "__main__":
    scrubber = PIIScrubber()
    sample = "My name is Samantha Vance and I am a senior at St. Paul High School. Contact me at sam.vance@gmail.com or 555-234-8901."
    clean_text, mapping = scrubber.deidentify(sample, student_name="Samantha Vance")
    print("=" * 60)
    print("  PII DE-IDENTIFICATION AUDIT")
    print("=" * 60)
    print("Original :", sample)
    print("Sanitized:", clean_text)
    print("Tokens   :", mapping)
    print("Restored :", scrubber.reidentify(clean_text, mapping))
    print("=" * 60)
