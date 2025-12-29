"""
Gmail Client - OAuth 2.0 authentication and email fetching
Supports batch operations and manual flag detection (starred/important)
"""

import os
import pickle
import base64
import time
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm

from config import BATCH_CONFIG
from logger import get_logger


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
]


def retry_with_backoff(func: Callable, *args, **kwargs):
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result
    """
    max_retries = BATCH_CONFIG['max_retries']
    base_delay = BATCH_CONFIG['retry_delay']
    backoff = BATCH_CONFIG['retry_backoff']

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if attempt == max_retries - 1:
                # Last attempt failed
                raise

            # Calculate delay with exponential backoff
            delay = base_delay * (backoff ** attempt)

            print(f"⚠️  API call failed (attempt {attempt + 1}/{max_retries}): {e.resp.status} {e.error_details if hasattr(e, 'error_details') else e}")
            print(f"   Retrying in {delay} seconds...")

            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = base_delay * (backoff ** attempt)
            print(f"⚠️  Error occurred (attempt {attempt + 1}/{max_retries}): {str(e)}")
            print(f"   Retrying in {delay} seconds...")

            time.sleep(delay)

    raise RuntimeError(f"Failed after {max_retries} attempts")


@dataclass
class EmailMessage:
    """Structured email message data"""
    id: str
    thread_id: str
    subject: str
    from_address: str
    to_address: str
    date: str
    snippet: str
    body: str
    labels: List[str]
    is_starred: bool
    is_important: bool
    is_unread: bool
    raw_message: Dict[str, Any]


class GmailClient:
    """
    Gmail API client with OAuth 2.0 authentication.
    Supports batch fetching and manual flag detection.
    """

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.pickle'):
        """
        Initialize Gmail client.

        Args:
            credentials_file: Path to OAuth 2.0 credentials JSON
            token_file: Path to save/load access token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.creds = None
        self.logger = get_logger('GmailClient')

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth 2.0.

        Returns:
            True if authentication successful
        """
        # Load existing token if available
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired token
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    print("Need to re-authenticate...")
                    self.creds = None

            if not self.creds:
                # New authentication flow
                if not os.path.exists(self.credentials_file):
                    print(f"ERROR: Credentials file not found: {self.credentials_file}")
                    print("Please download OAuth 2.0 credentials from Google Cloud Console")
                    return False

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during authentication: {e}")
                    return False

            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            print(f"Error building Gmail service: {e}")
            return False

    def fetch_emails(
        self,
        query: str = '',
        max_results: Optional[int] = None,
        label_ids: Optional[List[str]] = None,
        show_progress: bool = True,
    ) -> List[EmailMessage]:
        """
        Fetch emails matching query with progress tracking.

        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example.com')
            max_results: Maximum number of emails to fetch (None = all)
            label_ids: List of label IDs to filter by
            show_progress: Show progress bar

        Returns:
            List of EmailMessage objects
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        self.logger.info(f"Fetching emails with query: '{query}'")
        if max_results:
            self.logger.info(f"Max results: {max_results}")

        emails: List[EmailMessage] = []
        page_token = None
        total_messages = 0
        pbar = None

        try:
            # First, get total count for progress bar
            def _fetch_list_count():
                return self.service.users().messages().list(
                    userId='me',
                    q=query,
                    labelIds=label_ids,
                    maxResults=1,
                ).execute()

            count_result = retry_with_backoff(_fetch_list_count)
            estimated_total = count_result.get('resultSizeEstimate', 0)
            self.logger.info(f"Estimated {estimated_total} emails found")

            # Limit by max_results if specified
            progress_total = min(estimated_total, max_results) if max_results else estimated_total

            if show_progress and progress_total > 0:
                pbar = tqdm(
                    total=progress_total,
                    desc="Downloading emails",
                    unit="email",
                    colour="green"
                )

            while True:
                # Fetch message IDs with retry
                def _fetch_list():
                    return self.service.users().messages().list(
                        userId='me',
                        q=query,
                        labelIds=label_ids,
                        maxResults=BATCH_CONFIG['gmail_fetch_batch_size'],
                        pageToken=page_token,
                    ).execute()

                self.logger.debug(f"Fetching batch (page_token: {page_token})")
                results = retry_with_backoff(_fetch_list)
                messages = results.get('messages', [])

                if not messages:
                    self.logger.debug("No more messages to fetch")
                    break

                self.logger.debug(f"Fetched {len(messages)} message IDs")

                # Fetch full message details
                for msg_ref in messages:
                    try:
                        email = self.fetch_email_by_id(msg_ref['id'])
                        if email:
                            emails.append(email)
                            if pbar:
                                pbar.update(1)

                        # Check max_results limit
                        if max_results and len(emails) >= max_results:
                            self.logger.info(f"Reached max_results limit: {max_results}")
                            if pbar:
                                pbar.close()
                            return emails

                    except Exception as e:
                        self.logger.error(f"Error fetching email {msg_ref['id']}: {e}")
                        continue

                # Check for next page
                page_token = results.get('nextPageToken')
                if not page_token:
                    self.logger.debug("No more pages")
                    break

            if pbar:
                pbar.close()

        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            if pbar:
                pbar.close()

        self.logger.info(f"Successfully fetched {len(emails)} emails")
        return emails

    def fetch_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """
        Fetch single email by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            EmailMessage object or None if error
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            def _fetch_message():
                return self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()

            message = retry_with_backoff(_fetch_message)
            return self._parse_email(message)

        except HttpError as error:
            print(f"Error fetching email {message_id}: {error}")
            return None

    def _parse_email(self, message: Dict) -> EmailMessage:
        """
        Parse raw Gmail message into EmailMessage object.

        Args:
            message: Raw Gmail API message

        Returns:
            EmailMessage object
        """
        headers = {h['name']: h['value'] for h in message['payload']['headers']}

        # Extract body
        body = self._extract_body(message['payload'])

        # Extract labels
        labels = message.get('labelIds', [])

        # Detect manual flags
        is_starred = 'STARRED' in labels
        is_important = 'IMPORTANT' in labels
        is_unread = 'UNREAD' in labels

        return EmailMessage(
            id=message['id'],
            thread_id=message['threadId'],
            subject=headers.get('Subject', '(No Subject)'),
            from_address=headers.get('From', ''),
            to_address=headers.get('To', ''),
            date=headers.get('Date', ''),
            snippet=message.get('snippet', ''),
            body=body,
            labels=labels,
            is_starred=is_starred,
            is_important=is_important,
            is_unread=is_unread,
            raw_message=message,
        )

    def _extract_body(self, payload: Dict) -> str:
        """
        Extract email body from payload.

        Args:
            payload: Email payload from Gmail API

        Returns:
            Email body text (decoded)
        """
        body = ''

        # Check for direct body data
        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        # Check for multipart
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

                # Recursive for nested parts
                elif 'parts' in part:
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def delete_email(self, message_id: str) -> bool:
        """
        Permanently delete an email.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            self.service.users().messages().delete(
                userId='me',
                id=message_id
            ).execute()
            return True

        except HttpError as error:
            print(f"Error deleting email {message_id}: {error}")
            return False

    def trash_email(self, message_id: str) -> bool:
        """
        Move email to trash (recoverable).

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return True

        except HttpError as error:
            print(f"Error trashing email {message_id}: {error}")
            return False

    def batch_delete_emails(self, message_ids: List[str], use_trash: bool = True) -> Dict[str, int]:
        """
        Delete multiple emails in batch.

        Args:
            message_ids: List of Gmail message IDs
            use_trash: If True, move to trash (recoverable), else permanently delete

        Returns:
            Dictionary with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'total': len(message_ids),
        }

        for msg_id in message_ids:
            if use_trash:
                success = self.trash_email(msg_id)
            else:
                success = self.delete_email(msg_id)

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

        return results

    def get_labels(self) -> List[Dict]:
        """
        Get all Gmail labels.

        Returns:
            List of label dictionaries
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])

        except HttpError as error:
            print(f"Error fetching labels: {error}")
            return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Gmail Client Test")
    print("=" * 80)

    # Initialize client
    client = GmailClient()

    # Authenticate
    print("\nAuthenticating with Gmail...")
    if not client.authenticate():
        print("Authentication failed!")
        exit(1)

    print("Authentication successful!\n")

    # Fetch latest 5 emails
    print("Fetching latest 5 emails...")
    emails = client.fetch_emails(max_results=5)

    print(f"\nFound {len(emails)} emails:\n")

    for i, email in enumerate(emails, 1):
        print(f"{i}. {email.subject}")
        print(f"   From: {email.from_address}")
        print(f"   Date: {email.date}")
        print(f"   Starred: {email.is_starred}, Important: {email.is_important}")
        print(f"   Snippet: {email.snippet[:100]}...")
        print()

    # Get labels
    print("\nGmail Labels:")
    labels = client.get_labels()
    for label in labels[:10]:  # Show first 10
        print(f"  - {label['name']} (ID: {label['id']})")

    print("\n" + "=" * 80)
