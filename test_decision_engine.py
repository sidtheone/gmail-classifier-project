"""
Comprehensive test suite for DecisionEngine
Tests all 5 safety gates and edge cases
"""

import unittest
from config import Market, EmailCategory
from domain_checker import DomainChecker
from decision_engine import DecisionEngine, DeletionDecision, ConfidenceLevel


class TestDecisionEngine(unittest.TestCase):
    """Test cases for DecisionEngine with 5-gate safety system"""

    def setUp(self):
        """Set up test fixtures"""
        self.domain_checker = DomainChecker(Market.ALL)
        self.engine = DecisionEngine(
            self.domain_checker,
            confidence_threshold=90.0,
            enable_human_review=True,
        )

    def test_gate_1_category_promotional_pass(self):
        """Test Gate 1: Promotional category passes"""
        result = self.engine.evaluate(
            email_id="test001",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="deals@shop.com",
            is_starred=False,
            is_important=False,
        )

        gate_1 = result.gates[0]
        self.assertTrue(gate_1.passed)
        self.assertEqual(gate_1.gate_name, "Category Check")

    def test_gate_1_category_non_promotional_fail(self):
        """Test Gate 1: Non-promotional category fails"""
        result = self.engine.evaluate(
            email_id="test002",
            category="transactional",
            confidence=95.0,
            verified=True,
            from_address="receipt@store.com",
            is_starred=False,
            is_important=False,
        )

        gate_1 = result.gates[0]
        self.assertFalse(gate_1.passed)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_2_verification_pass(self):
        """Test Gate 2: Verified classification passes"""
        result = self.engine.evaluate(
            email_id="test003",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="newsletter@company.com",
            is_starred=False,
            is_important=False,
        )

        gate_2 = result.gates[1]
        self.assertTrue(gate_2.passed)
        self.assertEqual(gate_2.gate_name, "Verification Check")

    def test_gate_2_verification_fail(self):
        """Test Gate 2: Unverified classification fails"""
        result = self.engine.evaluate(
            email_id="test004",
            category="promotional",
            confidence=95.0,
            verified=False,
            from_address="deals@shop.com",
            is_starred=False,
            is_important=False,
        )

        gate_2 = result.gates[1]
        self.assertFalse(gate_2.passed)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_3_high_confidence_pass(self):
        """Test Gate 3: High confidence (≥90%) passes"""
        result = self.engine.evaluate(
            email_id="test005",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="marketing@company.com",
            is_starred=False,
            is_important=False,
        )

        gate_3 = result.gates[2]
        self.assertTrue(gate_3.passed)
        self.assertEqual(result.confidence_level, ConfidenceLevel.HIGH)

    def test_gate_3_medium_confidence_flagged(self):
        """Test Gate 3: Medium confidence (70-89%) flagged for review"""
        result = self.engine.evaluate(
            email_id="test006",
            category="promotional",
            confidence=75.0,
            verified=True,
            from_address="newsletter@site.com",
            is_starred=False,
            is_important=False,
        )

        self.assertEqual(result.confidence_level, ConfidenceLevel.MEDIUM)
        self.assertEqual(result.decision, DeletionDecision.FLAGGED_FOR_REVIEW)

    def test_gate_3_low_confidence_fail(self):
        """Test Gate 3: Low confidence (<70%) fails"""
        result = self.engine.evaluate(
            email_id="test007",
            category="promotional",
            confidence=65.0,
            verified=True,
            from_address="email@company.com",
            is_starred=False,
            is_important=False,
        )

        gate_3 = result.gates[2]
        self.assertFalse(gate_3.passed)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_4_protected_domain_usa_brokerage(self):
        """Test Gate 4: USA brokerage domain fails (protected)"""
        result = self.engine.evaluate(
            email_id="test008",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="alerts@schwab.com",
            is_starred=False,
            is_important=False,
        )

        gate_4 = result.gates[3]
        self.assertFalse(gate_4.passed)
        self.assertIn("PROTECTED", gate_4.reason)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_4_protected_domain_india_brokerage(self):
        """Test Gate 4: India brokerage domain fails (protected)"""
        result = self.engine.evaluate(
            email_id="test009",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="no-reply@zerodha.com",
            is_starred=False,
            is_important=False,
        )

        gate_4 = result.gates[3]
        self.assertFalse(gate_4.passed)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_4_protected_domain_germany_bank(self):
        """Test Gate 4: Germany bank domain fails (protected)"""
        result = self.engine.evaluate(
            email_id="test010",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="service@deutsche-bank.de",
            is_starred=False,
            is_important=False,
        )

        gate_4 = result.gates[3]
        self.assertFalse(gate_4.passed)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_4_non_protected_domain_pass(self):
        """Test Gate 4: Non-protected domain passes"""
        result = self.engine.evaluate(
            email_id="test011",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="deals@onlineshop.com",
            is_starred=False,
            is_important=False,
        )

        gate_4 = result.gates[3]
        self.assertTrue(gate_4.passed)

    def test_gate_5_starred_email_fail(self):
        """Test Gate 5: Starred email fails"""
        result = self.engine.evaluate(
            email_id="test012",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="deals@shop.com",
            is_starred=True,
            is_important=False,
        )

        gate_5 = result.gates[4]
        self.assertFalse(gate_5.passed)
        self.assertIn("starred", gate_5.reason.lower())
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_5_important_email_fail(self):
        """Test Gate 5: Important email fails"""
        result = self.engine.evaluate(
            email_id="test013",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="newsletter@company.com",
            is_starred=False,
            is_important=True,
        )

        gate_5 = result.gates[4]
        self.assertFalse(gate_5.passed)
        self.assertIn("important", gate_5.reason.lower())
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_gate_5_no_flags_pass(self):
        """Test Gate 5: No flags passes"""
        result = self.engine.evaluate(
            email_id="test014",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="deals@store.com",
            is_starred=False,
            is_important=False,
        )

        gate_5 = result.gates[4]
        self.assertTrue(gate_5.passed)

    def test_all_gates_pass_approved(self):
        """Test: All gates pass = APPROVED decision"""
        result = self.engine.evaluate(
            email_id="test015",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="marketing@shop.com",
            is_starred=False,
            is_important=False,
        )

        # All gates should pass
        for gate in result.gates:
            self.assertTrue(gate.passed)

        self.assertEqual(result.decision, DeletionDecision.APPROVED)
        self.assertEqual(result.confidence_level, ConfidenceLevel.HIGH)

    def test_critical_false_positive_prevention_investment(self):
        """Test: Investment platform email NEVER approved (critical safety test)"""
        # Test all major investment platforms across markets
        investment_emails = [
            "alerts@schwab.com",           # USA
            "notifications@fidelity.com",   # USA
            "no-reply@zerodha.com",        # India
            "alerts@groww.in",             # India
            "info@traderepublic.com",      # Germany
        ]

        for email_address in investment_emails:
            with self.subTest(email=email_address):
                result = self.engine.evaluate(
                    email_id="test_investment",
                    category="promotional",
                    confidence=95.0,
                    verified=True,
                    from_address=email_address,
                    is_starred=False,
                    is_important=False,
                )

                # CRITICAL: Must be REJECTED, never APPROVED
                self.assertNotEqual(
                    result.decision,
                    DeletionDecision.APPROVED,
                    f"CRITICAL FAILURE: Investment email {email_address} was approved for deletion!"
                )

    def test_critical_false_positive_prevention_government(self):
        """Test: Government email NEVER approved (critical safety test)"""
        government_emails = [
            "noreply@irs.gov",                    # USA
            "alerts@incometaxindia.gov.in",       # India
            "info@finanzamt.de",                  # Germany
        ]

        for email_address in government_emails:
            with self.subTest(email=email_address):
                result = self.engine.evaluate(
                    email_id="test_gov",
                    category="promotional",
                    confidence=95.0,
                    verified=True,
                    from_address=email_address,
                    is_starred=False,
                    is_important=False,
                )

                self.assertNotEqual(
                    result.decision,
                    DeletionDecision.APPROVED,
                    f"CRITICAL FAILURE: Government email {email_address} was approved for deletion!"
                )

    def test_statistics_tracking(self):
        """Test: Statistics are tracked correctly"""
        # Process multiple emails
        test_cases = [
            ("promotional", 95.0, True, "deals@shop.com", False, False, DeletionDecision.APPROVED),
            ("transactional", 95.0, True, "order@store.com", False, False, DeletionDecision.REJECTED),
            ("promotional", 75.0, True, "news@site.com", False, False, DeletionDecision.FLAGGED_FOR_REVIEW),
        ]

        for i, (cat, conf, verified, from_addr, starred, important, expected) in enumerate(test_cases):
            result = self.engine.evaluate(
                email_id=f"test_{i}",
                category=cat,
                confidence=conf,
                verified=verified,
                from_address=from_addr,
                is_starred=starred,
                is_important=important,
            )
            self.assertEqual(result.decision, expected)

        # Check statistics
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_processed"], 3)
        self.assertEqual(stats["approved"], 1)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(stats["flagged"], 1)


class TestDecisionEngineEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.domain_checker = DomainChecker(Market.ALL)
        self.engine = DecisionEngine(self.domain_checker)

    def test_invalid_category_failsafe(self):
        """Test: Invalid category defaults to PERSONAL_HUMAN (fail-safe)"""
        result = self.engine.evaluate(
            email_id="test_invalid",
            category="invalid_category",
            confidence=95.0,
            verified=True,
            from_address="test@example.com",
            is_starred=False,
            is_important=False,
        )

        # Should be rejected (not promotional)
        self.assertEqual(result.decision, DeletionDecision.REJECTED)

    def test_confidence_boundary_90_percent(self):
        """Test: Exactly 90% confidence (boundary case)"""
        result = self.engine.evaluate(
            email_id="test_boundary",
            category="promotional",
            confidence=90.0,
            verified=True,
            from_address="deals@shop.com",
            is_starred=False,
            is_important=False,
        )

        self.assertEqual(result.confidence_level, ConfidenceLevel.HIGH)
        self.assertEqual(result.decision, DeletionDecision.APPROVED)

    def test_confidence_boundary_89_percent(self):
        """Test: 89% confidence (just below threshold)"""
        result = self.engine.evaluate(
            email_id="test_boundary2",
            category="promotional",
            confidence=89.999,
            verified=True,
            from_address="newsletter@site.com",
            is_starred=False,
            is_important=False,
        )

        self.assertEqual(result.confidence_level, ConfidenceLevel.MEDIUM)
        self.assertEqual(result.decision, DeletionDecision.FLAGGED_FOR_REVIEW)

    def test_human_review_disabled(self):
        """Test: Medium confidence rejected when human review disabled"""
        engine_no_review = DecisionEngine(
            self.domain_checker,
            confidence_threshold=90.0,
            enable_human_review=False,
        )

        result = engine_no_review.evaluate(
            email_id="test_no_review",
            category="promotional",
            confidence=75.0,
            verified=True,
            from_address="newsletter@company.com",
            is_starred=False,
            is_important=False,
        )

        # Should be rejected, not flagged
        self.assertEqual(result.decision, DeletionDecision.REJECTED)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
