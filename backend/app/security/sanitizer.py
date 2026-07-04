import bleach

class InputSanitizer:
    def __init__(self):
        # Disallow all HTML tags for core inputs
        self.allowed_tags = []
        self.allowed_attrs = {}

        # Heuristics for prompt injection detection
        self.injection_indicators = [
            "ignore previous instructions",
            "ignore the above instructions",
            "system override",
            "you are now a",
            "forget your goals",
            "bypass system rules"
        ]

    def sanitize_string(self, text: str) -> str:
        """
        Cleans any HTML tags out of strings.
        """
        if not text:
            return ""
        # Bleach clean strips tags
        return bleach.clean(text, tags=self.allowed_tags, attributes=self.allowed_attrs, strip=True)

    def detect_prompt_injection(self, text: str) -> bool:
        """
        Detects potential prompt injection heuristics.
        """
        if not text:
            return False
        
        normalized = text.lower()
        for indicator in self.injection_indicators:
            if indicator in normalized:
                return True
        return False

# Singleton instance
sanitizer = InputSanitizer()
