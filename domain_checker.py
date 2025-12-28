"""
Domain Protection System for Gmail Classifier.

This module provides SAFETY-FIRST domain protection to ensure emails from
banks, government, healthcare, utilities, educational institutions, and
investment platforms are NEVER marked as promotional or deleted.
"""

import re
from typing import Tuple, Optional
from config import PROTECTED_DOMAINS, PROTECTED_DOMAIN_PATTERNS


class DomainChecker:
    """
    Checks if email domain is protected.

    Protected categories:
    - Banks & Financial Institutions
    - Government & Tax Authorities
    - Healthcare & Insurance
    - Utilities & Telecom
    - Educational Institutions
    - Investment Platforms & Brokers (CRITICAL - added to prevent misclassification)
    - Mutual Funds & Fund Registrars
    - Stock Exchanges

    This is a HARD OVERRIDE - protected domains bypass all other classification logic.
    """

    def __init__(self) -> None:
        """Initialize with protected domains and patterns."""
        self.protected_domains = set(d.lower() for d in PROTECTED_DOMAINS)
        self.protected_patterns = [re.compile(p, re.IGNORECASE) for p in PROTECTED_DOMAIN_PATTERNS]
        self.stats = {'protected_hits': 0}

    def extract_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()

    def is_protected(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Check if email domain is protected.

        Args:
            email: Email address to check

        Returns:
            Tuple of (is_protected, reason).
            - is_protected: True if domain should NEVER be marked promotional
            - reason: Explanation of why domain is protected (for logging)
        """
        domain = self.extract_domain(email)

        # Check exact domain match
        for protected in self.protected_domains:
            if domain == protected or domain.endswith('.' + protected):
                self.stats['protected_hits'] += 1
                return True, f"Protected domain: {protected}"

        # Check domain patterns (regex)
        for pattern in self.protected_patterns:
            if pattern.search(domain):
                self.stats['protected_hits'] += 1
                return True, f"Protected pattern: {pattern.pattern}"

        return False, None
