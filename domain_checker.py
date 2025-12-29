"""
Domain Checker - Identifies protected domains with market categorization
Supports USA, India, and Germany markets
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import (
    PROTECTED_DOMAINS,
    Market,
    get_all_protected_domains,
    get_protected_domains_by_category,
)


@dataclass
class DomainCheckResult:
    """Result of domain protection check"""
    is_protected: bool
    market: Optional[Market]
    category: Optional[str]
    matched_domain: Optional[str]
    reason: str


class DomainChecker:
    """
    Checks if email domains are protected and identifies their market.
    Protected emails bypass AI classification entirely.
    """

    def __init__(self, target_market: Market = Market.ALL):
        """
        Initialize domain checker.

        Args:
            target_market: Target market for optimization (usa, india, germany, or all)
        """
        self.target_market = target_market
        self.protected_domains = get_all_protected_domains(target_market)

        # Build reverse lookup for market/category identification
        self._build_domain_index()

    def _build_domain_index(self):
        """Build index for fast domain -> (market, category) lookup"""
        self.domain_index: Dict[str, Tuple[Market, str]] = {}

        markets = (
            [self.target_market]
            if self.target_market != Market.ALL
            else [Market.USA, Market.INDIA, Market.GERMANY]
        )

        for market in markets:
            market_key = market.value
            if market_key not in PROTECTED_DOMAINS:
                continue

            for category, domains in PROTECTED_DOMAINS[market_key].items():
                for domain in domains:
                    self.domain_index[domain.lower()] = (market, category)

    def extract_domain(self, email_address: str) -> Optional[str]:
        """
        Extract domain from email address.

        Args:
            email_address: Email address (e.g., 'support@zerodha.com')

        Returns:
            Domain string or None if invalid
        """
        if not email_address or "@" not in email_address:
            return None

        try:
            # Extract domain part after @
            domain = email_address.split("@")[-1].strip().lower()

            # Remove any trailing brackets or special characters
            domain = re.sub(r'[<>\[\]()]', '', domain)

            return domain
        except Exception:
            return None

    def check_domain(self, email_address: str) -> DomainCheckResult:
        """
        Check if email is from a protected domain.

        Args:
            email_address: Email address to check

        Returns:
            DomainCheckResult with protection status and metadata
        """
        domain = self.extract_domain(email_address)

        if not domain:
            return DomainCheckResult(
                is_protected=False,
                market=None,
                category=None,
                matched_domain=None,
                reason="Invalid email address or domain"
            )

        # Check exact domain match
        if domain in self.domain_index:
            market, category = self.domain_index[domain]
            return DomainCheckResult(
                is_protected=True,
                market=market,
                category=category,
                matched_domain=domain,
                reason=f"Exact match: {category} domain for {market.value}"
            )

        # Check pattern matches (e.g., .gov, .edu)
        for protected_pattern, (market, category) in self.domain_index.items():
            if self._matches_pattern(domain, protected_pattern):
                return DomainCheckResult(
                    is_protected=True,
                    market=market,
                    category=category,
                    matched_domain=protected_pattern,
                    reason=f"Pattern match: {category} domain for {market.value}"
                )

        # Not protected
        return DomainCheckResult(
            is_protected=False,
            market=None,
            category=None,
            matched_domain=None,
            reason="Not a protected domain"
        )

    def _matches_pattern(self, domain: str, pattern: str) -> bool:
        """
        Check if domain matches a pattern (e.g., .gov, .edu).

        Args:
            domain: Email domain to check
            pattern: Pattern to match against

        Returns:
            True if domain matches pattern
        """
        # Handle TLD patterns like .gov, .edu
        if pattern.startswith("."):
            return domain.endswith(pattern)

        # Handle subdomain patterns
        if "*" in pattern:
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
            return bool(re.match(regex_pattern, domain))

        return False

    def is_critical_financial_domain(self, email_address: str) -> bool:
        """
        Quick check if email is from critical financial domain.
        Used for extra safety checks.

        Args:
            email_address: Email address to check

        Returns:
            True if from investment/banking/brokerage domain
        """
        result = self.check_domain(email_address)

        if not result.is_protected:
            return False

        return result.category in [
            "investment_brokerage",
            "banking",
        ]

    def get_market_stats(self, email_addresses: List[str]) -> Dict[str, int]:
        """
        Get statistics on market distribution of email addresses.

        Args:
            email_addresses: List of email addresses to analyze

        Returns:
            Dictionary with market counts
        """
        stats = {
            "total": len(email_addresses),
            "protected": 0,
            "usa": 0,
            "india": 0,
            "germany": 0,
            "unprotected": 0,
        }

        for email in email_addresses:
            result = self.check_domain(email)

            if result.is_protected:
                stats["protected"] += 1
                if result.market:
                    stats[result.market.value] += 1
            else:
                stats["unprotected"] += 1

        return stats

    def get_category_stats(self, email_addresses: List[str]) -> Dict[str, int]:
        """
        Get statistics on category distribution.

        Args:
            email_addresses: List of email addresses to analyze

        Returns:
            Dictionary with category counts
        """
        stats = {}

        for email in email_addresses:
            result = self.check_domain(email)

            if result.is_protected and result.category:
                stats[result.category] = stats.get(result.category, 0) + 1

        return stats


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_email_protection(email_address: str, target_market: Market = Market.ALL) -> bool:
    """
    Quick helper to check if email is protected.

    Args:
        email_address: Email address to check
        target_market: Target market

    Returns:
        True if email is from protected domain
    """
    checker = DomainChecker(target_market)
    result = checker.check_domain(email_address)
    return result.is_protected


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test domain checker with examples from all three markets
    checker = DomainChecker(Market.ALL)

    test_emails = [
        # USA
        "alerts@schwab.com",
        "notifications@fidelity.com",
        "support@chase.com",
        "info@irs.gov",
        "noreply@unitedhealthcare.com",

        # India
        "no-reply@zerodha.com",
        "alerts@groww.in",
        "statements@hdfcbank.com",
        "noreply@incometaxindia.gov.in",

        # Germany
        "info@traderepublic.com",
        "service@deutsche-bank.de",
        "kontakt@tk.de",
        "mail@finanzamt.de",

        # Non-protected
        "marketing@randomcompany.com",
        "deals@onlineshop.com",
    ]

    print("Domain Protection Check Results:")
    print("=" * 80)

    for email in test_emails:
        result = checker.check_domain(email)
        status = "PROTECTED" if result.is_protected else "unprotected"
        market_info = f" [{result.market.value.upper()}]" if result.market else ""

        print(f"{status:12} {market_info:8} {email:40} - {result.reason}")

    print("\n" + "=" * 80)
    print("\nMarket Statistics:")
    stats = checker.get_market_stats(test_emails)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nCategory Statistics:")
    cat_stats = checker.get_category_stats(test_emails)
    for category, count in sorted(cat_stats.items()):
        print(f"  {category}: {count}")
