"""
Decision Engine - Multi-layered safety system for deletion decisions
Implements 5 mandatory safety gates (ALL must pass for deletion)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from config import (
    EmailCategory,
    ConfidenceLevel,
    CONFIDENCE_THRESHOLDS,
    get_confidence_level,
)
from domain_checker import DomainChecker, DomainCheckResult


class DeletionDecision(str, Enum):
    """Final deletion decision"""
    APPROVED = "approved"          # All gates passed - safe to delete
    REJECTED = "rejected"          # Failed one or more gates - DO NOT delete
    FLAGGED_FOR_REVIEW = "flagged" # Medium confidence - needs human review


@dataclass
class GateResult:
    """Result of a single safety gate check"""
    gate_number: int
    gate_name: str
    passed: bool
    reason: str


@dataclass
class DeletionDecisionResult:
    """Complete decision result with all gate checks"""
    decision: DeletionDecision
    email_id: str
    category: EmailCategory
    confidence: float
    confidence_level: ConfidenceLevel
    gates: List[GateResult]
    final_reason: str
    metadata: Dict


class DecisionEngine:
    """
    Multi-layered safety system with 5 mandatory gates.
    ALL gates must pass for email to be approved for deletion.
    """

    def __init__(
        self,
        domain_checker: DomainChecker,
        confidence_threshold: float = 90.0,
        enable_human_review: bool = True,
    ):
        """
        Initialize decision engine.

        Args:
            domain_checker: DomainChecker instance for protected domain checks
            confidence_threshold: Minimum confidence for deletion (default 90%)
            enable_human_review: Enable human review for medium confidence emails
        """
        self.domain_checker = domain_checker
        self.confidence_threshold = confidence_threshold
        self.enable_human_review = enable_human_review

        # Statistics tracking
        self.stats = {
            "total_processed": 0,
            "approved": 0,
            "rejected": 0,
            "flagged": 0,
            "gate_failures": {
                "gate_1_category": 0,
                "gate_2_verification": 0,
                "gate_3_confidence": 0,
                "gate_4_protected_domain": 0,
                "gate_5_manual_flags": 0,
            },
        }

    def evaluate(
        self,
        email_id: str,
        category: str,
        confidence: float,
        verified: bool,
        from_address: str,
        is_starred: bool = False,
        is_important: bool = False,
        metadata: Optional[Dict] = None,
    ) -> DeletionDecisionResult:
        """
        Evaluate email against all 5 safety gates.

        Args:
            email_id: Gmail message ID
            category: AI-classified category
            confidence: Confidence score (0-100)
            verified: Whether classification passed dual-agent verification
            from_address: Email sender address
            is_starred: Whether email is starred in Gmail
            is_important: Whether email is marked important in Gmail
            metadata: Additional metadata for logging

        Returns:
            DeletionDecisionResult with complete gate evaluation
        """
        self.stats["total_processed"] += 1

        # Normalize category to EmailCategory enum
        try:
            email_category = EmailCategory(category.lower())
        except ValueError:
            # Invalid category - fail-safe to PERSONAL_HUMAN
            email_category = EmailCategory.PERSONAL_HUMAN

        # Determine confidence level
        confidence_level = get_confidence_level(confidence)

        gates: List[GateResult] = []
        metadata = metadata or {}

        # ====================================================================
        # GATE 1: Category Check
        # ====================================================================
        gate_1 = self._check_gate_1_category(email_category)
        gates.append(gate_1)

        # ====================================================================
        # GATE 2: Verification Check
        # ====================================================================
        gate_2 = self._check_gate_2_verification(verified)
        gates.append(gate_2)

        # ====================================================================
        # GATE 3: Confidence Threshold
        # ====================================================================
        gate_3 = self._check_gate_3_confidence(confidence, confidence_level)
        gates.append(gate_3)

        # ====================================================================
        # GATE 4: Protected Domain Check
        # ====================================================================
        gate_4 = self._check_gate_4_protected_domain(from_address)
        gates.append(gate_4)

        # Store domain check result in metadata
        if hasattr(gate_4, 'domain_result'):
            metadata['domain_check'] = gate_4.domain_result

        # ====================================================================
        # GATE 5: Manual Flags Check
        # ====================================================================
        gate_5 = self._check_gate_5_manual_flags(is_starred, is_important)
        gates.append(gate_5)

        # ====================================================================
        # FINAL DECISION
        # ====================================================================
        decision, final_reason = self._make_final_decision(
            gates, confidence_level, email_category
        )

        # Update statistics
        self._update_stats(decision, gates)

        return DeletionDecisionResult(
            decision=decision,
            email_id=email_id,
            category=email_category,
            confidence=confidence,
            confidence_level=confidence_level,
            gates=gates,
            final_reason=final_reason,
            metadata=metadata,
        )

    # ========================================================================
    # INDIVIDUAL GATE CHECKS
    # ========================================================================

    def _check_gate_1_category(self, category: EmailCategory) -> GateResult:
        """
        Gate 1: Email must be categorized as PROMOTIONAL.
        Only promotional emails are eligible for deletion.
        """
        passed = category == EmailCategory.PROMOTIONAL

        return GateResult(
            gate_number=1,
            gate_name="Category Check",
            passed=passed,
            reason=(
                "Category is PROMOTIONAL"
                if passed
                else f"Category is {category.value}, not PROMOTIONAL"
            ),
        )

    def _check_gate_2_verification(self, verified: bool) -> GateResult:
        """
        Gate 2: Classification must pass dual-agent verification.
        Verifier agent must confirm promotional classification.
        """
        return GateResult(
            gate_number=2,
            gate_name="Verification Check",
            passed=verified,
            reason=(
                "Passed dual-agent verification"
                if verified
                else "Failed dual-agent verification"
            ),
        )

    def _check_gate_3_confidence(
        self, confidence: float, confidence_level: ConfidenceLevel
    ) -> GateResult:
        """
        Gate 3: Confidence must meet threshold.
        Default threshold is 90% for auto-deletion.
        Medium confidence (70-89%) triggers human review if enabled.
        """
        # For flagged reviews, we consider the gate "passed" for evaluation
        # but the final decision will be FLAGGED, not APPROVED
        if confidence_level == ConfidenceLevel.MEDIUM and self.enable_human_review:
            return GateResult(
                gate_number=3,
                gate_name="Confidence Threshold",
                passed=True,  # Technically passes, but will be flagged
                reason=f"Medium confidence ({confidence:.1f}%) - flagged for human review",
            )

        passed = confidence >= self.confidence_threshold

        return GateResult(
            gate_number=3,
            gate_name="Confidence Threshold",
            passed=passed,
            reason=(
                f"Confidence {confidence:.1f}% >= threshold {self.confidence_threshold}%"
                if passed
                else f"Confidence {confidence:.1f}% < threshold {self.confidence_threshold}%"
            ),
        )

    def _check_gate_4_protected_domain(self, from_address: str) -> GateResult:
        """
        Gate 4: Email must NOT be from protected domain.
        Protected domains (banks, brokerages, government) bypass deletion entirely.
        """
        domain_result = self.domain_checker.check_domain(from_address)

        passed = not domain_result.is_protected

        gate = GateResult(
            gate_number=4,
            gate_name="Protected Domain Check",
            passed=passed,
            reason=(
                "Not from protected domain"
                if passed
                else f"PROTECTED: {domain_result.reason}"
            ),
        )

        # Attach domain result for metadata
        gate.domain_result = domain_result

        return gate

    def _check_gate_5_manual_flags(
        self, is_starred: bool, is_important: bool
    ) -> GateResult:
        """
        Gate 5: Email must NOT have manual flags (starred/important).
        User-flagged emails are never deleted.
        """
        has_flags = is_starred or is_important
        passed = not has_flags

        flags = []
        if is_starred:
            flags.append("starred")
        if is_important:
            flags.append("important")

        return GateResult(
            gate_number=5,
            gate_name="Manual Flags Check",
            passed=passed,
            reason=(
                "No manual flags"
                if passed
                else f"Has manual flags: {', '.join(flags)}"
            ),
        )

    # ========================================================================
    # FINAL DECISION LOGIC
    # ========================================================================

    def _make_final_decision(
        self,
        gates: List[GateResult],
        confidence_level: ConfidenceLevel,
        category: EmailCategory,
    ) -> tuple[DeletionDecision, str]:
        """
        Make final deletion decision based on all gate results.

        Args:
            gates: List of all gate check results
            confidence_level: Confidence level (HIGH/MEDIUM/LOW)
            category: Email category

        Returns:
            Tuple of (decision, reason)
        """
        # Check if all gates passed
        all_passed = all(gate.passed for gate in gates)

        # Find failed gates
        failed_gates = [gate for gate in gates if not gate.passed]

        # CASE 1: One or more gates failed - REJECT
        if not all_passed:
            failed_gate_names = [gate.gate_name for gate in failed_gates]
            return (
                DeletionDecision.REJECTED,
                f"Failed gates: {', '.join(failed_gate_names)}",
            )

        # CASE 2: All gates passed, but medium confidence - FLAG FOR REVIEW
        if confidence_level == ConfidenceLevel.MEDIUM and self.enable_human_review:
            return (
                DeletionDecision.FLAGGED_FOR_REVIEW,
                "All gates passed but confidence is medium (70-89%) - requires human review",
            )

        # CASE 3: All gates passed and high confidence - APPROVE
        if confidence_level == ConfidenceLevel.HIGH:
            return (
                DeletionDecision.APPROVED,
                "All 5 safety gates passed with high confidence",
            )

        # CASE 4: Low confidence - REJECT (should be caught by gate 3, but fail-safe)
        return (
            DeletionDecision.REJECTED,
            "Low confidence (<70%) - not eligible for deletion",
        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def _update_stats(self, decision: DeletionDecision, gates: List[GateResult]):
        """Update internal statistics"""
        if decision == DeletionDecision.APPROVED:
            self.stats["approved"] += 1
        elif decision == DeletionDecision.REJECTED:
            self.stats["rejected"] += 1
        elif decision == DeletionDecision.FLAGGED_FOR_REVIEW:
            self.stats["flagged"] += 1

        # Track gate failures
        for gate in gates:
            if not gate.passed:
                gate_key = f"gate_{gate.gate_number}_{gate.gate_name.lower().replace(' ', '_')}"
                if gate_key in self.stats["gate_failures"]:
                    self.stats["gate_failures"][gate_key] += 1

    def get_stats(self) -> Dict:
        """Get decision engine statistics"""
        stats = self.stats.copy()

        # Calculate percentages
        total = stats["total_processed"]
        if total > 0:
            stats["approval_rate"] = (stats["approved"] / total) * 100
            stats["rejection_rate"] = (stats["rejected"] / total) * 100
            stats["flag_rate"] = (stats["flagged"] / total) * 100

        return stats

    def reset_stats(self):
        """Reset statistics"""
        for key in ["total_processed", "approved", "rejected", "flagged"]:
            self.stats[key] = 0

        for gate in self.stats["gate_failures"]:
            self.stats["gate_failures"][gate] = 0

    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()

        print("\n" + "=" * 80)
        print("DECISION ENGINE STATISTICS")
        print("=" * 80)
        print(f"Total Emails Processed: {stats['total_processed']}")
        print()
        print(f"Approved for Deletion:  {stats['approved']:4} ({stats.get('approval_rate', 0):5.1f}%)")
        print(f"Rejected (Do Not Delete): {stats['rejected']:4} ({stats.get('rejection_rate', 0):5.1f}%)")
        print(f"Flagged for Review:     {stats['flagged']:4} ({stats.get('flag_rate', 0):5.1f}%)")
        print()
        print("Gate Failure Breakdown:")

        for gate_name, count in stats["gate_failures"].items():
            if count > 0:
                print(f"  {gate_name}: {count}")

        print("=" * 80 + "\n")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from config import Market

    # Create test decision engine
    domain_checker = DomainChecker(Market.ALL)
    engine = DecisionEngine(domain_checker, confidence_threshold=90.0)

    # Test cases
    test_cases = [
        {
            "name": "Safe promotional email - APPROVE",
            "email_id": "test001",
            "category": "promotional",
            "confidence": 95.0,
            "verified": True,
            "from_address": "deals@onlineshop.com",
            "is_starred": False,
            "is_important": False,
        },
        {
            "name": "Brokerage email - REJECT (protected domain)",
            "email_id": "test002",
            "category": "promotional",
            "confidence": 95.0,
            "verified": True,
            "from_address": "alerts@zerodha.com",
            "is_starred": False,
            "is_important": False,
        },
        {
            "name": "Medium confidence - FLAG FOR REVIEW",
            "email_id": "test003",
            "category": "promotional",
            "confidence": 75.0,
            "verified": True,
            "from_address": "newsletter@company.com",
            "is_starred": False,
            "is_important": False,
        },
        {
            "name": "Not promotional - REJECT (wrong category)",
            "email_id": "test004",
            "category": "transactional",
            "confidence": 95.0,
            "verified": True,
            "from_address": "receipt@store.com",
            "is_starred": False,
            "is_important": False,
        },
        {
            "name": "Starred email - REJECT (manual flag)",
            "email_id": "test005",
            "category": "promotional",
            "confidence": 95.0,
            "verified": True,
            "from_address": "deals@shop.com",
            "is_starred": True,
            "is_important": False,
        },
    ]

    print("\nTesting Decision Engine with 5-Gate Safety System")
    print("=" * 80)

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("-" * 80)

        result = engine.evaluate(
            email_id=test["email_id"],
            category=test["category"],
            confidence=test["confidence"],
            verified=test["verified"],
            from_address=test["from_address"],
            is_starred=test["is_starred"],
            is_important=test["is_important"],
        )

        print(f"Decision: {result.decision.value.upper()}")
        print(f"Reason: {result.final_reason}")
        print("\nGate Results:")

        for gate in result.gates:
            status = "PASS" if gate.passed else "FAIL"
            print(f"  Gate {gate.gate_number} ({gate.gate_name}): {status:4} - {gate.reason}")

    # Print statistics
    engine.print_stats()
