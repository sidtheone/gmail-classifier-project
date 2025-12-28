#!/usr/bin/env python3
"""
Tests for KeywordMatcher - English and German promotional email detection.

Run with: python test_keyword_matcher.py
"""

import sys
from typing import Dict, List

from keyword_matcher import KeywordMatcher


# =============================================================================
# TEST DATA - ENGLISH PROMOTIONAL EMAILS
# =============================================================================

ENGLISH_PROMOTIONAL: List[Dict[str, str]] = [
    {
        "name": "E-commerce Sale",
        "subject": "Flash Sale! 50% Off Everything - Today Only!",
        "sender": "deals@fashionstore.com",
        "body": """Hi there!

Don't miss our biggest flash sale of the year! For today only, enjoy 50% off everything in store.

Shop now and save big on:
- Winter jackets and coats
- Designer handbags
- Premium footwear

Use code FLASH50 at checkout. Free shipping on orders over $50.

Hurry - this exclusive offer expires at midnight!

Shop Now: [link]

To unsubscribe from our mailing list, click here."""
    },
    {
        "name": "Newsletter Digest",
        "subject": "Your Weekly Tech Newsletter - New Arrivals Inside",
        "sender": "newsletter@techgadgets.com",
        "body": """Weekly Tech Digest

Hey gadget lover!

Here's what's new this week:

NEW ARRIVALS:
- Smart Home Hub Pro - Now available
- Wireless Earbuds X3 - Just dropped

DEALS OF THE WEEK:
- Save up to 40% on refurbished laptops
- Buy one get one free on phone cases

Recommended for you based on your browsing history:
- Portable chargers
- USB-C adapters

View in browser | Manage preferences | Unsubscribe"""
    },
    {
        "name": "Loyalty Rewards",
        "subject": "You've earned 500 bonus points! Redeem now",
        "sender": "rewards@coffeeshop.com",
        "body": """Congratulations!

You've earned 500 bonus points on your loyalty account!

Your current balance: 1,250 points

Redeem your points for:
- Free drinks
- Exclusive merchandise
- Special discounts

As a VIP member, you also get early access to our seasonal menu.

Claim now before your points expire!

Click here to redeem your rewards.

Update your preferences | Unsubscribe"""
    },
    {
        "name": "Black Friday Promo",
        "subject": "Black Friday Preview - Exclusive Early Access",
        "sender": "promo@electronics.com",
        "body": """BLACK FRIDAY STARTS EARLY FOR YOU!

As a valued customer, you get exclusive early access to our Black Friday deals.

DOORBUSTERS:
- 4K TVs starting at $299
- Laptops up to 60% off
- Gaming consoles in stock

Limited quantities available. Shop now before they're gone!

Add to cart now and checkout when the sale goes live.

Free shipping on all orders. No coupon needed.

View online | Unsubscribe from promotional emails"""
    },
    {
        "name": "Subscription Box",
        "subject": "Your monthly box is ready - Plus a special offer inside!",
        "sender": "hello@beautybox.com",
        "body": """Your October Beauty Box is on its way!

Inside this month's box:
- Luxury face serum
- Organic lip balm
- Limited edition palette

SPECIAL OFFER: Upgrade to annual subscription and save 20%!

Get free shipping on your next order with code FREESHIP.

Refer a friend and you both get $10 off!

Love your box? Share on social media!

Manage subscription | Update preferences | Unsubscribe"""
    }
]


# =============================================================================
# TEST DATA - GERMAN PROMOTIONAL EMAILS
# =============================================================================

GERMAN_PROMOTIONAL: List[Dict[str, str]] = [
    {
        "name": "Online Shop Sale",
        "subject": "Sommerschlussverkauf - Bis zu 70% Rabatt!",
        "sender": "angebote@modeshop.de",
        "body": """Liebe Kundin, lieber Kunde,

unser großer Sommerschlussverkauf hat begonnen!

Sparen Sie bis zu 70% auf ausgewählte Artikel:
- Sommerkleider ab 19,99€
- Herrenmode stark reduziert
- Schuhe im Sale

Jetzt shoppen und Schnäppchen sichern!

Kostenloser Versand ab 50€ Bestellwert.

Nur für kurze Zeit - greifen Sie jetzt zu!

Im Browser ansehen | Newsletter abbestellen"""
    },
    {
        "name": "Newsletter Angebot",
        "subject": "Ihre wöchentlichen Angebote - Nur heute: Gratis Versand",
        "sender": "newsletter@kaufhaus.de",
        "body": """Guten Tag!

Diese Woche haben wir besondere Angebote für Sie:

NEUHEITEN:
- Smart TV 55 Zoll - Jetzt erhältlich
- Küchenmaschine Premium - Neu im Sortiment

AKTIONEN:
- 30% Rabatt auf Elektronikartikel
- Gutscheincode SOMMER23 für 10€ Rabatt

Das könnte Ihnen gefallen:
- Bluetooth Lautsprecher
- Fitness Tracker

Jetzt entdecken und sparen!

Abmelden | E-Mail-Einstellungen ändern"""
    },
    {
        "name": "Treueprogramm",
        "subject": "Sie haben 1000 Bonuspunkte gesammelt!",
        "sender": "service@supermarkt.de",
        "body": """Herzlichen Glückwunsch!

Sie haben 1000 Bonuspunkte auf Ihrem Treuekonto!

Punkte einlösen für:
- Prämien aus unserem Katalog
- Rabattgutscheine
- Exklusive Produkte

Als treuer Kunde erhalten Sie exklusiven Zugang zu Sonderaktionen.

Jetzt Punkte einlösen!

Ihre Prämie wartet auf Sie.

Vom Newsletter abmelden"""
    },
    {
        "name": "Sonderaktion",
        "subject": "Exklusiv für Sie: 25% Rabatt auf alles!",
        "sender": "info@buchhandlung.de",
        "body": """Nur für Sie!

Als geschätzter Kunde erhalten Sie heute 25% Rabatt auf Ihre gesamte Bestellung.

Ihr persönlicher Gutscheincode: LESEN25

Gültig bis Sonntag auf:
- Bestseller
- Neuerscheinungen
- Hörbücher

Jetzt bestellen und sparen!

Versandkostenfrei ab 20€.

Nicht verpassen - nur noch wenige Tage!

Hier klicken zum Shoppen | Abbestellen"""
    },
    {
        "name": "Reise Newsletter",
        "subject": "Last Minute Angebote - Urlaub ab 299€",
        "sender": "deals@reiseportal.de",
        "body": """Traumurlaub zum Schnäppchenpreis!

Unsere Last Minute Angebote:
- Mallorca 1 Woche ab 299€
- Türkei All-Inclusive ab 449€
- Kreuzfahrt Mittelmeer ab 599€

Jetzt buchen und bis zu 40% sparen!

Gratis Stornierung bis 24h vor Abflug.

Exklusiv für Newsletter-Abonnenten: 50€ Rabatt mit Code SONNE50

Jetzt sichern - nur solange der Vorrat reicht!

Im Browser ansehen | Newsletter abbestellen"""
    }
]


# =============================================================================
# TEST DATA - NON-PROMOTIONAL EMAILS (CONTROL GROUP)
# =============================================================================

NON_PROMOTIONAL: List[Dict[str, str]] = [
    {
        "name": "Order Confirmation",
        "subject": "Order Confirmation #12345",
        "sender": "orders@amazon.com",
        "body": """Thank you for your order!

Order Number: 12345
Date: October 15, 2024

Items ordered:
- Blue T-Shirt (Size M) - $29.99

Shipping Address:
123 Main Street
New York, NY 10001

Estimated delivery: October 18-20

Track your package: [link]

Questions? Contact customer service."""
    },
    {
        "name": "Personal Email",
        "subject": "Re: Dinner on Saturday?",
        "sender": "john.smith@gmail.com",
        "body": """Hey!

Saturday works great for me. How about 7pm at that Italian place we talked about?

Let me know if that works for you.

Cheers,
John"""
    },
    {
        "name": "Shipping Notification",
        "subject": "Your package has shipped",
        "sender": "shipping@fedex.com",
        "body": """Your package is on its way!

Tracking Number: 1234567890
From: Online Store
To: Your Address

Current Status: In Transit
Expected Delivery: Tomorrow by 5pm

Track your package online."""
    },
    {
        "name": "German Receipt",
        "subject": "Ihre Rechnung Nr. 2024-1234",
        "sender": "rechnung@telekom.de",
        "body": """Sehr geehrter Kunde,

anbei erhalten Sie Ihre Rechnung für Oktober 2024.

Rechnungsnummer: 2024-1234
Betrag: 49,99€
Fällig am: 01.11.2024

Die Abbuchung erfolgt automatisch von Ihrem Konto.

Mit freundlichen Grüßen,
Ihr Telekom Team"""
    },
    {
        "name": "Work Email",
        "subject": "Meeting tomorrow at 10am",
        "sender": "boss@company.com",
        "body": """Hi team,

Reminder that we have our weekly sync tomorrow at 10am in the conference room.

Agenda:
1. Project updates
2. Q4 planning
3. Open discussion

Please come prepared with your status updates.

Thanks,
Manager"""
    }
]


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_tests() -> bool:
    """
    Run all keyword matcher tests.

    Returns:
        True if all tests passed, False otherwise.
    """
    matcher = KeywordMatcher()

    print("=" * 70)
    print("KEYWORD MATCHER TEST RESULTS")
    print("=" * 70)

    results = {
        "english_promo": {"passed": 0, "failed": 0},
        "german_promo": {"passed": 0, "failed": 0},
        "non_promo": {"passed": 0, "failed": 0}
    }

    # Test English promotional emails (should match)
    print("\n[1/3] ENGLISH PROMOTIONAL EMAILS (expected: promotional)")
    print("-" * 70)

    for email in ENGLISH_PROMOTIONAL:
        email_content = {
            "subject": email["subject"],
            "body": email["body"]
        }
        is_promo, count, keywords = matcher.check(email_content)

        passed = is_promo is True
        status = "PASS" if passed else "FAIL"

        if passed:
            results["english_promo"]["passed"] += 1
        else:
            results["english_promo"]["failed"] += 1

        print(f"  [{status}] {email['name']}")
        print(f"        Matches: {count} | Keywords: {', '.join(keywords[:5])}")

    # Test German promotional emails (should match)
    print("\n[2/3] GERMAN PROMOTIONAL EMAILS (expected: promotional)")
    print("-" * 70)

    for email in GERMAN_PROMOTIONAL:
        email_content = {
            "subject": email["subject"],
            "body": email["body"]
        }
        is_promo, count, keywords = matcher.check(email_content)

        passed = is_promo is True
        status = "PASS" if passed else "FAIL"

        if passed:
            results["german_promo"]["passed"] += 1
        else:
            results["german_promo"]["failed"] += 1

        print(f"  [{status}] {email['name']}")
        print(f"        Matches: {count} | Keywords: {', '.join(keywords[:5])}")

    # Test non-promotional emails (should NOT match)
    print("\n[3/3] NON-PROMOTIONAL EMAILS (expected: not promotional)")
    print("-" * 70)

    for email in NON_PROMOTIONAL:
        email_content = {
            "subject": email["subject"],
            "body": email["body"]
        }
        is_promo, count, keywords = matcher.check(email_content)

        passed = is_promo is not True  # Should NOT be promotional
        status = "PASS" if passed else "FAIL"

        if passed:
            results["non_promo"]["passed"] += 1
        else:
            results["non_promo"]["failed"] += 1

        print(f"  [{status}] {email['name']}")
        keywords_str = ', '.join(keywords[:5]) if keywords else 'none'
        print(f"        Matches: {count} | Keywords: {keywords_str}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_passed = sum(r["passed"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())
    total = total_passed + total_failed

    print(f"\n  English Promotional: {results['english_promo']['passed']}/5 passed")
    print(f"  German Promotional:  {results['german_promo']['passed']}/5 passed")
    print(f"  Non-Promotional:     {results['non_promo']['passed']}/5 passed")
    print(f"\n  TOTAL: {total_passed}/{total} tests passed ({100*total_passed//total}%)")

    if total_failed == 0:
        print("\n  All tests PASSED!")
    else:
        print(f"\n  {total_failed} test(s) FAILED")

    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
