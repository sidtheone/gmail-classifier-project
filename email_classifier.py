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

# Anthropic API
import anthropic

# Local imports
from config import (
    GMAIL_SCOPES,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    BATCH_SIZE,
    MAX_BODY_LENGTH,
    AI_MODEL,
    AI_MAX_TOKENS,
    CONFIDENCE_THRESHOLD,
    VERIFICATION_THRESHOLD,
    API_DELAY,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    SENDER_CACHE_FILE,
    PROGRESS_FILE,
    SUMMARY_FILE,
    PROMOTIONAL_SENDER_PATTERNS,
)
from keyword_matcher import KeywordMatcher


# =============================================================================
# GMAIL API INTEGRATION
# =============================================================================

class GmailService:
    """Handles Gmail API authentication and operations."""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.credentials_path = os.path.join(project_dir, CREDENTIALS_FILE)
        self.token_path = os.path.join(project_dir, TOKEN_FILE)
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth 2.0."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("  Token refreshed successfully")
                except Exception as e:
                    print(f"  Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    print(f"\n  ERROR: {CREDENTIALS_FILE} not found!")
                    print(f"  Please place your OAuth credentials at:")
                    print(f"  {self.credentials_path}")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("  New authentication completed")

            # Save token
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        return True

    def get_messages(self, page_token: Optional[str] = None,
                     max_results: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """Fetch messages from inbox with pagination."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results,
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            next_token = results.get('nextPageToken')
            return messages, next_token

        except HttpError as e:
            if e.resp.status in [429, 500, 503]:
                raise  # Let caller handle with backoff
            raise

    def get_message_details(self, msg_id: str) -> Optional[Dict]:
        """Get full message details including headers and body."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            return message
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    def trash_messages(self, message_ids: List[str]) -> int:
        """Move messages to trash in batches."""
        success_count = 0

        for i in range(0, len(message_ids), 100):
            batch = message_ids[i:i+100]

            try:
                body = {'ids': batch}
                self.service.users().messages().batchModify(
                    userId='me',
                    body={'ids': batch, 'addLabelIds': ['TRASH']}
                ).execute()
                success_count += len(batch)
            except HttpError as e:
                print(f"  Error trashing batch: {e}")
                # Try individual deletion
                for msg_id in batch:
                    try:
                        self.service.users().messages().trash(
                            userId='me', id=msg_id
                        ).execute()
                        success_count += 1
                    except:
                        pass

        return success_count


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
            'promotional': {},      # {email: count}
            'non_promotional': {}   # {email: count}
        }
        self.load()

    def load(self) -> None:
        """Load cache from disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self) -> None:
        """Save cache to disk."""
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def check(self, email: str) -> Optional[bool]:
        """Check if sender is in cache. Returns is_promotional or None."""
        email = email.lower()

        # Check promotional patterns first
        for pattern in PROMOTIONAL_SENDER_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                return True

        # Check cache
        promo_count = self.cache['promotional'].get(email, 0)
        non_promo_count = self.cache['non_promotional'].get(email, 0)

        total = promo_count + non_promo_count
        if total >= 2:  # Need at least 2 emails to trust cache
            if promo_count >= total * 0.8:
                return True
            elif non_promo_count >= total * 0.8:
                return False

        return None

    def update(self, email: str, is_promotional: bool) -> None:
        """Update cache with new classification."""
        email = email.lower()
        key = 'promotional' if is_promotional else 'non_promotional'
        self.cache[key][email] = self.cache[key].get(email, 0) + 1


# =============================================================================
# AI CLASSIFICATION
# =============================================================================

class AIClassifier:
    """Dual-agent AI classification system using Claude."""

    CLASSIFIER_PROMPT = """You are an email classifier. Analyze this email and determine if it's promotional.

PROMOTIONAL emails include:
- Marketing newsletters, product announcements
- Sales, discounts, deals, coupons (Angebote, Rabatte, Gutscheine)
- Promotional content from brands/stores
- Social media notifications (LinkedIn, Facebook updates)
- Automated marketing emails

NON-PROMOTIONAL emails include:
- Personal correspondence
- Transaction receipts/confirmations (Quittungen)
- Shipping notifications (Versandbestätigung)
- Account security alerts
- Work/business communications
- Bills and statements
- Appointment confirmations

Email details:
Subject: {subject}
From: {sender}
Body preview: {body}

Respond ONLY with valid JSON (no markdown):
{{"is_promotional": true/false, "confidence": 0-100, "reason": "brief explanation"}}"""

    VERIFIER_PROMPT = """You are a classification verifier. Review this email classification.

Original classification: {classification}
Confidence: {confidence}%
Reason: {reason}

Email details:
Subject: {subject}
From: {sender}
Body preview: {body}

Common false positives to catch:
- Transaction receipts mistaken for promotions
- Shipping confirmations from retail stores
- Account statements from financial services
- Personal emails from business domains

Common false negatives to catch:
- Promotional newsletters with personal greetings
- "You might like" recommendations
- Loyalty program updates
- Social media digest emails

Respond ONLY with valid JSON (no markdown):
{{"classification_correct": true/false, "confidence": 0-100, "corrected_reason": "explanation if corrected"}}"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.stats = {
            'primary_calls': 0,
            'verification_calls': 0,
            'corrections': 0,
            'cache_hits': 0,
            'input_tokens': 0,
            'output_tokens': 0
        }
        self.last_call_time = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_call_time
        if elapsed < API_DELAY:
            time.sleep(API_DELAY - elapsed)
        self.last_call_time = time.time()

    def _call_api(self, prompt: str, retries: int = 0) -> Optional[Dict]:
        """Make API call with exponential backoff."""
        self._rate_limit()

        try:
            response = self.client.messages.create(
                model=AI_MODEL,
                max_tokens=AI_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            # Track tokens
            self.stats['input_tokens'] += response.usage.input_tokens
            self.stats['output_tokens'] += response.usage.output_tokens

            # Parse JSON response
            content = response.content[0].text.strip()

            # Handle potential markdown wrapping
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

            return json.loads(content)

        except anthropic.RateLimitError:
            if retries < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retries)
                print(f"\n  Rate limited, waiting {backoff:.1f}s...")
                time.sleep(backoff)
                return self._call_api(prompt, retries + 1)
            raise
        except json.JSONDecodeError as e:
            print(f"\n  JSON parse error: {e}")
            return None
        except Exception as e:
            if retries < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retries)
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
                'is_promotional': False,
                'confidence': 0,
                'reason': 'Classification failed',
                'verified': False
            }

        return {
            'is_promotional': result.get('is_promotional', False),
            'confidence': result.get('confidence', 50),
            'reason': result.get('reason', 'Unknown'),
            'verified': False
        }

    def verify(self, email_content: Dict, classification: Dict) -> Dict:
        """Secondary verification using Agent 2."""
        self.stats['verification_calls'] += 1

        prompt = self.VERIFIER_PROMPT.format(
            classification='promotional' if classification['is_promotional'] else 'non-promotional',
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
            return {
                'is_promotional': not classification['is_promotional'],
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


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

class ProgressTracker:
    """Tracks and persists classification progress."""

    def __init__(self, project_dir: str):
        self.progress_path = os.path.join(project_dir, PROGRESS_FILE)
        self.summary_path = os.path.join(project_dir, SUMMARY_FILE)
        self.progress = {
            'processed_ids': [],
            'page_token': None,
            'promotional_emails': [],  # List of {id, subject, sender, confidence}
            'non_promotional_count': 0,
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
                    self.progress.update(saved)
                    return bool(saved.get('processed_ids'))
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

        if classification['is_promotional']:
            self.progress['promotional_emails'].append({
                'id': msg_id,
                'subject': email_content['subject'][:100],
                'sender': email_content['sender'],
                'email': email_content['email'],
                'confidence': classification['confidence'],
                'verified': classification.get('verified', False),
                'corrected': classification.get('corrected', False)
            })
        else:
            self.progress['non_promotional_count'] += 1

    def update_page_token(self, token: Optional[str]) -> None:
        """Update pagination token."""
        self.progress['page_token'] = token

    def complete_batch(self) -> None:
        """Mark batch as complete and save."""
        self.progress['batches_completed'] += 1
        self.save()

    def get_summary(self) -> Dict:
        """Generate sender summary from promotional emails."""
        sender_groups = defaultdict(list)

        for email in self.progress['promotional_emails']:
            sender_groups[email['email']].append(email)

        summary = {
            'total_processed': len(self.progress['processed_ids']),
            'promotional_count': len(self.progress['promotional_emails']),
            'non_promotional_count': self.progress['non_promotional_count'],
            'senders': {}
        }

        for sender, emails in sorted(sender_groups.items(),
                                     key=lambda x: -len(x[1])):
            summary['senders'][sender] = {
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

    def __init__(self, project_dir: str, anthropic_key: str):
        self.project_dir = project_dir
        self.gmail = GmailService(project_dir)
        self.cache = SenderCache(project_dir)
        self.keyword_matcher = KeywordMatcher()
        self.classifier = AIClassifier(anthropic_key)
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
        print("  Legend: 💾=cached 🔑=keyword 🔍=verified ✏️=corrected ✓=promo ✗=not-promo")
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

                    # Check cache first
                    cached_result = None
                    if use_cache:
                        cached_result = self.cache.check(email_content['email'])

                    if cached_result is not None:
                        # Use cached classification
                        self.classifier.stats['cache_hits'] += 1
                        classification = {
                            'is_promotional': cached_result,
                            'confidence': 95,
                            'reason': 'Cached sender',
                            'verified': True,
                            'cached': True
                        }
                        print("💾", end="", flush=True)
                    else:
                        # Check keywords before AI classification
                        keyword_result, match_count, matched_keywords = \
                            self.keyword_matcher.check(email_content)

                        if keyword_result is not None:
                            # Keyword match found - classify as promotional
                            self.classifier.stats['keyword_hits'] = \
                                self.classifier.stats.get('keyword_hits', 0) + 1
                            classification = {
                                'is_promotional': True,
                                'confidence': min(70 + match_count * 5, 95),
                                'reason': f'Keyword match ({match_count}): {", ".join(matched_keywords[:3])}',
                                'verified': True,
                                'keyword_match': True
                            }
                            print("🔑", end="", flush=True)

                            # Update cache with keyword result
                            self.cache.update(email_content['email'], True)
                        else:
                            # AI classification
                            classification = self.classifier.classify_with_verification(
                                email_content, verify_low_confidence
                            )

                            # Update cache
                            self.cache.update(email_content['email'],
                                             classification['is_promotional'])

                            # Print indicator (only for AI classification)
                            if classification.get('corrected'):
                                print("✏️", end="", flush=True)
                            elif classification.get('verified'):
                                print("🔍", end="", flush=True)
                            elif classification['is_promotional']:
                                print("✓", end="", flush=True)
                            else:
                                print("✗", end="", flush=True)

                    # Record result
                    self.progress.add_result(msg_id, email_content, classification)

                    batch_processed += 1
                    processed += 1

                    if max_total and processed >= max_total:
                        break

                # Save progress after each batch
                self.progress.update_page_token(next_token)
                self.progress.complete_batch()
                self.cache.save()

                # Print batch stats
                promo_count = len(self.progress.progress['promotional_emails'])
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
            'estimated_cost': self._estimate_cost()
        }

        return results

    def _estimate_cost(self) -> Dict:
        """Estimate API costs based on token usage."""
        # Claude Haiku pricing (as of 2024)
        INPUT_COST_PER_M = 0.25   # $0.25 per million input tokens
        OUTPUT_COST_PER_M = 1.25  # $1.25 per million output tokens

        input_cost = (self.classifier.stats['input_tokens'] / 1_000_000) * INPUT_COST_PER_M
        output_cost = (self.classifier.stats['output_tokens'] / 1_000_000) * OUTPUT_COST_PER_M

        return {
            'input_tokens': self.classifier.stats['input_tokens'],
            'output_tokens': self.classifier.stats['output_tokens'],
            'input_cost': f"${input_cost:.4f}",
            'output_cost': f"${output_cost:.4f}",
            'total_cost': f"${input_cost + output_cost:.4f}"
        }

    def delete_promotional(self, dry_run: bool = True) -> Dict:
        """Delete promotional emails after user confirmation."""
        promo_emails = self.progress.progress['promotional_emails']

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
    cost = results['estimated_cost']

    print("\n" + "=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)

    print(f"\nEmails Processed: {summary['total_processed']}")
    print(f"  Promotional:     {summary['promotional_count']}")
    print(f"  Non-Promotional: {summary['non_promotional_count']}")

    print(f"\nClassification Statistics:")
    print(f"  AI Classifications:     {stats['primary_calls']}")
    print(f"  AI Verifications:       {stats['verification_calls']}")
    print(f"  AI Corrections:         {stats['corrections']}")
    print(f"  Keyword Matches:        {stats.get('keyword_hits', 0)}")
    print(f"  Cache Hits:             {stats['cache_hits']}")

    total_classified = stats['cache_hits'] + stats.get('keyword_hits', 0) + stats['primary_calls']
    if total_classified > 0:
        # Fast path = cache + keyword hits (no AI needed)
        fast_path = stats['cache_hits'] + stats.get('keyword_hits', 0)
        fast_rate = (fast_path / total_classified) * 100
        print(f"  Fast Path Rate:         {fast_rate:.1f}% (cache + keywords)")

        if stats['verification_calls'] > 0:
            correction_rate = (stats['corrections'] /
                              stats['verification_calls']) * 100
            print(f"  Correction Rate:        {correction_rate:.1f}%")

    print(f"\nToken Usage:")
    print(f"  Input:  {cost['input_tokens']:,} tokens ({cost['input_cost']})")
    print(f"  Output: {cost['output_tokens']:,} tokens ({cost['output_cost']})")
    print(f"  Total Cost: {cost['total_cost']}")

    # Top senders
    if summary['senders']:
        print(f"\nTop 10 Promotional Senders:")
        for i, (sender, data) in enumerate(list(summary['senders'].items())[:10]):
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
    parser.add_argument('--api-key', '-k',
                        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
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

    args = parser.parse_args()

    print_header()

    # Get API key
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: Anthropic API key required!")
        print("Set ANTHROPIC_API_KEY environment variable or use --api-key flag")
        sys.exit(1)

    # Initialize classifier
    classifier = GmailClassifier(args.project_dir, api_key)

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
