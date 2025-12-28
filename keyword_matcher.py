"""
Keyword matching module for promotional email detection.

Supports both English and German promotional keywords.
"""

from typing import Dict, List, Optional, Tuple

from config import (
    PROMOTIONAL_KEYWORDS_EN,
    PROMOTIONAL_KEYWORDS_DE,
    KEYWORD_THRESHOLD,
)


class KeywordMatcher:
    """Matches promotional keywords in email content (English and German)."""

    def __init__(self) -> None:
        """Initialize with combined English and German keywords."""
        self.keywords: set[str] = set(
            [kw.lower() for kw in PROMOTIONAL_KEYWORDS_EN] +
            [kw.lower() for kw in PROMOTIONAL_KEYWORDS_DE]
        )
        self.threshold: int = KEYWORD_THRESHOLD

    def count_matches(self, text: str) -> Tuple[int, List[str]]:
        """
        Count keyword matches in text.

        Args:
            text: The text to search for keywords.

        Returns:
            Tuple of (match_count, list_of_matched_keywords).
        """
        text_lower = text.lower()
        matched = [kw for kw in self.keywords if kw in text_lower]
        return len(matched), matched

    def check(self, email_content: Dict[str, str]) -> Tuple[Optional[bool], int, List[str]]:
        """
        Check if email is promotional based on keywords.

        Args:
            email_content: Dictionary with 'subject' and 'body' keys.

        Returns:
            Tuple of (is_promotional or None, match_count, matched_keywords).
            Returns None for is_promotional if below threshold.
        """
        combined_text = f"{email_content.get('subject', '')} {email_content.get('body', '')}"
        match_count, matched = self.count_matches(combined_text)

        if match_count >= self.threshold:
            return True, match_count, matched

        return None, match_count, matched

    def get_confidence(self, match_count: int) -> int:
        """
        Calculate confidence score based on match count.

        Args:
            match_count: Number of keyword matches.

        Returns:
            Confidence score between 70-95.
        """
        return min(70 + match_count * 5, 95)
