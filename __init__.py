"""
Gmail Promotional Email Classifier Package.

AI-powered dual-agent verification system for classifying and managing promotional emails.
"""

from config import (
    # Gmail API
    GMAIL_SCOPES,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    # Processing
    BATCH_SIZE,
    MAX_BODY_LENGTH,
    # AI Classification
    AI_MODEL,
    AI_MAX_TOKENS,
    CONFIDENCE_THRESHOLD,
    VERIFICATION_THRESHOLD,
    # Rate Limiting
    API_DELAY,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    # Files
    SENDER_CACHE_FILE,
    PROGRESS_FILE,
    SUMMARY_FILE,
    # Patterns and Keywords
    PROMOTIONAL_SENDER_PATTERNS,
    PROMOTIONAL_KEYWORDS_EN,
    PROMOTIONAL_KEYWORDS_DE,
    KEYWORD_THRESHOLD,
)

from keyword_matcher import KeywordMatcher

__all__ = [
    # Config
    'GMAIL_SCOPES',
    'CREDENTIALS_FILE',
    'TOKEN_FILE',
    'BATCH_SIZE',
    'MAX_BODY_LENGTH',
    'AI_MODEL',
    'AI_MAX_TOKENS',
    'CONFIDENCE_THRESHOLD',
    'VERIFICATION_THRESHOLD',
    'API_DELAY',
    'MAX_RETRIES',
    'INITIAL_BACKOFF',
    'SENDER_CACHE_FILE',
    'PROGRESS_FILE',
    'SUMMARY_FILE',
    'PROMOTIONAL_SENDER_PATTERNS',
    'PROMOTIONAL_KEYWORDS_EN',
    'PROMOTIONAL_KEYWORDS_DE',
    'KEYWORD_THRESHOLD',
    # Classes
    'KeywordMatcher',
]
