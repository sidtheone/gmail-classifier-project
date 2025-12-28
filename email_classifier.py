#!/usr/bin/env python3
"""
Enterprise-Grade Gmail Promotional Email Classifier
====================================================
AI-powered dual-agent verification system for classifying and managing promotional emails.

Features:
- OAuth 2.0 Gmail API integration
- Dual-agent AI classification (Claude Haiku)
- Smart sender caching (60-80% cache hit rate)
- Batch processing with progress persistence
- Exponential backoff for rate limiting
- Bilingual support (English/German)

Author: Claude AI Assistant
License: MIT
"""

import os
import sys
import json
import pickle
import base64
import re
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from email.utils import parseaddr
from collections import defaultdict

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# AI APIs
import anthropic
import google.generativeai as genai

# Local imports
import config
from config import (
    GMAIL_SCOPES,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    BATCH_SIZE,
    AI_BATCH_SIZE,
    MAX_BODY_LENGTH,
    AI_PROVIDER,
    ANTHROPIC_MODEL,
    GEMINI_MODEL,
    AI_MAX_TOKENS,
    CONFIDENCE_THRESHOLD,
    VERIFICATION_THRESHOLD,
    API_DELAY,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    RATE_LIMIT_BACKOFF,
    RATE_LIMIT_TPM,
    RATE_LIMIT_RPM,
    RATE_LIMIT_RPD,
    SENDER_CACHE_FILE,
    PROGRESS_FILE,
    SUMMARY_FILE,
    PROMOTIONAL_SENDER_PATTERNS,
    COSTS,
    PROTECTED_DOMAINS,
    PROTECTED_DOMAIN_PATTERNS,
)
from keyword_matcher import KeywordMatcher
from decision_engine import EmailCategory, DecisionEngine, DeletionDecision
from domain_checker import DomainChecker
from gmail_client import GmailService


def debug_log(message: str, data: Any = None) -> None:
    """Print debug message if DEBUG is enabled."""
    if config.DEBUG:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"  [DEBUG {timestamp}] {message}")
        if data is not None:
            if isinstance(data, dict):
                for key, value in data.items():
                    val_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"    {key}: {val_str}")
            else:
                data_str = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                print(f"    {data_str}")


# =============================================================================
# EMAIL PARSING
# =============================================================================

class EmailParser:
    """Utilities for parsing email content."""

    @staticmethod
    def extract_email_address(sender: str) -> str:
        """Extract email address from 'Name <email>' format."""
        _, email = parseaddr(sender)
        return email.lower() if email else sender.lower()

    @staticmethod
    def decode_body(payload: Dict) -> str:
        """Decode email body from base64."""
        body = ""

        if 'body' in payload and payload['body'].get('data'):
            try:
                data = payload['body']['data']
                # Gmail uses URL-safe base64
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            except Exception:
                pass

        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    if part.get('body', {}).get('data'):
                        try:
                            data = part['body']['data']
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
                        except Exception:
                            pass
                elif mime_type.startswith('multipart/'):
                    # Recurse into nested parts
                    nested = EmailParser.decode_body(part)
                    if nested:
                        body = nested
                        break

        return body

    @staticmethod
    def get_email_content(message: Dict) -> Dict[str, str]:
        """Extract subject, sender, and body from message."""
        headers = message.get('payload', {}).get('headers', [])

        subject = ""
        sender = ""

        for header in headers:
            name = header.get('name', '').lower()
            if name == 'subject':
                subject = header.get('value', '')
            elif name == 'from':
                sender = header.get('value', '')

        body = EmailParser.decode_body(message.get('payload', {}))

        # Truncate body
        if len(body) > MAX_BODY_LENGTH:
            body = body[:MAX_BODY_LENGTH] + "..."

        # Clean up body
        body = ' '.join(body.split())  # Normalize whitespace

        return {
            'subject': subject,
            'sender': sender,
            'body': body,
            'email': EmailParser.extract_email_address(sender)
        }


# =============================================================================
# SENDER CACHE
# =============================================================================

class SenderCache:
    """Manages sender classification cache for optimization."""

    def __init__(self, project_dir: str):
        self.cache_path = os.path.join(project_dir, SENDER_CACHE_FILE)
        self.cache = {
            'version': '2.0',
            'senders': {}  # {email: {category: count, ...}}
        }
        self.load()

    def load(self) -> None:
        """Load cache from disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    loaded = json.load(f)
                    # Check version - if old v1 format, start fresh
                    if loaded.get('version') == '2.0':
                        self.cache = loaded
                    else:
                        # Old format detected - purge and start fresh
                        print("  Old cache format detected - starting fresh")
                        os.remove(self.cache_path)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self) -> None:
        """Save cache to disk."""
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def check(self, email: str) -> Optional[EmailCategory]:
        """Check if sender is in cache. Returns EmailCategory or None."""
        email = email.lower()

        # Check promotional patterns first (return PROMOTIONAL category)
        for pattern in PROMOTIONAL_SENDER_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                return EmailCategory.PROMOTIONAL

        # Check cache - return category if ≥80% threshold with 2+ emails
        sender_data = self.cache['senders'].get(email, {})
        total = sum(sender_data.values())

        if total >= 2:  # Need at least 2 emails to trust cache
            for category_str, count in sender_data.items():
                if count >= total * 0.8:
                    try:
                        return EmailCategory(category_str)
                    except ValueError:
                        pass  # Invalid category, continue

        return None

    def update(self, email: str, category: EmailCategory) -> None:
        """Update cache with new classification."""
        email = email.lower()

        if email not in self.cache['senders']:
            self.cache['senders'][email] = {}

        cat_str = category.value if isinstance(category, EmailCategory) else str(category)
        self.cache['senders'][email][cat_str] = self.cache['senders'][email].get(cat_str, 0) + 1


# =============================================================================
# AI CLASSIFICATION
# =============================================================================

class AIClassifier:
    """Dual-agent AI classification system supporting Anthropic and Gemini."""

    CLASSIFIER_PROMPT = """You are an email classifier. Classify this email into ONE of these 5 categories:

1. PROMOTIONAL: Marketing newsletters, sales, discounts, product announcements, social media notifications, automated marketing

2. TRANSACTIONAL: Purchase receipts, shipping confirmations, delivery updates, payment confirmations, order status

3. SYSTEM_SECURITY: Account alerts, password resets, security notifications, login alerts, verification codes, 2FA

4. SOCIAL_PLATFORM: Social network updates, friend requests, mentions, comments (Facebook, LinkedIn, Twitter)

5. PERSONAL_HUMAN: Direct human correspondence, work emails, personal messages, meeting invites from real people

CRITICAL: Investment platforms (banks, brokerages, mutual funds, stock exchanges) are NEVER promotional!
- Examples: Zerodha, Groww, SBIMF, Schwab, Fidelity, Vanguard, ICICI Direct
- These should be classified as TRANSACTIONAL or SYSTEM_SECURITY

Email details:
Subject: {subject}
From: {sender}
Body preview: {body}

Respond ONLY with valid JSON (no markdown):
{{"category": "promotional|transactional|system_security|social_platform|personal_human", "confidence": 0-100, "reason": "brief explanation"}}"""

    VERIFIER_PROMPT = """You are a classification verifier. Review this email classification.

Original classification: {classification}
Confidence: {confidence}%
Reason: {reason}

Email details:
Subject: {subject}
From: {sender}
Body preview: {body}

CRITICAL: Investment platform emails (banks, brokerages, mutual funds) should NEVER be promotional!
- Examples: Zerodha, Groww, SBIMF, Schwab, Fidelity, Vanguard, ICICI Direct, Upstox
- These should be TRANSACTIONAL or SYSTEM_SECURITY, NOT promotional

Common false positives to catch:
- Transaction receipts mistaken for promotions
- Shipping confirmations from retail stores
- Investment platform updates mistaken for promotions (CRITICAL!)
- Account statements from financial services
- Personal emails from business domains

Common false negatives to catch:
- Promotional newsletters with personal greetings
- "You might like" recommendations
- Loyalty program marketing updates
- Social media digest emails

Categories: promotional, transactional, system_security, social_platform, personal_human

Respond ONLY with valid JSON (no markdown):
{{"classification_correct": true/false, "corrected_category": "category if corrected", "confidence": 0-100, "corrected_reason": "explanation if corrected"}}"""

    def __init__(self, api_key: str, provider: str = AI_PROVIDER):
        self.provider = provider
        self.api_key = api_key

        if provider == 'anthropic':
            self.client = anthropic.Anthropic(api_key=api_key)
        elif provider == 'gemini':
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(GEMINI_MODEL)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self.stats = {
            'primary_calls': 0,
            'verification_calls': 0,
            'corrections': 0,
            'cache_hits': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'rate_limit_hits': 0
        }
        self.last_call_time = 0

        # Rate limiting tracking
        self.minute_start_time = time.time()
        self.tokens_this_minute = 0
        self.requests_this_minute = 0
        self.requests_today = 0
        self.day_start_time = time.time()

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        current_time = time.time()

        # Reset daily counter if a day has passed
        if current_time - self.day_start_time >= 86400:  # 24 hours
            self.requests_today = 0
            self.day_start_time = current_time
            debug_log("Rate limit: Daily counter reset")

        # Reset minute counters if a minute has passed
        if current_time - self.minute_start_time >= 60:
            self.tokens_this_minute = 0
            self.requests_this_minute = 0
            self.minute_start_time = current_time
            debug_log("Rate limit: Minute counter reset")

        # Check daily limit (RPD)
        if self.requests_today >= RATE_LIMIT_RPD:
            wait_time = 86400 - (current_time - self.day_start_time)
            print(f"\n  Daily request limit reached ({RATE_LIMIT_RPD}). Waiting {wait_time/3600:.1f} hours...")
            time.sleep(wait_time)
            self.requests_today = 0
            self.day_start_time = time.time()
            self.tokens_this_minute = 0
            self.requests_this_minute = 0
            self.minute_start_time = time.time()

        # Check requests per minute (RPM)
        if self.requests_this_minute >= RATE_LIMIT_RPM:
            wait_time = 60 - (current_time - self.minute_start_time)
            if wait_time > 0:
                debug_log(f"Rate limit: RPM limit hit, waiting {wait_time:.1f}s")
                print(f"\n  RPM limit reached ({RATE_LIMIT_RPM}/min). Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.tokens_this_minute = 0
                self.requests_this_minute = 0
                self.minute_start_time = time.time()

        # Check tokens per minute (TPM)
        if self.tokens_this_minute >= RATE_LIMIT_TPM:
            wait_time = 60 - (current_time - self.minute_start_time)
            if wait_time > 0:
                debug_log(f"Rate limit: TPM limit hit ({self.tokens_this_minute}/{RATE_LIMIT_TPM}), waiting {wait_time:.1f}s")
                print(f"\n  TPM limit reached ({self.tokens_this_minute}/{RATE_LIMIT_TPM}). Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.tokens_this_minute = 0
                self.requests_this_minute = 0
                self.minute_start_time = time.time()

        # Enforce minimum delay between calls
        elapsed = time.time() - self.last_call_time
        if elapsed < API_DELAY:
            time.sleep(API_DELAY - elapsed)

        self.last_call_time = time.time()

    def _call_anthropic(self, prompt: str, retries: int = 0) -> Optional[Dict]:
        """Make Anthropic API call."""
        debug_log(f"Anthropic API: Calling {ANTHROPIC_MODEL}", {
            "retry": retries,
            "prompt_length": len(prompt)
        })
        try:
            response = self.client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=AI_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )
            self.stats['input_tokens'] += response.usage.input_tokens
            self.stats['output_tokens'] += response.usage.output_tokens
            result = response.content[0].text.strip()
            debug_log(f"Anthropic API: Success", {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "response": result[:100]
            })
            return result

        except anthropic.RateLimitError as e:
            debug_log(f"Anthropic API: Rate limit error", {
                "error": str(e),
                "retry": retries
            })
            if retries < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retries)
                print(f"\n  Rate limited, waiting {backoff:.1f}s...")
                time.sleep(backoff)
                return self._call_anthropic(prompt, retries + 1)
            raise
        except Exception as e:
            debug_log(f"Anthropic API: Error", {
                "error_type": type(e).__name__,
                "error": str(e),
                "retry": retries
            })
            raise

    def _call_gemini(self, prompt: str, retries: int = 0) -> Optional[str]:
        """Make Gemini API call."""
        debug_log(f"Gemini API: Calling {GEMINI_MODEL}", {
            "retry": retries,
            "prompt_length": len(prompt)
        })
        try:
            # Increment request counters before call
            self.requests_this_minute += 1
            self.requests_today += 1

            response = self.client.generate_content(prompt)

            # Track tokens (Gemini doesn't always return exact counts)
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            else:
                # Rough estimate: 4 chars per token
                input_tokens = len(prompt) // 4
                output_tokens = len(response.text) // 4

            # Update stats
            self.stats['input_tokens'] += input_tokens
            self.stats['output_tokens'] += output_tokens

            # Update TPM counter
            total_tokens = input_tokens + output_tokens
            self.tokens_this_minute += total_tokens

            result = response.text.strip()
            debug_log(f"Gemini API: Success", {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tokens_this_minute": self.tokens_this_minute,
                "requests_this_minute": self.requests_this_minute,
                "response": result[:100]
            })
            return result

        except Exception as e:
            error_str = str(e)
            debug_log(f"Gemini API: Error", {
                "error_type": type(e).__name__,
                "error": error_str[:200],
                "retry": retries
            })
            if 'quota' in error_str.lower() or 'rate' in error_str.lower() or '429' in error_str:
                self.stats['rate_limit_hits'] += 1
                if retries < MAX_RETRIES:
                    print(f"\n  ⚠️  Rate limited! Waiting {RATE_LIMIT_BACKOFF:.0f}s before retry {retries + 1}/{MAX_RETRIES}...")
                    time.sleep(RATE_LIMIT_BACKOFF)
                    # Reset counters after wait
                    self.tokens_this_minute = 0
                    self.requests_this_minute = 0
                    self.minute_start_time = time.time()
                    return self._call_gemini(prompt, retries + 1)
            raise

    def _call_api(self, prompt: str, retries: int = 0) -> Optional[Dict]:
        """Make API call with exponential backoff."""
        self._rate_limit()
        debug_log(f"AI API: Starting call", {"provider": self.provider})

        try:
            if self.provider == 'anthropic':
                content = self._call_anthropic(prompt, retries)
            else:
                content = self._call_gemini(prompt, retries)

            if content is None:
                debug_log("AI API: Received None response")
                return None

            # Handle potential markdown wrapping
            if content.startswith('```'):
                debug_log("AI API: Stripping markdown wrapper")
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

            result = json.loads(content)
            debug_log(f"AI API: Parsed JSON successfully", result)
            return result

        except json.JSONDecodeError as e:
            debug_log(f"AI API: JSON parse error", {
                "error": str(e),
                "content": content[:200] if content else "None"
            })
            print(f"\n  JSON parse error: {e}")
            return None
        except Exception as e:
            debug_log(f"AI API: Exception", {
                "error_type": type(e).__name__,
                "error": str(e)[:200],
                "retry": retries
            })
            if retries < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retries)
                debug_log(f"AI API: Retrying after {backoff}s")
                time.sleep(backoff)
                return self._call_api(prompt, retries + 1)
            raise

    def classify(self, email_content: Dict) -> Dict:
        """Primary classification using Agent 1."""
        self.stats['primary_calls'] += 1

        prompt = self.CLASSIFIER_PROMPT.format(
            subject=email_content['subject'][:200],
            sender=email_content['sender'][:100],
            body=email_content['body']
        )

        result = self._call_api(prompt)

        if result is None:
            return {
                'category': EmailCategory.PERSONAL_HUMAN,  # Safe default
                'confidence': 0,
                'reason': 'Classification failed',
                'verified': False
            }

        # Convert string category to enum
        category_str = result.get('category', 'personal_human')
        try:
            category = EmailCategory(category_str)
        except ValueError:
            category = EmailCategory.PERSONAL_HUMAN  # Safe default

        return {
            'category': category,
            'confidence': result.get('confidence', 50),
            'reason': result.get('reason', 'Unknown'),
            'verified': False
        }

    def verify(self, email_content: Dict, classification: Dict) -> Dict:
        """Secondary verification using Agent 2."""
        self.stats['verification_calls'] += 1

        # Get category as string for prompt
        category = classification.get('category')
        if isinstance(category, EmailCategory):
            category_str = category.value
        else:
            category_str = str(category)

        prompt = self.VERIFIER_PROMPT.format(
            classification=category_str,
            confidence=classification['confidence'],
            reason=classification['reason'],
            subject=email_content['subject'][:200],
            sender=email_content['sender'][:100],
            body=email_content['body']
        )

        result = self._call_api(prompt)

        if result is None:
            classification['verified'] = True
            return classification

        if not result.get('classification_correct', True):
            self.stats['corrections'] += 1

            # Get corrected category
            corrected_cat_str = result.get('corrected_category', category_str)
            try:
                corrected_category = EmailCategory(corrected_cat_str)
            except ValueError:
                corrected_category = classification['category']  # Keep original if invalid

            return {
                'category': corrected_category,
                'confidence': result.get('confidence', classification['confidence']),
                'reason': result.get('corrected_reason', classification['reason']),
                'verified': True,
                'corrected': True
            }

        classification['verified'] = True
        classification['verification_confidence'] = result.get('confidence', 100)
        return classification

    def classify_with_verification(self, email_content: Dict,
                                   verify_low_confidence: bool = True) -> Dict:
        """Full classification pipeline with optional verification."""
        result = self.classify(email_content)

        # Verify if confidence is below threshold
        if verify_low_confidence and result['confidence'] < VERIFICATION_THRESHOLD:
            result = self.verify(email_content, result)

        return result

    def batch_classify(self, email_list: List[Dict]) -> List[Dict]:
        """
        Batch classification - classify multiple emails in a single API call.

        Args:
            email_list: List of email content dicts with keys: subject, sender, body, msg_id

        Returns:
            List of classification dicts matching the order of input emails
        """
        if not email_list:
            return []

        self.stats['primary_calls'] += 1  # Count as one API call

        # Build compact batch prompt
        batch_prompt = """You are an email classifier. Classify these emails into categories.

Categories: promotional, transactional, system_security, social_platform, personal_human

CRITICAL: Investment platforms (banks, brokerages, mutual funds) are NEVER promotional!

Emails to classify:
"""

        for idx, email in enumerate(email_list):
            batch_prompt += f"""
{idx}. Subject: {email['subject'][:150]}
   From: {email['sender'][:80]}
   Preview: {email['body'][:200]}
"""

        batch_prompt += """
Respond with ONLY a JSON array (no markdown) where each object has:
{"idx": number, "cat": "category", "c": 0-100 (confidence)}

Example: [{"idx":0,"cat":"promotional","c":85},{"idx":1,"cat":"transactional","c":90}]"""

        result = self._call_api(batch_prompt)

        if result is None or not isinstance(result, list):
            # Fallback: mark all as personal_human (safe default) with low confidence
            debug_log("Batch classification failed, using fallback")
            return [{
                'category': EmailCategory.PERSONAL_HUMAN,
                'confidence': 0,
                'reason': 'Batch classification failed',
                'verified': False
            } for _ in email_list]

        # Convert compact format to full format
        classifications = []
        for item in result:
            idx = item.get('idx', 0)
            category_str = item.get('cat', 'personal_human')

            # Convert string to enum
            try:
                category = EmailCategory(category_str)
            except ValueError:
                category = EmailCategory.PERSONAL_HUMAN  # Safe default

            classifications.append({
                'category': category,
                'confidence': item.get('c', 50),
                'reason': f'Batch classified (#{idx})',
                'verified': False
            })

        debug_log(f"Batch classified {len(classifications)} emails")
        return classifications

    def batch_verify(self, email_list: List[Dict], classifications: List[Dict]) -> List[Dict]:
        """
        Batch verification - verify multiple classifications in a single API call.

        Args:
            email_list: List of email content dicts
            classifications: List of classification results to verify

        Returns:
            List of verified/corrected classification dicts
        """
        if not email_list or not classifications:
            return classifications

        self.stats['verification_calls'] += 1

        # Build compact batch verification prompt
        batch_prompt = """You are a classification verifier. Review these email classifications and correct any errors.

CRITICAL: Investment platforms (banks, brokerages, mutual funds) should NEVER be promotional!

Common errors to catch:
- Investment platform updates mistaken for promotions (CRITICAL!)
- Receipts/shipping confirmations mistaken for promotions
- Newsletter-style promotional content marked incorrectly

Classifications to verify:
"""

        for idx, (email, cls) in enumerate(zip(email_list, classifications)):
            category = cls.get('category')
            if isinstance(category, EmailCategory):
                cat_str = category.value
            else:
                cat_str = str(category)

            batch_prompt += f"""
{idx}. [{cat_str.upper()}] Conf:{cls['confidence']}% - {email['sender'][:60]}
   "{email['subject'][:100]}"
"""

        batch_prompt += """
Respond with ONLY a JSON array (no markdown) for emails that need correction:
[{"idx": number, "cat": "corrected_category", "c": 0-100}]

Categories: promotional, transactional, system_security, social_platform, personal_human

If no corrections needed, return empty array: []"""

        result = self._call_api(batch_prompt)

        if result is None:
            # No corrections, mark all as verified
            for cls in classifications:
                cls['verified'] = True
            return classifications

        # Apply corrections
        corrected_indices = set()
        if isinstance(result, list):
            for correction in result:
                idx = correction.get('idx', -1)
                if 0 <= idx < len(classifications):
                    corrected_indices.add(idx)
                    self.stats['corrections'] += 1

                    # Parse corrected category
                    cat_str = correction.get('cat', 'personal_human')
                    try:
                        corrected_category = EmailCategory(cat_str)
                    except ValueError:
                        corrected_category = classifications[idx].get('category', EmailCategory.PERSONAL_HUMAN)

                    classifications[idx] = {
                        'category': corrected_category,
                        'confidence': correction.get('c', classifications[idx]['confidence']),
                        'reason': f'Batch corrected (#{idx})',
                        'verified': True,
                        'corrected': True
                    }

        # Mark non-corrected as verified
        for idx, cls in enumerate(classifications):
            if idx not in corrected_indices:
                cls['verified'] = True

        debug_log(f"Batch verified {len(classifications)} emails, corrected {len(corrected_indices)}")
        return classifications


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

class ProgressTracker:
    """Tracks and persists classification progress."""

    def __init__(self, project_dir: str):
        self.progress_path = os.path.join(project_dir, PROGRESS_FILE)
        self.summary_path = os.path.join(project_dir, SUMMARY_FILE)
        self.progress = {
            'version': '2.0',
            'processed_ids': [],
            'page_token': None,
            'emails': [],  # List of all emails with category, subject, sender, confidence
            'category_counts': {
                'promotional': 0,
                'transactional': 0,
                'system_security': 0,
                'social_platform': 0,
                'personal_human': 0
            },
            'started_at': None,
            'last_updated': None,
            'batches_completed': 0
        }
        self.load()

    def load(self) -> bool:
        """Load progress from disk. Returns True if resuming."""
        if os.path.exists(self.progress_path):
            try:
                with open(self.progress_path, 'r') as f:
                    saved = json.load(f)
                    # Check version - if old v1 format, start fresh
                    if saved.get('version') == '2.0':
                        self.progress.update(saved)
                        return bool(saved.get('processed_ids'))
                    else:
                        # Old format detected - purge and start fresh
                        print("  Old progress format detected - starting fresh")
                        os.remove(self.progress_path)
                        return False
            except (json.JSONDecodeError, IOError):
                pass
        return False

    def save(self) -> None:
        """Save progress to disk."""
        self.progress['last_updated'] = datetime.now().isoformat()
        with open(self.progress_path, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def is_processed(self, msg_id: str) -> bool:
        """Check if message was already processed."""
        return msg_id in self.progress['processed_ids']

    def add_result(self, msg_id: str, email_content: Dict,
                   classification: Dict) -> None:
        """Record classification result."""
        self.progress['processed_ids'].append(msg_id)

        # Get category
        category = classification.get('category')
        if isinstance(category, EmailCategory):
            cat_str = category.value
        else:
            cat_str = str(category) if category else 'personal_human'

        # Add to emails list
        self.progress['emails'].append({
            'id': msg_id,
            'category': cat_str,
            'subject': email_content['subject'][:100],
            'sender': email_content['sender'],
            'email': email_content['email'],
            'confidence': classification['confidence'],
            'verified': classification.get('verified', False),
            'corrected': classification.get('corrected', False)
        })

        # Update category counts
        if cat_str in self.progress['category_counts']:
            self.progress['category_counts'][cat_str] += 1

    def update_page_token(self, token: Optional[str]) -> None:
        """Update pagination token."""
        self.progress['page_token'] = token

    def complete_batch(self) -> None:
        """Mark batch as complete and save."""
        self.progress['batches_completed'] += 1
        self.save()

    def get_summary(self) -> Dict:
        """Generate sender summary from all emails."""
        sender_groups = defaultdict(list)

        # Group promotional emails by sender for detailed summary
        promotional_emails = [e for e in self.progress['emails']
                            if e.get('category') == 'promotional']

        for email in promotional_emails:
            sender_groups[email['email']].append(email)

        summary = {
            'total_processed': len(self.progress['processed_ids']),
            'category_counts': self.progress['category_counts'].copy(),
            'promotional_senders': {}
        }

        # Build sender details for promotional senders
        for sender, emails in sorted(sender_groups.items(),
                                     key=lambda x: -len(x[1])):
            summary['promotional_senders'][sender] = {
                'count': len(emails),
                'emails': [e['id'] for e in emails],
                'avg_confidence': sum(e['confidence'] for e in emails) / len(emails),
                'sample_subjects': [e['subject'] for e in emails[:3]]
            }

        return summary

    def save_summary(self) -> None:
        """Save final summary to disk."""
        summary = self.get_summary()
        with open(self.summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

    def reset(self) -> None:
        """Clear all progress."""
        self.progress = {
            'processed_ids': [],
            'page_token': None,
            'promotional_emails': [],
            'non_promotional_count': 0,
            'started_at': datetime.now().isoformat(),
            'last_updated': None,
            'batches_completed': 0
        }
        if os.path.exists(self.progress_path):
            os.remove(self.progress_path)


# =============================================================================
# MAIN CLASSIFIER
# =============================================================================

class GmailClassifier:
    """Main orchestrator for the email classification system."""

    def __init__(self, project_dir: str, api_key: str, provider: str = AI_PROVIDER):
        self.project_dir = project_dir
        self.provider = provider
        self.gmail = GmailService(project_dir)
        self.cache = SenderCache(project_dir)
        self.domain_checker = DomainChecker()
        self.keyword_matcher = KeywordMatcher()
        self.classifier = AIClassifier(api_key, provider)
        self.progress = ProgressTracker(project_dir)

    def initialize(self) -> bool:
        """Initialize Gmail service."""
        print("\n[1/4] Authenticating with Gmail API...")
        if not self.gmail.authenticate():
            return False
        print("  Gmail authentication successful")
        return True

    def process_inbox(self, max_total: Optional[int] = None,
                      use_cache: bool = True,
                      verify_low_confidence: bool = True) -> Dict:
        """Main processing loop for inbox classification."""

        # Check for resume
        if self.progress.load():
            print(f"\n  Resuming from previous session...")
            print(f"  Already processed: {len(self.progress.progress['processed_ids'])} emails")
            print(f"  Promotional found: {len(self.progress.progress['promotional_emails'])}")
        else:
            self.progress.progress['started_at'] = datetime.now().isoformat()

        print("\n[2/4] Processing inbox...")
        print("  Legend: 🛡️=protected 🔍=verified ✏️=corrected ✓=promo ✗=not-promo")
        print("  Note: Cache disabled - classifying each email fresh for audit")
        print()

        page_token = self.progress.progress.get('page_token')
        processed = 0
        batch_num = self.progress.progress.get('batches_completed', 0)

        start_time = time.time()

        try:
            while True:
                # Check limit
                if max_total and processed >= max_total:
                    print(f"\n  Reached limit of {max_total} emails")
                    break

                # Fetch batch
                batch_num += 1
                messages, next_token = self.gmail.get_messages(page_token)

                if not messages:
                    print("\n  No more messages to process")
                    break

                print(f"\n  Batch {batch_num}: ", end="", flush=True)

                batch_processed = 0

                # Phase 1: Collect and pre-filter emails
                emails_to_classify = []
                email_metadata = []  # Track msg_id and email_content for each

                for msg in messages:
                    msg_id = msg['id']

                    # Skip if already processed
                    if self.progress.is_processed(msg_id):
                        continue

                    # Get email details
                    details = self.gmail.get_message_details(msg_id)
                    if not details:
                        continue

                    email_content = EmailParser.get_email_content(details)

                    debug_log(f"Processing email", {
                        "msg_id": msg_id,
                        "from": email_content['email'],
                        "subject": email_content['subject'][:50]
                    })

                    # Check protected domains FIRST
                    is_protected, protection_reason = self.domain_checker.is_protected(
                        email_content['email']
                    )

                    if is_protected:
                        classification = {
                            'category': EmailCategory.PERSONAL_HUMAN,  # Protected domains classified as safe
                            'confidence': 100,
                            'reason': protection_reason,
                            'verified': True,
                            'protected': True
                        }
                        print("🛡️", end="", flush=True)
                        self.progress.add_result(msg_id, email_content, classification)
                        batch_processed += 1
                        processed += 1
                        if max_total and processed >= max_total:
                            break
                        continue

                    # Cache disabled - classify each email fresh for audit
                    # (User request: "Don't use cache, classify each email")
                    # Skip cache check entirely

                    # Keywords disabled - classify each email with AI for consistent audit
                    # (User request: "classify each email")
                    # Skip keyword matching

                    # Need AI classification - add to batch
                    emails_to_classify.append({
                        'subject': email_content['subject'],
                        'sender': email_content['sender'],
                        'body': email_content['body'],
                        'msg_id': msg_id
                    })
                    email_metadata.append((msg_id, email_content))

                # Phase 2: Batch classify remaining emails
                if emails_to_classify:
                    debug_log(f"Batch classifying {len(emails_to_classify)} emails")

                    # Process in sub-batches of AI_BATCH_SIZE
                    for i in range(0, len(emails_to_classify), AI_BATCH_SIZE):
                        sub_batch = emails_to_classify[i:i + AI_BATCH_SIZE]
                        sub_metadata = email_metadata[i:i + AI_BATCH_SIZE]

                        # Batch classify
                        classifications = self.classifier.batch_classify(sub_batch)

                        # CRITICAL: ALWAYS verify promotional emails (safety-first)
                        # Also verify low-confidence classifications for other categories
                        verify_indices = []
                        for idx, cls in enumerate(classifications):
                            # ALWAYS verify promotional (regardless of confidence)
                            if cls.get('category') == EmailCategory.PROMOTIONAL:
                                verify_indices.append(idx)
                            # Verify other categories if low confidence
                            elif verify_low_confidence and cls['confidence'] < VERIFICATION_THRESHOLD:
                                verify_indices.append(idx)

                        if verify_indices:
                            verify_emails = [sub_batch[idx] for idx in verify_indices]
                            verify_cls = [classifications[idx] for idx in verify_indices]

                            verified_cls = self.classifier.batch_verify(verify_emails, verify_cls)

                            # Update classifications with verified results
                            for idx, verified in zip(verify_indices, verified_cls):
                                classifications[idx] = verified

                        # Record results
                        for (msg_id, email_content), classification in zip(sub_metadata, classifications):
                            # Cache disabled - but still save for audit trail
                            self.cache.update(email_content['email'],
                                            classification['category'])

                            # Print indicator
                            category = classification.get('category')
                            if classification.get('corrected'):
                                print("✏️", end="", flush=True)
                            elif classification.get('verified'):
                                print("🔍", end="", flush=True)
                            elif category == EmailCategory.PROMOTIONAL:
                                print("✓", end="", flush=True)
                            else:
                                print("✗", end="", flush=True)

                            # Record result
                            self.progress.add_result(msg_id, email_content, classification)
                            batch_processed += 1
                            processed += 1

                            if max_total and processed >= max_total:
                                break

                        if max_total and processed >= max_total:
                            break

                # Save progress after each batch
                self.progress.update_page_token(next_token)
                self.progress.complete_batch()
                self.cache.save()

                # Print batch stats
                promo_count = self.progress.progress['category_counts']['promotional']
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                print(f" [{batch_processed}] Total: {processed} | Promo: {promo_count} | "
                      f"{rate:.1f} emails/sec")

                if not next_token:
                    print("\n  Reached end of inbox")
                    break

                page_token = next_token

        except KeyboardInterrupt:
            print("\n\n  Interrupted! Progress saved.")
            self.progress.save()
            self.cache.save()

        # Generate and save summary
        print("\n[3/4] Generating summary...")
        self.progress.save_summary()

        return self._compile_results()

    def _compile_results(self) -> Dict:
        """Compile final results and statistics."""
        summary = self.progress.get_summary()

        results = {
            'summary': summary,
            'ai_stats': self.classifier.stats,
            'domain_stats': self.domain_checker.stats,
            'estimated_cost': self._estimate_cost()
        }

        return results

    def _estimate_cost(self) -> Dict:
        """Estimate API costs based on token usage."""
        cost_rates = COSTS.get(self.provider, COSTS['gemini'])

        input_cost = (self.classifier.stats['input_tokens'] / 1_000_000) * cost_rates['input']
        output_cost = (self.classifier.stats['output_tokens'] / 1_000_000) * cost_rates['output']

        return {
            'provider': self.provider,
            'input_tokens': self.classifier.stats['input_tokens'],
            'output_tokens': self.classifier.stats['output_tokens'],
            'input_cost': f"${input_cost:.4f}",
            'output_cost': f"${output_cost:.4f}",
            'total_cost': f"${input_cost + output_cost:.4f}"
        }

    def delete_promotional(self, dry_run: bool = True) -> Dict:
        """Delete promotional emails after user confirmation."""
        # Filter promotional emails
        promo_emails = [e for e in self.progress.progress['emails']
                       if e.get('category') == 'promotional']

        if not promo_emails:
            print("  No promotional emails to delete")
            return {'deleted': 0}

        # Group by sender for display
        sender_groups = defaultdict(list)
        for email in promo_emails:
            sender_groups[email['email']].append(email)

        print(f"\n[4/4] Promotional emails by sender:")
        print("-" * 60)

        for sender, emails in sorted(sender_groups.items(),
                                     key=lambda x: -len(x[1]))[:20]:
            avg_conf = sum(e['confidence'] for e in emails) / len(emails)
            print(f"  {sender}: {len(emails)} emails (avg {avg_conf:.0f}% confidence)")

        if len(sender_groups) > 20:
            print(f"  ... and {len(sender_groups) - 20} more senders")

        print("-" * 60)
        print(f"\nTotal: {len(promo_emails)} promotional emails to delete")

        if dry_run:
            print("\n[DRY RUN] No emails deleted. Use --delete to actually delete.")
            return {'deleted': 0, 'dry_run': True}

        # Confirm deletion
        print("\nAre you sure you want to move these emails to trash?")
        confirm = input("Type 'yes' to confirm: ").strip().lower()

        if confirm != 'yes':
            print("Deletion cancelled.")
            return {'deleted': 0, 'cancelled': True}

        print("\nDeleting promotional emails...")
        message_ids = [e['id'] for e in promo_emails]
        deleted = self.gmail.trash_messages(message_ids)

        print(f"  Moved {deleted}/{len(message_ids)} emails to trash")
        return {'deleted': deleted, 'total': len(message_ids)}


# =============================================================================
# CLI INTERFACE
# =============================================================================

def print_header():
    """Print application header."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Gmail Promotional Email Classifier                       ║
║     AI-Powered Dual-Agent Verification System                ║
╚══════════════════════════════════════════════════════════════╝
""")


def print_results(results: Dict):
    """Print classification results."""
    summary = results['summary']
    stats = results['ai_stats']
    domain_stats = results.get('domain_stats', {})
    cost = results['estimated_cost']

    print("\n" + "=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)

    print(f"\nEmails Processed: {summary['total_processed']}")
    print(f"\nEmails by Category:")
    category_counts = summary.get('category_counts', {})
    print(f"  Promotional:      {category_counts.get('promotional', 0)}")
    print(f"  Transactional:    {category_counts.get('transactional', 0)}")
    print(f"  System/Security:  {category_counts.get('system_security', 0)}")
    print(f"  Social/Platform:  {category_counts.get('social_platform', 0)}")
    print(f"  Personal/Human:   {category_counts.get('personal_human', 0)}")

    print(f"\nClassification Statistics:")
    print(f"  Protected Domains:      {domain_stats.get('protected_hits', 0)}")
    print(f"  AI Classifications:     {stats['primary_calls']}")
    print(f"  AI Verifications:       {stats['verification_calls']}")
    print(f"  AI Corrections:         {stats['corrections']}")

    if stats['verification_calls'] > 0:
        correction_rate = (stats['corrections'] /
                          stats['verification_calls']) * 100
        print(f"  Correction Rate:        {correction_rate:.1f}%")

    print(f"\nToken Usage ({cost.get('provider', 'unknown').title()}):")
    print(f"  Input:  {cost['input_tokens']:,} tokens ({cost['input_cost']})")
    print(f"  Output: {cost['output_tokens']:,} tokens ({cost['output_cost']})")
    print(f"  Total Cost: {cost['total_cost']}")

    # Rate limit info
    if stats.get('rate_limit_hits', 0) > 0:
        print(f"\nRate Limiting:")
        print(f"  Rate Limit Hits: {stats['rate_limit_hits']} (waited 60s each)")
        print(f"  Total Wait Time: ~{stats['rate_limit_hits'] * 60 / 60:.1f} minutes")

    # Top senders
    if summary.get('promotional_senders'):
        print(f"\nTop 10 Promotional Senders:")
        for i, (sender, data) in enumerate(list(summary['promotional_senders'].items())[:10]):
            print(f"  {i+1:2}. {sender}: {data['count']} emails "
                  f"({data['avg_confidence']:.0f}% avg confidence)")

    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Gmail Promotional Email Classifier with AI-powered verification'
    )
    parser.add_argument('--project-dir', '-d',
                        default='/Users/sidhartharora/dev/claude/email/gmail-classifier-project',
                        help='Project directory containing credentials')
    parser.add_argument('--provider', '-p',
                        choices=['gemini', 'anthropic'],
                        default=AI_PROVIDER,
                        help=f'AI provider (default: {AI_PROVIDER})')
    parser.add_argument('--api-key', '-k',
                        help='API key (or set GEMINI_API_KEY/ANTHROPIC_API_KEY env var)')
    parser.add_argument('--max-emails', '-m', type=int, default=None,
                        help='Maximum emails to process (default: all)')
    parser.add_argument('--no-cache', action='store_true',
                        help='Disable sender caching')
    parser.add_argument('--no-verify', action='store_true',
                        help='Disable secondary verification')
    parser.add_argument('--delete', action='store_true',
                        help='Delete promotional emails after classification')
    parser.add_argument('--reset', action='store_true',
                        help='Reset progress and start fresh')
    parser.add_argument('--summary-only', action='store_true',
                        help='Only show summary of previous run')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging (shows API calls and results)')

    args = parser.parse_args()

    # Enable debug mode
    if args.debug:
        config.DEBUG = True
        print("\n[DEBUG MODE ENABLED]")

    print_header()

    # Get API key based on provider
    if args.api_key:
        api_key = args.api_key
    elif args.provider == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    else:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        env_var = 'GEMINI_API_KEY' if args.provider == 'gemini' else 'ANTHROPIC_API_KEY'
        print(f"ERROR: {args.provider.title()} API key required!")
        print(f"Set {env_var} environment variable or use --api-key flag")
        sys.exit(1)

    print(f"  Using provider: {args.provider}")

    # Initialize classifier
    classifier = GmailClassifier(args.project_dir, api_key, args.provider)

    # Handle reset
    if args.reset:
        print("Resetting progress...")
        classifier.progress.reset()
        print("Progress cleared.")

    # Summary only mode
    if args.summary_only:
        if classifier.progress.load():
            print_results(classifier._compile_results())
        else:
            print("No previous results found.")
        sys.exit(0)

    # Initialize Gmail
    if not classifier.initialize():
        sys.exit(1)

    # Process inbox
    results = classifier.process_inbox(
        max_total=args.max_emails,
        use_cache=not args.no_cache,
        verify_low_confidence=not args.no_verify
    )

    # Print results
    print_results(results)

    # Handle deletion
    if args.delete:
        classifier.delete_promotional(dry_run=False)
    else:
        classifier.delete_promotional(dry_run=True)

    print("\nDone!")


if __name__ == '__main__':
    main()
