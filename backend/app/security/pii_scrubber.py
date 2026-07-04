import re
from typing import Dict, Tuple

class PIIScrubber:
    def __init__(self):
        # Email Regex
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        # Phone numbers (various formats)
        self.phone_pattern = re.compile(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
        # Basic Address placeholder (captures Zip code patterns or general state expressions)
        self.zip_pattern = re.compile(r'\b\d{5}(?:-\d{4})?\b')

    def scrub(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Detects PII in text and replaces it with unique placeholders.
        Returns the scrubbed text and a dictionary containing placeholder mappings.
        """
        mapping = {}
        scrubbed = text

        # Scrub Emails
        emails = self.email_pattern.findall(scrubbed)
        for i, email in enumerate(set(emails)):
            placeholder = f"[EMAIL_{i+1}]"
            mapping[placeholder] = email
            scrubbed = scrubbed.replace(email, placeholder)

        # Scrub Phones
        phones = self.phone_pattern.findall(scrubbed)
        # Sort by length descending to prevent replacing substrings of longer phone numbers
        phones = sorted(list(set(phones)), key=len, reverse=True)
        for i, phone in enumerate(phones):
            # Exclude short digit sequences that aren't phone numbers (min length 7 digits)
            digit_count = sum(c.isdigit() for c in phone)
            if digit_count >= 7:
                placeholder = f"[PHONE_{i+1}]"
                mapping[placeholder] = phone
                scrubbed = scrubbed.replace(phone, placeholder)

        # Scrub Zip/Postal Codes
        zips = self.zip_pattern.findall(scrubbed)
        for i, zp in enumerate(set(zips)):
            placeholder = f"[ZIP_{i+1}]"
            mapping[placeholder] = zp
            scrubbed = scrubbed.replace(zp, placeholder)

        return scrubbed, mapping

    def rehydrate(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Replaces placeholders back with original PII values.
        """
        rehydrated = text
        for placeholder, original in mapping.items():
            rehydrated = rehydrated.replace(placeholder, original)
        return rehydrated

# Singleton instance
pii_scrubber = PIIScrubber()
