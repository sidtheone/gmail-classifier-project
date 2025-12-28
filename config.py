"""
Configuration constants for the Gmail Promotional Email Classifier.

This module contains all configurable settings including:
- Gmail API settings
- Processing parameters
- AI classification thresholds
- Rate limiting configuration
- Promotional keywords (English and German)
"""

from typing import List


# =============================================================================
# GMAIL API SETTINGS
# =============================================================================

GMAIL_SCOPES: List[str] = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE: str = 'credentials.json'
TOKEN_FILE: str = 'token.pickle'


# =============================================================================
# PROCESSING SETTINGS
# =============================================================================

BATCH_SIZE: int = 100
MAX_BODY_LENGTH: int = 1000


# =============================================================================
# AI CLASSIFICATION SETTINGS
# =============================================================================

AI_MODEL: str = 'claude-haiku-4-5-20251001'
AI_MAX_TOKENS: int = 200
CONFIDENCE_THRESHOLD: int = 75  # Mark as promotional if >= this
VERIFICATION_THRESHOLD: int = 85  # Trigger Agent 2 if < this


# =============================================================================
# RATE LIMITING
# =============================================================================

API_DELAY: float = 0.5  # seconds between API calls
MAX_RETRIES: int = 5
INITIAL_BACKOFF: float = 1.0  # seconds


# =============================================================================
# CACHE AND PROGRESS FILES
# =============================================================================

SENDER_CACHE_FILE: str = 'sender_cache.json'
PROGRESS_FILE: str = 'classifier_progress.json'
SUMMARY_FILE: str = 'sender_summary.json'


# =============================================================================
# PROMOTIONAL SENDER PATTERNS (regex for email addresses)
# =============================================================================

PROMOTIONAL_SENDER_PATTERNS: List[str] = [
    r'^marketing@',
    r'^newsletter@',
    r'^news@',
    r'^deals@',
    r'^promo@',
    r'^promotions@',
    r'^offers@',
    r'^sales@',
    r'^info@.*shop',
    r'^noreply@.*marketing',
    r'^hello@.*newsletter',
]


# =============================================================================
# PROMOTIONAL KEYWORDS - ENGLISH
# =============================================================================

PROMOTIONAL_KEYWORDS_EN: List[str] = [
    # Unsubscribe signals
    'unsubscribe', 'opt-out', 'opt out', 'manage preferences', 'email preferences',
    'update your preferences', 'subscription preferences',

    # Urgency
    'limited time', 'act now', "don't miss", 'hurry', 'expires soon', 'ending soon',
    'last chance', 'final hours', 'today only', 'this week only',

    # Discounts and offers
    'sale', 'discount', '% off', 'percent off', 'save up to', 'deal', 'deals',
    'offer', 'special offer', 'promo', 'promotion', 'promotional',

    # Free stuff
    'free shipping', 'free delivery', 'free trial', 'free gift', 'free sample',
    'complimentary', 'no cost',

    # Call to action
    'shop now', 'buy now', 'order now', 'get yours', 'claim now', 'grab yours',
    'add to cart', 'checkout now',

    # Exclusivity
    'exclusive', 'members only', 'vip', 'early access', 'sneak peek', 'preview',

    # Newsletter signals
    'newsletter', 'weekly digest', 'monthly update', 'daily deals', 'weekly roundup',

    # Coupons
    'coupon', 'voucher', 'promo code', 'discount code', 'redeem', 'use code',

    # Sales events
    'flash sale', 'clearance', 'black friday', 'cyber monday', 'holiday sale',
    'summer sale', 'winter sale', 'spring sale', 'fall sale', 'seasonal sale',

    # Product updates
    'new arrival', 'new arrivals', 'just dropped', 'back in stock', 'now available',
    'new collection', 'new release',

    # Loyalty
    'loyalty', 'rewards', 'points', 'earn points', 'redeem points', 'bonus points',

    # Personalization (marketing style)
    'recommended for you', 'you might like', 'based on your', 'picked for you',
    'curated for you', 'just for you',

    # Technical
    'view in browser', 'view online', 'click here', 'learn more',
]


# =============================================================================
# PROMOTIONAL KEYWORDS - GERMAN
# =============================================================================

PROMOTIONAL_KEYWORDS_DE: List[str] = [
    # Unsubscribe signals
    'abmelden', 'abbestellen', 'newsletter abbestellen', 'vom newsletter abmelden',
    'e-mail-einstellungen', 'benachrichtigungen verwalten',

    # Urgency
    'nur für kurze zeit', 'nur heute', 'bald endet', 'letzte chance', 'endet bald',
    'nicht verpassen', 'jetzt zugreifen', 'nur noch heute', 'läuft ab',

    # Discounts and offers
    'angebot', 'angebote', 'sonderangebot', 'rabatt', '% rabatt', 'prozent rabatt',
    'sparen', 'spare', 'günstiger', 'reduziert', 'preissenkung', 'schnäppchen',
    'aktion', 'aktionen', 'sonderaktion',

    # Free stuff
    'kostenloser versand', 'gratis', 'geschenkt', 'kostenlos', 'versandkostenfrei',
    'gratis versand', 'ohne versandkosten',

    # Call to action
    'jetzt kaufen', 'jetzt bestellen', 'jetzt shoppen', 'jetzt sichern',
    'jetzt entdecken', 'jetzt zuschlagen', 'hier klicken', 'mehr erfahren',
    'in den warenkorb',

    # Exclusivity
    'exklusiv', 'nur für sie', 'nur für dich', 'mitglieder', 'vip-zugang',
    'exklusiver zugang', 'vorab-zugang',

    # Newsletter signals
    'newsletter', 'wöchentlicher newsletter', 'monatsübersicht',

    # Coupons
    'gutschein', 'gutscheincode', 'rabattcode', 'einlösen', 'code einlösen',
    'mit code', 'ihr code',

    # Sales events
    'sale', 'schlussverkauf', 'ausverkauf', 'räumungsverkauf', 'sommerschlussverkauf',
    'winterschlussverkauf', 'black friday', 'cyber monday',

    # Product updates
    'neuheiten', 'neu eingetroffen', 'wieder verfügbar', 'jetzt erhältlich',
    'neue kollektion', 'neu im sortiment', 'wieder da',

    # Loyalty
    'treuepunkte', 'bonuspunkte', 'prämie', 'prämienpunkte', 'punkte sammeln',
    'punkte einlösen',

    # Personalization (marketing style)
    'das könnte ihnen gefallen', 'das könnte dir gefallen', 'empfohlen für sie',
    'für sie ausgewählt', 'passend für sie', 'unsere empfehlung',

    # Technical
    'im browser ansehen', 'online ansehen', 'webversion',
]


# =============================================================================
# KEYWORD MATCHING SETTINGS
# =============================================================================

KEYWORD_THRESHOLD: int = 3  # Minimum keyword matches to auto-classify as promotional
