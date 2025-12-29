"""
Example: Using the Gmail Classifier Programmatically

This script demonstrates how to use the email classifier components
programmatically instead of via the CLI.
"""

from config import Market, Language, EmailCategory
from domain_checker import DomainChecker
from decision_engine import DecisionEngine
from gmail_client import GmailClient
from ai_classifier import AIClassifier, AIProvider


def example_1_domain_checking():
    """Example 1: Check if domains are protected"""
    print("=" * 80)
    print("Example 1: Domain Protection Checking")
    print("=" * 80)

    checker = DomainChecker(Market.ALL)

    test_emails = [
        "alerts@zerodha.com",      # India - Protected
        "deals@shop.com",          # Not protected
        "service@deutsche-bank.de", # Germany - Protected
    ]

    for email in test_emails:
        result = checker.check_domain(email)
        print(f"\n{email}:")
        print(f"  Protected: {result.is_protected}")
        if result.is_protected:
            print(f"  Market: {result.market.value}")
            print(f"  Category: {result.category}")
            print(f"  Reason: {result.reason}")


def example_2_decision_evaluation():
    """Example 2: Evaluate deletion decisions"""
    print("\n" + "=" * 80)
    print("Example 2: Decision Engine Evaluation")
    print("=" * 80)

    domain_checker = DomainChecker(Market.ALL)
    engine = DecisionEngine(domain_checker, confidence_threshold=90.0)

    # Test case 1: Safe promotional email
    result1 = engine.evaluate(
        email_id="test001",
        category="promotional",
        confidence=95.0,
        verified=True,
        from_address="deals@onlineshop.com",
        is_starred=False,
        is_important=False,
    )

    print(f"\nTest 1 - Safe promotional email:")
    print(f"  Decision: {result1.decision.value}")
    print(f"  Confidence: {result1.confidence}%")
    print(f"  Reason: {result1.final_reason}")

    # Test case 2: Protected domain
    result2 = engine.evaluate(
        email_id="test002",
        category="promotional",
        confidence=95.0,
        verified=True,
        from_address="alerts@schwab.com",
        is_starred=False,
        is_important=False,
    )

    print(f"\nTest 2 - Protected domain (brokerage):")
    print(f"  Decision: {result2.decision.value}")
    print(f"  Reason: {result2.final_reason}")

    # Print statistics
    print("\nEngine Statistics:")
    stats = engine.get_stats()
    print(f"  Total processed: {stats['total_processed']}")
    print(f"  Approved: {stats['approved']}")
    print(f"  Rejected: {stats['rejected']}")


def example_3_gmail_fetching():
    """Example 3: Fetch emails from Gmail"""
    print("\n" + "=" * 80)
    print("Example 3: Fetching Emails from Gmail")
    print("=" * 80)

    client = GmailClient()

    # Authenticate
    if not client.authenticate():
        print("Authentication failed!")
        return

    # Fetch latest 5 emails
    print("\nFetching latest 5 emails...")
    emails = client.fetch_emails(max_results=5)

    for i, email in enumerate(emails, 1):
        print(f"\n{i}. {email.subject}")
        print(f"   From: {email.from_address}")
        print(f"   Starred: {email.is_starred}")
        print(f"   Important: {email.is_important}")
        print(f"   Snippet: {email.snippet[:80]}...")


def example_4_ai_classification():
    """Example 4: AI Classification with Gemini"""
    print("\n" + "=" * 80)
    print("Example 4: AI Classification")
    print("=" * 80)

    import os
    if not os.getenv('GEMINI_API_KEY'):
        print("GEMINI_API_KEY not set - skipping AI classification example")
        return

    classifier = AIClassifier(provider=AIProvider.GEMINI)

    # Sample emails
    emails = [
        {
            "from": "deals@shop.com",
            "subject": "50% OFF Sale Today!",
            "body": "Get 50% off all items. Limited time offer!",
        },
        {
            "from": "alerts@zerodha.com",
            "subject": "Dividend Credited",
            "body": "Rs. 500 dividend has been credited to your account.",
        },
    ]

    print("\nClassifying emails...")
    results = classifier.classify_batch(emails)

    for email, result in zip(emails, results):
        print(f"\nFrom: {email['from']}")
        print(f"Subject: {email['subject']}")
        print(f"  Category: {result.category.value}")
        print(f"  Confidence: {result.confidence}%")
        print(f"  Verified: {result.verified}")
        print(f"  Language: {result.language}")
        print(f"  Reason: {result.reason}")


def example_5_complete_workflow():
    """Example 5: Complete classification workflow"""
    print("\n" + "=" * 80)
    print("Example 5: Complete Classification Workflow")
    print("=" * 80)

    import os
    if not os.getenv('GEMINI_API_KEY'):
        print("GEMINI_API_KEY not set - skipping complete workflow example")
        return

    # Initialize components
    gmail_client = GmailClient()
    domain_checker = DomainChecker(Market.ALL)
    decision_engine = DecisionEngine(domain_checker)
    ai_classifier = AIClassifier(provider=AIProvider.GEMINI)

    # Step 1: Authenticate
    print("\n1. Authenticating with Gmail...")
    if not gmail_client.authenticate():
        print("   Failed!")
        return
    print("   Success!")

    # Step 2: Fetch emails
    print("\n2. Fetching emails...")
    emails = gmail_client.fetch_emails(max_results=3)
    print(f"   Fetched {len(emails)} emails")

    # Step 3: Classify
    print("\n3. Classifying with AI...")
    email_data = [
        {
            "from": e.from_address,
            "subject": e.subject,
            "body": e.body[:500],
        }
        for e in emails
    ]
    classifications = ai_classifier.classify_batch(email_data)
    print(f"   Classified {len(classifications)} emails")

    # Step 4: Make decisions
    print("\n4. Evaluating with decision engine...")
    for email, classification in zip(emails, classifications):
        result = decision_engine.evaluate(
            email_id=email.id,
            category=classification.category.value,
            confidence=classification.confidence,
            verified=classification.verified,
            from_address=email.from_address,
            is_starred=email.is_starred,
            is_important=email.is_important,
        )

        print(f"\n   Email: {email.subject[:50]}...")
        print(f"   Category: {classification.category.value}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Confidence: {classification.confidence}%")

        # Show gate failures
        failed_gates = [g for g in result.gates if not g.passed]
        if failed_gates:
            print(f"   Failed gates:")
            for gate in failed_gates:
                print(f"     - {gate.gate_name}: {gate.reason}")

    # Step 5: Statistics
    print("\n5. Statistics:")
    stats = decision_engine.get_stats()
    print(f"   Approved: {stats['approved']}")
    print(f"   Rejected: {stats['rejected']}")
    print(f"   Flagged: {stats['flagged']}")


if __name__ == "__main__":
    print("Gmail Email Classifier - Usage Examples")
    print("=" * 80)

    # Run examples
    example_1_domain_checking()
    example_2_decision_evaluation()

    # These require Gmail authentication
    # Uncomment to run:
    # example_3_gmail_fetching()
    # example_4_ai_classification()
    # example_5_complete_workflow()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("\nTo run Gmail/AI examples, uncomment the function calls at the bottom")
    print("of this script and ensure you have credentials.json and API keys set.")
