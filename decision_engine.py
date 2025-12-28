"""
Decision Engine for Gmail Classifier - SAFETY-FIRST Deletion Logic.

This module implements the CRITICAL safety checks that determine whether an email
should be deleted. ALL criteria must be met before deletion is approved.

DELETION CRITERIA (ALL must be true):
1. Category == Promotional
2. Verified == True (dual-agent verification completed)
3. Confidence >= 90%
4. NOT protected domain (banks, government, healthcare, investment platforms, etc.)
5. NOT starred/important (manual user flags)

This is the LAST LINE OF DEFENSE before deletion - every check must pass.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EmailCategory(Enum):
    """Email classification categories."""
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    SYSTEM_SECURITY = "system_security"
    SOCIAL_PLATFORM = "social_platform"
    PERSONAL_HUMAN = "personal_human"


@dataclass
class DeletionDecision:
    """
    Represents a deletion decision with full audit trail.

    Attributes:
        should_delete: Final decision - True if ALL criteria passed
        reasons: List of reasons why email SHOULD be deleted
        blocks: List of reasons why email should NOT be deleted (blocking factors)
        email_id: Gmail message ID
        category: Classified category
        confidence: Final confidence score
        verified: Whether dual-agent verification was completed
        is_protected_domain: Whether domain is protected
        has_manual_flags: Whether user manually flagged (starred/important)
        manual_flag_list: List of manual flags if any
    """
    should_delete: bool
    reasons: List[str]
    blocks: List[str]
    email_id: str
    category: EmailCategory
    confidence: int
    verified: bool
    is_protected_domain: bool
    has_manual_flags: bool
    manual_flag_list: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/serialization."""
        return {
            'should_delete': self.should_delete,
            'reasons': self.reasons,
            'blocks': self.blocks,
            'email_id': self.email_id,
            'category': self.category.value,
            'confidence': self.confidence,
            'verified': self.verified,
            'is_protected_domain': self.is_protected_domain,
            'has_manual_flags': self.has_manual_flags,
            'manual_flag_list': self.manual_flag_list
        }


class DecisionEngine:
    """
    SAFETY-FIRST decision engine for email deletion.

    This class implements the critical safety logic that determines whether
    an email should be deleted. It enforces ALL deletion criteria and provides
    a full audit trail for every decision.

    Statistics tracked:
    - approved_for_deletion: Emails that passed ALL checks
    - blocked_by_category: Not promotional
    - blocked_by_verification: Not verified by dual-agent
    - blocked_by_confidence: Confidence < 90%
    - blocked_by_domain: Protected domain (banks, investment, etc.)
    - blocked_by_manual_flags: User manually starred/flagged
    """

    # Minimum confidence threshold for deletion
    MIN_CONFIDENCE_FOR_DELETION = 90

    def __init__(self):
        """Initialize decision engine with empty stats."""
        self.stats = {
            'total_evaluated': 0,
            'approved_for_deletion': 0,
            'blocked_by_category': 0,
            'blocked_by_verification': 0,
            'blocked_by_confidence': 0,
            'blocked_by_domain': 0,
            'blocked_by_manual_flags': 0
        }

    def should_delete(
        self,
        email_id: str,
        classification: Dict,
        is_protected_domain: bool,
        has_manual_flags: bool,
        manual_flag_list: Optional[List[str]] = None
    ) -> DeletionDecision:
        """
        Determine if an email should be deleted.

        ALL of these criteria must be true for deletion:
        1. Category == Promotional
        2. Verified == True
        3. Confidence >= 90%
        4. NOT protected domain
        5. NOT starred/important

        Args:
            email_id: Gmail message ID
            classification: Classification result dict with keys:
                - 'category': EmailCategory enum
                - 'confidence': int (0-100)
                - 'verified': bool
            is_protected_domain: True if domain is protected
            has_manual_flags: True if email is starred/important
            manual_flag_list: List of manual flags (e.g., ['starred', 'important'])

        Returns:
            DeletionDecision object with full audit trail
        """
        self.stats['total_evaluated'] += 1

        # Extract classification data
        category = classification.get('category')
        confidence = classification.get('confidence', 0)
        verified = classification.get('verified', False)

        # Convert string category to enum if needed
        if isinstance(category, str):
            try:
                category = EmailCategory(category)
            except ValueError:
                category = EmailCategory.PERSONAL_HUMAN  # Safe default

        reasons = []
        blocks = []

        # Check 1: Category must be Promotional
        if category != EmailCategory.PROMOTIONAL:
            blocks.append(f"Category is {category.value}, not promotional")
            self.stats['blocked_by_category'] += 1
        else:
            reasons.append("Category is promotional")

        # Check 2: Must be verified by dual-agent
        if not verified:
            blocks.append("Not verified by dual-agent system")
            self.stats['blocked_by_verification'] += 1
        else:
            reasons.append("Verified by dual-agent")

        # Check 3: Confidence must be >= 90%
        if confidence < self.MIN_CONFIDENCE_FOR_DELETION:
            blocks.append(f"Confidence {confidence}% < {self.MIN_CONFIDENCE_FOR_DELETION}% threshold")
            self.stats['blocked_by_confidence'] += 1
        else:
            reasons.append(f"High confidence ({confidence}%)")

        # Check 4: NOT protected domain
        if is_protected_domain:
            blocks.append("Protected domain (bank/government/investment/healthcare/utility/education)")
            self.stats['blocked_by_domain'] += 1
        else:
            reasons.append("Not a protected domain")

        # Check 5: NOT starred/important
        if has_manual_flags:
            flag_str = ', '.join(manual_flag_list or ['unknown'])
            blocks.append(f"Manually flagged by user ({flag_str})")
            self.stats['blocked_by_manual_flags'] += 1
        else:
            reasons.append("No manual flags")

        # Final decision: ALL criteria must be met (no blocks)
        should_delete = len(blocks) == 0

        if should_delete:
            self.stats['approved_for_deletion'] += 1

        return DeletionDecision(
            should_delete=should_delete,
            reasons=reasons,
            blocks=blocks,
            email_id=email_id,
            category=category,
            confidence=confidence,
            verified=verified,
            is_protected_domain=is_protected_domain,
            has_manual_flags=has_manual_flags,
            manual_flag_list=manual_flag_list or []
        )

    def get_stats(self) -> Dict:
        """
        Get deletion decision statistics.

        Returns:
            Dictionary with counts for each decision outcome
        """
        return self.stats.copy()

    def get_stats_summary(self) -> str:
        """
        Get human-readable statistics summary.

        Returns:
            Formatted string with statistics
        """
        total = self.stats['total_evaluated']
        if total == 0:
            return "No emails evaluated yet"

        approved = self.stats['approved_for_deletion']
        approval_rate = (approved / total * 100) if total > 0 else 0

        lines = [
            f"Deletion Decision Statistics:",
            f"  Total evaluated:           {total}",
            f"  Approved for deletion:     {approved} ({approval_rate:.1f}%)",
            f"",
            f"  Blocked by category:       {self.stats['blocked_by_category']}",
            f"  Blocked by verification:   {self.stats['blocked_by_verification']}",
            f"  Blocked by confidence:     {self.stats['blocked_by_confidence']}",
            f"  Blocked by domain:         {self.stats['blocked_by_domain']}",
            f"  Blocked by manual flags:   {self.stats['blocked_by_manual_flags']}"
        ]

        return '\n'.join(lines)

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        for key in self.stats:
            self.stats[key] = 0
