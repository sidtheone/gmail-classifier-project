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
# DEBUG SETTINGS
# =============================================================================

DEBUG: bool = False  # Set via --debug flag


# =============================================================================
# GMAIL API SETTINGS
# =============================================================================

GMAIL_SCOPES: List[str] = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE: str = 'credentials.json'
TOKEN_FILE: str = 'token.pickle'


# =============================================================================
# PROCESSING SETTINGS
# =============================================================================

BATCH_SIZE: int = 100  # Emails to fetch from Gmail per batch
AI_BATCH_SIZE: int = 200  # Emails to classify in single API call (optimized for 4M TPM)
MAX_BODY_LENGTH: int = 1000


# =============================================================================
# AI CLASSIFICATION SETTINGS
# =============================================================================

# Provider: "anthropic" or "gemini"
AI_PROVIDER: str = 'gemini'  # Default to Gemini (cheapest option)

# Anthropic models
ANTHROPIC_MODEL: str = 'claude-haiku-4-5-20251001'

# Gemini models - Latest options (Dec 2025):
# - 'gemini-2.5-flash-lite'  : Fastest, cheapest - ideal for classification (DEFAULT)
# - 'gemini-2.5-flash'       : Best price-performance
# - 'gemini-2.5-pro'         : Most capable, higher cost
# - 'gemini-2.0-flash'       : Previous gen, stable
# - 'gemini-3-flash-preview' : Newest, experimental
GEMINI_MODEL: str = 'gemini-2.5-flash-lite'

AI_MAX_TOKENS: int = 200
CONFIDENCE_THRESHOLD: int = 75  # Mark as promotional if >= this
VERIFICATION_THRESHOLD: int = 85  # Trigger Agent 2 if < this

# Cost per million tokens (for estimation)
COSTS = {
    'anthropic': {'input': 0.25, 'output': 1.25},   # Claude Haiku
    'gemini': {'input': 0.075, 'output': 0.30},      # Gemini Flash
}


# =============================================================================
# RATE LIMITING
# =============================================================================

# Gemini 2.5 Flash-Lite Rate Limits (Paid Tier - Dec 2025)
RATE_LIMIT_TPM: int = 4000000  # Tokens per minute (4M TPM)
RATE_LIMIT_RPD: int = 10000    # Requests per day (increased for paid tier)
RATE_LIMIT_RPM: int = 60       # Requests per minute (increased for higher TPM)

API_DELAY: float = 0.1  # seconds between API calls (reduced for higher limits)
MAX_RETRIES: int = 5
INITIAL_BACKOFF: float = 60.0  # seconds - wait 60s when rate limited
RATE_LIMIT_BACKOFF: float = 60.0  # seconds - fixed wait for rate limit errors


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
# PROTECTED DOMAINS (never mark as promotional)
# =============================================================================

# Banks and Financial Institutions
PROTECTED_DOMAINS_BANKS: List[str] = [
    # German Banks
    'deutsche-bank.de', 'deutschebank.com', 'commerzbank.de', 'commerzbank.com',
    'sparkasse.de', 'dkb.de', 'ing.de', 'ing-diba.de', 'comdirect.de',
    'hypovereinsbank.de', 'unicredit.de', 'postbank.de', 'targobank.de',
    'volksbank.de', 'raiffeisen.de', 'sparda.de', 'n26.com', 'bunq.com',

    # US/International Banks
    'chase.com', 'bankofamerica.com', 'wellsfargo.com', 'citi.com', 'citibank.com',
    'usbank.com', 'pnc.com', 'capitalone.com', 'tdbank.com', 'hsbc.com',
    'barclays.com', 'barclays.co.uk', 'santander.com', 'santander.de',
    'ubs.com', 'credit-suisse.com', 'goldmansachs.com', 'morganstanley.com',

    # Indian Banks
    'sbi.co.in', 'onlinesbi.sbi', 'statebankofindia.com', 'hdfcbank.com',
    'icicibank.com', 'axisbank.com', 'pnbindia.in', 'pnb.co.in',
    'bankofbaroda.in', 'bankofbaroda.com', 'canarabank.com', 'canarabank.in',
    'unionbankofindia.co.in', 'idfcfirstbank.com', 'kotak.com', 'kotakbank.com',
    'indusind.com', 'yesbank.in', 'bankofindia.co.in', 'bankofindia.com',
    'centralbankofindia.co.in', 'indianbank.in', 'ucobank.com', 'ucobank.co.in',
    'rbl.co.in', 'rblbank.com', 'aubank.in', 'federalbank.co.in',
    'southindianbank.com', 'karnatakabank.com', 'cityunionbank.com',

    # Payment Services
    'paypal.com', 'paypal.de', 'stripe.com', 'wise.com', 'transferwise.com',
    'revolut.com', 'klarna.com', 'adyen.com',
    # Indian Payment Services
    'paytm.com', 'paytmbank.com', 'phonepe.com', 'bharatpe.com', 'razorpay.com',
    'googlepay.com', 'amazonpay.in', 'mobikwik.com', 'freecharge.in',
]

# Investment Platforms, Brokers & Mutual Funds (CRITICAL - prevent misclassification)
PROTECTED_DOMAINS_INVESTMENT: List[str] = [
    # Indian Stock Brokers
    'zerodha.com', 'zerodha.net', 'kite.trade', 'coin.zerodha.com',
    'groww.in', 'groww.com',
    'upstox.com', 'upstox.in',
    'icicidirect.com', 'icicisecurities.com',
    '5paisa.com',
    'angelone.in', 'angelbroking.com',
    'kotaksecurities.com',
    'hdfcsec.com',
    'sharekhan.com',
    'motilaloswal.com',
    'axisdirect.in',
    'edelweiss.in', 'edelweissfin.com',

    # Indian Mutual Funds
    'sbimf.com', 'sbimutualfund.com',
    'axismf.com',
    'miraeassetmf.co.in',
    'hdfcfund.com',
    'icicipruamc.com', 'iciciprulife.com',
    'dspim.com', 'dspinvestment.com',
    'ppfas.in', 'ppfas.com',
    'sundarammutual.com',
    'franklintempletonindia.com', 'franklintempleton.co.in',
    'motilaloswalmf.com',
    'kotakmf.com',
    'utimf.com',
    'nipponindiaim.com',
    'tatamutualfund.com',

    # Fund Registrars (CRITICAL - handle all mutual fund transactions)
    'kfintech.com', 'kfintech.net', 'kfintech.co.in',
    'camsonline.com', 'cams.co.in', 'camsonline.co.in',

    # Investment Aggregators
    'fundsindia.com',
    'mfutility.in',
    'kuvera.in',
    'paytmmoney.com',

    # US Brokers
    'schwab.com', 'charlesschwab.com',
    'fidelity.com',
    'vanguard.com',
    'etrade.com',
    'tdameritrade.com',
    'robinhood.com',
    'interactivebrokers.com',
    'merrilledge.com',
    'scottrade.com',
    'ally.com',
    'webull.com',

    # Cryptocurrency Platforms
    'coinbase.com',
    'kraken.com',
    'binance.com', 'binance.us',
    'gemini.com',

    # Stock Exchanges
    'nse.co.in', 'nseindia.com',
    'bse.co.in', 'bseindia.com',
    'nasdaq.com',
    'nyse.com',
    'lse.co.uk',  # London Stock Exchange
]

# Government and Authorities
PROTECTED_DOMAINS_GOVERNMENT: List[str] = [
    # German Government
    'bundesregierung.de', 'bund.de', 'bayern.de', 'nrw.de', 'bw.de',
    'berlin.de', 'hamburg.de', 'hessen.de', 'niedersachsen.de',
    'finanzamt.de', 'arbeitsagentur.de', 'bundesagentur.de',
    'elster.de', 'bzst.de', 'zoll.de', 'polizei.de',
    'krankenkasse.de', 'gkv.de', 'rentenversicherung.de', 'drv.de',

    # US Government
    'gov', 'irs.gov', 'ssa.gov', 'state.gov', 'dhs.gov', 'uscis.gov',

    # Indian Government
    'gov.in', 'nic.in', 'incometax.gov.in', 'incometaxindia.gov.in',
    'tin.nsdl.com', 'epfindia.gov.in', 'epfindia.com', 'uidai.gov.in',
    'digilocker.gov.in', 'india.gov.in', 'mygov.in', 'aadhaar.gov.in',
    'gst.gov.in', 'cbic.gov.in', 'cbdt.gov.in', 'rbi.org.in',
    'sebi.gov.in', 'irdai.gov.in', 'pfrda.org.in', 'npci.org.in',
    'nsdl.co.in', 'cdslindia.com', 'passportindia.gov.in',

    # EU/International
    'europa.eu', 'ec.europa.eu', 'gov.uk', 'gov.au', 'gc.ca',
]

# Healthcare and Insurance
PROTECTED_DOMAINS_HEALTHCARE: List[str] = [
    # German Health Insurance
    'tk.de', 'techniker.de', 'aok.de', 'barmer.de', 'dak.de',
    'ikk.de', 'bkk.de', 'knappschaft.de', 'hek.de',

    # Insurance Companies
    'allianz.de', 'allianz.com', 'axa.de', 'axa.com', 'ergo.de',
    'huk.de', 'huk24.de', 'debeka.de', 'signal-iduna.de',

    # Indian Healthcare and Insurance
    'licindia.in', 'licindia.com', 'maxhealthcare.com', 'apollohospitals.com',
    'fortishealthcare.com', 'aiims.edu', 'icicilombard.com', 'hdfcergo.com',
    'bajajallianz.com', 'starhealth.in', 'reliancegeneral.co.in',
    'nationalinsurance.nic.co.in', 'orientalinsurance.org.in', 'newindia.co.in',
    'uiic.co.in', 'careinsurance.com', 'maxbupa.com', 'niva.co.in',
    'manipalhospitals.com', 'narayanahealth.org', 'medanta.org',
]

# Utilities and Essential Services
PROTECTED_DOMAINS_UTILITIES: List[str] = [
    # Telecom
    'telekom.de', 't-online.de', 'vodafone.de', 'o2.de', 'telefonica.de',
    '1und1.de', 'congstar.de',

    # Energy
    'eon.de', 'rwe.de', 'vattenfall.de', 'enbw.de', 'stadtwerke.de',

    # Other Essential
    'gez.de', 'rundfunkbeitrag.de', 'schufa.de',

    # Indian Telecom
    'airtel.in', 'airtel.com', 'myvi.in', 'myvi.com', 'vodafone.in',
    'jio.com', 'reliancejio.com', 'bsnl.co.in', 'bsnl.in', 'mtnl.in',
    'mtnl.net.in', 'idea.adityabirla.com',

    # Indian Energy and Utilities
    'adanipower.com', 'ntpc.co.in', 'powergrid.in', 'tatapower.com',
    'mahadiscom.in', 'bsesdelhi.com', 'cesc.co.in', 'delhipower.com',
]

# Educational Institutions
PROTECTED_DOMAINS_EDUCATION: List[str] = [
    'edu', 'ac.uk', 'uni-', 'university', 'hochschule', 'fh-',
    'tu-', 'rwth-', 'lmu.de', 'tum.de', 'kit.edu',

    # Indian Educational Institutions
    'ac.in', 'iitb.ac.in', 'iitd.ac.in', 'iitm.ac.in', 'iitk.ac.in',
    'iitkgp.ac.in', 'iitr.ac.in', 'iitbhu.ac.in', 'iitg.ac.in',
    'iimbg.ac.in', 'iima.ac.in', 'iimb.ac.in', 'iimc.ac.in',
    'bits-pilani.ac.in', 'du.ac.in', 'amu.ac.in', 'bhu.ac.in',
    'jnu.ac.in', 'annauniv.edu', 'iitbombay.org', 'iisc.ac.in',
    'nit.ac.in', 'nitt.edu', 'nitk.ac.in', 'ipu.ac.in',
]

# Combine all protected domains
PROTECTED_DOMAINS: List[str] = (
    PROTECTED_DOMAINS_BANKS +
    PROTECTED_DOMAINS_INVESTMENT +  # CRITICAL: Investment platforms protection
    PROTECTED_DOMAINS_GOVERNMENT +
    PROTECTED_DOMAINS_HEALTHCARE +
    PROTECTED_DOMAINS_UTILITIES +
    PROTECTED_DOMAINS_EDUCATION
)

# Domain patterns (regex) - for partial matching
PROTECTED_DOMAIN_PATTERNS: List[str] = [
    r'\.gov$', r'\.gov\.',           # Government domains
    r'\.gov\.in$', r'\.nic\.in$',    # Indian government domains
    r'\.edu$', r'\.ac\.',            # Educational domains
    r'\.ac\.in$',                    # Indian educational domains
    r'bank', r'sparkasse', r'volks', # Bank-related
    r'securities', r'broker',        # Investment brokers
    r'mutualfund', r'mutual.*fund',  # Mutual funds
    r'kfintech', r'camsonline',      # Fund registrars
    r'\bmf\b',                       # Mutual fund abbreviation
    r'amc$',                         # Asset Management Company
    r'finanzamt', r'steuer',         # Tax authorities
    r'versicherung', r'insurance',   # Insurance
    r'polizei', r'police',           # Police
    r'kranken', r'health',           # Healthcare
    r'universitaet', r'university',  # Universities
    r'\biit', r'\biim', r'\bnit',    # Indian institutes (IIT, IIM, NIT)
]


# =============================================================================
# KEYWORD MATCHING SETTINGS
# =============================================================================

KEYWORD_THRESHOLD: int = 3  # Minimum keyword matches to auto-classify as promotional
