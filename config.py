"""
Configuration for Safety-First Gmail Email Classifier
Supports USA, India, and Germany markets with bilingual classification
"""

from typing import Dict, List, Set
from enum import Enum


class Market(str, Enum):
    """Supported geographic markets"""
    USA = "usa"
    INDIA = "india"
    GERMANY = "germany"
    ALL = "all"


class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    GERMAN = "de"
    BOTH = "both"


class EmailCategory(str, Enum):
    """Email classification categories"""
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    SYSTEM_SECURITY = "system_security"
    SOCIAL_PLATFORM = "social_platform"
    PERSONAL_HUMAN = "personal_human"


class ConfidenceLevel(str, Enum):
    """Three-tier confidence system"""
    HIGH = "high"      # ≥90% - Eligible for auto-deletion after verification
    MEDIUM = "medium"  # 70-89% - Flag for human review
    LOW = "low"        # <70% - Keep, do not delete


# ============================================================================
# PROTECTED DOMAINS - ORGANIZED BY MARKET AND CATEGORY
# These domains are NEVER deleted, bypassing AI classification entirely
# ============================================================================

PROTECTED_DOMAINS: Dict[str, Dict[str, List[str]]] = {
    # ========== USA MARKET ==========
    "usa": {
        "investment_brokerage": [
            # Major US brokerages
            "schwab.com",
            "fidelity.com",
            "etrade.com",
            "tdameritrade.com",
            "vanguard.com",
            "robinhood.com",
            "webull.com",
            "interactivebrokers.com",
            "merrilledge.com",
            "sofi.com",
            "m1finance.com",
            "ally.com",
            "tastyworks.com",
            "tradestation.com",
        ],
        "banking": [
            # Major banks
            "chase.com",
            "bankofamerica.com",
            "wellsfargo.com",
            "citi.com",
            "usbank.com",
            "pnc.com",
            "capitalone.com",
            "tdbank.com",
            "americanexpress.com",
            "discover.com",
            "marcus.com",
            "goldmansachs.com",
            # Digital banks
            "chime.com",
            "revolut.com",
            "n26.com",
            "wise.com",
            "paypal.com",
            "venmo.com",
            "cashapp.com",
        ],
        "government": [
            # Government domains (exact match and pattern)
            ".gov",
            "irs.gov",
            "ssa.gov",
            "usps.com",
            "dmv.ca.gov",
            "dmv.ny.gov",
            # Add state-specific domains as needed
        ],
        "healthcare": [
            # Health insurance providers
            "uhc.com",
            "unitedhealthcare.com",
            "anthem.com",
            "bluecrossma.com",
            "cigna.com",
            "aetna.com",
            "humana.com",
            "kaiserpermanente.org",
            "bcbs.com",
            # Healthcare systems
            "mayoclinic.org",
            "clevelandclinic.org",
        ],
        "utilities": [
            # Major telecoms
            "verizon.com",
            "att.com",
            "t-mobile.com",
            "sprint.com",
            "comcast.com",
            "xfinity.com",
            "spectrum.com",
            # Energy
            "pge.com",
            "duke-energy.com",
            "coned.com",
        ],
        "education": [
            ".edu",
            # Major universities (examples)
            "stanford.edu",
            "mit.edu",
            "harvard.edu",
        ],
    },

    # ========== INDIA MARKET ==========
    "india": {
        "investment_brokerage": [
            # Indian brokerages (CRITICAL - common false positive source)
            "zerodha.com",
            "groww.in",
            "upstox.com",
            "angelone.in",
            "5paisa.com",
            "icicidirect.com",
            "hdfcsec.com",
            "kotaksecurities.com",
            "sharekhan.com",
            "motilaloswalsec.com",
            "sbismart.com",
            "axisdirect.in",
            "indiainfoline.com",
            "religareonline.com",
        ],
        "banking": [
            # Major Indian banks
            "hdfcbank.com",
            "icicibank.com",
            "sbi.co.in",
            "axisbank.com",
            "kotak.com",
            "yesbank.in",
            "indusind.com",
            "idbibank.in",
            "pnbindia.in",
            "bankofbaroda.in",
            # Digital banks
            "paytm.com",
            "phonepe.com",
            "googlepay.com",
            "amazonpay.in",
        ],
        "government": [
            # Indian government
            ".gov.in",
            ".nic.in",
            "incometaxindia.gov.in",
            "uidai.gov.in",
            "epfindia.gov.in",
            "indianrailways.gov.in",
        ],
        "healthcare": [
            # Health insurance
            "starhealth.in",
            "maxbupa.com",
            "reliancegeneral.co.in",
            "careinsurance.com",
            "apollomunichinsurance.com",
        ],
        "utilities": [
            # Telecoms
            "airtel.in",
            "jio.com",
            "vi.com",
            "bsnl.co.in",
        ],
        "education": [
            ".ac.in",
            ".edu.in",
            # IITs, IIMs, etc.
            "iitb.ac.in",
            "iitd.ac.in",
            "iisc.ac.in",
        ],
    },

    # ========== GERMANY MARKET ==========
    "germany": {
        "investment_brokerage": [
            # German brokers and trading platforms
            "traderepublic.com",
            "scalable.capital",
            "flatex.de",
            "comdirect.de",
            "consorsbank.de",
            "ing.de",
            "dkb.de",
            "onvista.de",
            "lynxbroker.de",
            "captrader.com",
        ],
        "banking": [
            # Major German banks
            "deutsche-bank.de",
            "commerzbank.de",
            "sparkasse.de",
            "postbank.de",
            "volksbank.de",
            "ing.de",
            "dkb.de",
            "n26.com",
            "revolut.com",
            "bunq.com",
        ],
        "government": [
            # German government
            ".gov.de",
            "bund.de",
            "bundesfinanzministerium.de",
            "finanzamt.de",
            "arbeitsagentur.de",
            "rentenversicherung.de",
        ],
        "healthcare": [
            # German health insurance (Krankenkassen)
            "tk.de",
            "aok.de",
            "barmer.de",
            "dak.de",
            "kkh.de",
            "ikk-classic.de",
            "hkk.de",
            "bkk-vbu.de",
        ],
        "utilities": [
            # German telecoms
            "telekom.de",
            "vodafone.de",
            "o2online.de",
            "1und1.de",
            # Energy
            "eon.de",
            "rwe.de",
            "vattenfall.de",
        ],
        "education": [
            ".edu.de",
            # Universities
            "tum.de",
            "lmu.de",
            "fu-berlin.de",
            "rwth-aachen.de",
        ],
    },
}


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

CONFIDENCE_THRESHOLDS = {
    ConfidenceLevel.HIGH: 90,    # ≥90% - Eligible for auto-deletion
    ConfidenceLevel.MEDIUM: 70,  # 70-89% - Flag for human review
    ConfidenceLevel.LOW: 0,      # <70% - Keep
}


# ============================================================================
# RATE LIMITS (API calls per minute)
# ============================================================================

RATE_LIMITS = {
    "gemini": 60,        # Gemini Flash default
    "anthropic": 50,     # Claude tier-dependent
    "gmail_api": 250,    # Gmail API quota per minute
}


# ============================================================================
# BATCH PROCESSING CONFIGURATION
# ============================================================================

BATCH_CONFIG = {
    "classifier_batch_size": 20,   # Emails per AI classification request
    "gmail_fetch_batch_size": 500, # Emails to fetch per Gmail API call (max)
    "max_retries": 3,              # Retry failed API calls
    "retry_delay": 2,              # Seconds between retries
    "retry_backoff": 2,            # Exponential backoff multiplier
}


# ============================================================================
# DELETION SAFETY GATES (ALL MUST PASS)
# ============================================================================

SAFETY_GATES = {
    "gate_1_category": "Category must be PROMOTIONAL",
    "gate_2_verification": "Must pass dual-agent verification",
    "gate_3_confidence": "Confidence must meet threshold (default ≥90%)",
    "gate_4_protected_domain": "Must NOT be from protected domain",
    "gate_5_manual_flags": "Must NOT be starred or marked important",
}


# ============================================================================
# AI PROVIDER CONFIGURATION
# ============================================================================

AI_PROVIDERS = {
    "gemini": {
        "model": "gemini-2.5-flash-lite",
        "temperature": 0.1,  # Low temperature for consistency
        "max_tokens": 4096,
    },
    "anthropic": {
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.1,
        "max_tokens": 4096,
    },
}


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_CONFIG = {
    "log_dir": "logs",
    "results_dir": "classification_results",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_protected_domains(market: Market = Market.ALL) -> Set[str]:
    """
    Get all protected domains for specified market(s).

    Args:
        market: Target market (usa, india, germany, or all)

    Returns:
        Set of all protected domain strings
    """
    domains = set()

    if market == Market.ALL:
        markets = [Market.USA, Market.INDIA, Market.GERMANY]
    else:
        markets = [market]

    for m in markets:
        market_key = m.value
        if market_key in PROTECTED_DOMAINS:
            for category_domains in PROTECTED_DOMAINS[market_key].values():
                domains.update(category_domains)

    return domains


def get_protected_domains_by_category(market: Market, category: str) -> List[str]:
    """
    Get protected domains for specific market and category.

    Args:
        market: Target market
        category: Domain category (e.g., 'investment_brokerage')

    Returns:
        List of protected domains in that category
    """
    market_key = market.value if market != Market.ALL else None

    if market_key and market_key in PROTECTED_DOMAINS:
        return PROTECTED_DOMAINS[market_key].get(category, [])

    return []


def get_confidence_level(confidence_score: float) -> ConfidenceLevel:
    """
    Determine confidence level from numeric score.

    Args:
        confidence_score: Confidence percentage (0-100)

    Returns:
        ConfidenceLevel enum
    """
    if confidence_score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.HIGH]:
        return ConfidenceLevel.HIGH
    elif confidence_score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.MEDIUM]:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration on import"""
    # Ensure all markets have all required categories
    required_categories = [
        "investment_brokerage",
        "banking",
        "government",
        "healthcare",
        "utilities",
        "education",
    ]

    for market in [Market.USA, Market.INDIA, Market.GERMANY]:
        market_key = market.value
        if market_key not in PROTECTED_DOMAINS:
            raise ValueError(f"Missing protected domains for market: {market_key}")

        for category in required_categories:
            if category not in PROTECTED_DOMAINS[market_key]:
                raise ValueError(
                    f"Missing category '{category}' for market '{market_key}'"
                )

            if not PROTECTED_DOMAINS[market_key][category]:
                print(
                    f"WARNING: Empty protected domain list for "
                    f"{market_key}.{category}"
                )


# Run validation on import
validate_config()
