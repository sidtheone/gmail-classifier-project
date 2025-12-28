#!/usr/bin/env python3
"""
Test suite for DecisionEngine - SAFETY-FIRST deletion logic validation.

This validates that ALL 5 deletion criteria are enforced:
1. Category == Promotional
2. Verified == True
3. Confidence >= 90%
4. NOT protected domain
5. NOT starred/important
"""

from decision_engine import DecisionEngine, EmailCategory, DeletionDecision


def test_should_delete_all_criteria_met():
    """Test: Should delete when ALL criteria are met."""
    engine = DecisionEngine()

    classification = {
        'category': EmailCategory.PROMOTIONAL,
        'confidence': 95,
        'verified': True
    }

    decision = engine.should_delete(
        email_id='test123',
        classification=classification,
        is_protected_domain=False,
        has_manual_flags=False,
        manual_flag_list=[]
    )

    assert decision.should_delete == True, "Should delete when all criteria met"
    assert len(decision.blocks) == 0, "Should have no blocking factors"
    assert len(decision.reasons) == 5, "Should have 5 reasons (all criteria passed)"
    print("✓ Test passed: Should delete when all criteria met")


def test_should_not_delete_non_promotional():
    """Test: Should NOT delete non-promotional categories."""
    engine = DecisionEngine()

    for category in [EmailCategory.TRANSACTIONAL, EmailCategory.SYSTEM_SECURITY,
                     EmailCategory.SOCIAL_PLATFORM, EmailCategory.PERSONAL_HUMAN]:
        classification = {
            'category': category,
            'confidence': 95,
            'verified': True
        }

        decision = engine.should_delete(
            email_id='test123',
            classification=classification,
            is_protected_domain=False,
            has_manual_flags=False
        )

        assert decision.should_delete == False, f"Should NOT delete {category.value}"
        assert any('Category is' in block for block in decision.blocks), \
            f"Should be blocked by category for {category.value}"

    print("✓ Test passed: Should NOT delete non-promotional categories")


def test_should_not_delete_not_verified():
    """Test: Should NOT delete if not verified by dual-agent."""
    engine = DecisionEngine()

    classification = {
        'category': EmailCategory.PROMOTIONAL,
        'confidence': 95,
        'verified': False  # Not verified!
    }

    decision = engine.should_delete(
        email_id='test123',
        classification=classification,
        is_protected_domain=False,
        has_manual_flags=False
    )

    assert decision.should_delete == False, "Should NOT delete unverified emails"
    assert any('Not verified' in block for block in decision.blocks), \
        "Should be blocked by verification status"
    assert engine.stats['blocked_by_verification'] == 1
    print("✓ Test passed: Should NOT delete unverified emails")


def test_should_not_delete_low_confidence():
    """Test: Should NOT delete if confidence < 90%."""
    engine = DecisionEngine()

    for confidence in [50, 70, 85, 89]:
        classification = {
            'category': EmailCategory.PROMOTIONAL,
            'confidence': confidence,
            'verified': True
        }

        decision = engine.should_delete(
            email_id='test123',
            classification=classification,
            is_protected_domain=False,
            has_manual_flags=False
        )

        assert decision.should_delete == False, \
            f"Should NOT delete with {confidence}% confidence"
        assert any(f'Confidence {confidence}%' in block for block in decision.blocks), \
            f"Should be blocked by low confidence ({confidence}%)"

    print("✓ Test passed: Should NOT delete low confidence emails")


def test_should_not_delete_protected_domain():
    """Test: Should NOT delete protected domains (CRITICAL)."""
    engine = DecisionEngine()

    classification = {
        'category': EmailCategory.PROMOTIONAL,
        'confidence': 99,
        'verified': True
    }

    decision = engine.should_delete(
        email_id='test123',
        classification=classification,
        is_protected_domain=True,  # Protected domain!
        has_manual_flags=False
    )

    assert decision.should_delete == False, \
        "Should NOT delete protected domain (banks, investment, etc.)"
    assert any('Protected domain' in block for block in decision.blocks), \
        "Should be blocked by protected domain"
    assert engine.stats['blocked_by_domain'] == 1
    print("✓ Test passed: Should NOT delete protected domains (CRITICAL)")


def test_should_not_delete_starred():
    """Test: Should NOT delete starred/important emails."""
    engine = DecisionEngine()

    classification = {
        'category': EmailCategory.PROMOTIONAL,
        'confidence': 95,
        'verified': True
    }

    decision = engine.should_delete(
        email_id='test123',
        classification=classification,
        is_protected_domain=False,
        has_manual_flags=True,
        manual_flag_list=['starred']
    )

    assert decision.should_delete == False, "Should NOT delete starred emails"
    assert any('Manually flagged' in block for block in decision.blocks), \
        "Should be blocked by manual flags"
    assert engine.stats['blocked_by_manual_flags'] == 1
    print("✓ Test passed: Should NOT delete starred/important emails")


def test_investment_platform_scenario():
    """Test: CRITICAL investment platform scenario - must NEVER delete."""
    engine = DecisionEngine()

    # Scenario: AI classified as promotional with high confidence,
    # but domain checker caught it as protected
    classification = {
        'category': EmailCategory.PROMOTIONAL,  # Misclassified!
        'confidence': 99,  # High confidence
        'verified': True   # Even verified!
    }

    decision = engine.should_delete(
        email_id='zerodha_email',
        classification=classification,
        is_protected_domain=True,  # Domain checker SAVES it
        has_manual_flags=False
    )

    assert decision.should_delete == False, \
        "CRITICAL: Investment platform email must NEVER be deleted"
    assert decision.is_protected_domain == True
    print("✓ Test passed: CRITICAL investment platform scenario - NEVER deleted")


def test_stats_tracking():
    """Test: Statistics tracking works correctly."""
    engine = DecisionEngine()

    # Create various scenarios
    scenarios = [
        # (category, verified, confidence, protected, flags, should_delete)
        (EmailCategory.PROMOTIONAL, True, 95, False, False, True),   # Should delete
        (EmailCategory.TRANSACTIONAL, True, 95, False, False, False), # Blocked by category
        (EmailCategory.PROMOTIONAL, False, 95, False, False, False),  # Blocked by verification
        (EmailCategory.PROMOTIONAL, True, 85, False, False, False),   # Blocked by confidence
        (EmailCategory.PROMOTIONAL, True, 95, True, False, False),    # Blocked by domain
        (EmailCategory.PROMOTIONAL, True, 95, False, True, False),    # Blocked by flags
    ]

    for category, verified, confidence, protected, flags, expected in scenarios:
        classification = {
            'category': category,
            'confidence': confidence,
            'verified': verified
        }
        engine.should_delete(
            'test',
            classification,
            protected,
            flags,
            ['starred'] if flags else []
        )

    assert engine.stats['total_evaluated'] == 6
    assert engine.stats['approved_for_deletion'] == 1
    assert engine.stats['blocked_by_category'] == 1
    assert engine.stats['blocked_by_verification'] == 1
    assert engine.stats['blocked_by_confidence'] == 1
    assert engine.stats['blocked_by_domain'] == 1
    assert engine.stats['blocked_by_manual_flags'] == 1

    print("✓ Test passed: Statistics tracking")
    print(f"\n{engine.get_stats_summary()}")


def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("DECISION ENGINE TEST SUITE")
    print("=" * 60)
    print()

    test_should_delete_all_criteria_met()
    test_should_not_delete_non_promotional()
    test_should_not_delete_not_verified()
    test_should_not_delete_low_confidence()
    test_should_not_delete_protected_domain()
    test_should_not_delete_starred()
    test_investment_platform_scenario()
    test_stats_tracking()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)


if __name__ == '__main__':
    run_all_tests()
