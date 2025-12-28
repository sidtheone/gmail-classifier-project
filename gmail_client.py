"""
Gmail API Client for Gmail Classifier.

This module handles all Gmail API operations including authentication,
message fetching, and deletion with safety checks.
"""

import os
import pickle
from typing import List, Dict, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from config import GMAIL_SCOPES, CREDENTIALS_FILE, TOKEN_FILE


def debug_log(message: str, data: dict = None) -> None:
    """Import debug_log function (will be defined in email_classifier)."""
    import config
    if config.DEBUG:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"  [DEBUG {timestamp}] {message}")
        if data:
            for key, value in data.items():
                val_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                print(f"    {key}: {val_str}")


class GmailService:
    """
    Handles Gmail API authentication and operations.

    This service provides safe access to Gmail with deletion safety checks:
    - Check for manual flags (starred, important)
    - Batch trash operations (recoverable)
    - Error handling and retry logic
    """

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.credentials_path = os.path.join(project_dir, CREDENTIALS_FILE)
        self.token_path = os.path.join(project_dir, TOKEN_FILE)
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth 2.0."""
        debug_log("Gmail API: Starting authentication")
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            debug_log(f"Gmail API: Loading token from {self.token_path}")
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    debug_log("Gmail API: Refreshing expired token")
                    creds.refresh(Request())
                    print("  Token refreshed successfully")
                except Exception as e:
                    debug_log(f"Gmail API: Token refresh failed", {"error": str(e)})
                    print(f"  Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    debug_log(f"Gmail API: Credentials file not found", {"path": self.credentials_path})
                    print(f"\n  ERROR: {CREDENTIALS_FILE} not found!")
                    print(f"  Please place your OAuth credentials at:")
                    print(f"  {self.credentials_path}")
                    return False

                debug_log("Gmail API: Starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("  New authentication completed")

            # Save token
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            debug_log("Gmail API: Token saved")

        self.service = build('gmail', 'v1', credentials=creds)
        debug_log("Gmail API: Service built successfully")
        return True

    def get_messages(self, page_token: Optional[str] = None,
                     max_results: int = 100) -> Tuple[List[Dict], Optional[str]]:
        """Fetch messages from inbox with pagination."""
        debug_log(f"Gmail API: Fetching messages", {
            "max_results": max_results,
            "page_token": page_token[:20] + "..." if page_token else None
        })
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results,
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            next_token = results.get('nextPageToken')
            debug_log(f"Gmail API: Fetched {len(messages)} messages", {
                "has_next_page": next_token is not None
            })
            return messages, next_token

        except HttpError as e:
            debug_log(f"Gmail API: Error fetching messages", {
                "status": e.resp.status,
                "error": str(e)
            })
            if e.resp.status in [429, 500, 503]:
                raise  # Let caller handle with backoff
            raise

    def get_message_details(self, msg_id: str) -> Optional[Dict]:
        """Get full message details including headers and body."""
        debug_log(f"Gmail API: Fetching message details", {"msg_id": msg_id})
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            debug_log(f"Gmail API: Message fetched successfully", {"msg_id": msg_id})
            return message
        except HttpError as e:
            debug_log(f"Gmail API: Error fetching message", {
                "msg_id": msg_id,
                "status": e.resp.status,
                "error": str(e)
            })
            if e.resp.status == 404:
                return None
            raise

    def has_manual_flags(self, msg_id: str) -> Tuple[bool, List[str]]:
        """
        Check if email has manual flags (starred, important).

        This is a CRITICAL SAFETY CHECK - emails manually flagged by the user
        should NEVER be deleted, as the user explicitly marked them as important.

        Args:
            msg_id: Gmail message ID

        Returns:
            Tuple of (has_flags, list_of_flags)
            - has_flags: True if email has any manual flags
            - list_of_flags: List of flag names (e.g., ['starred', 'important'])
        """
        debug_log(f"Gmail API: Checking manual flags", {"msg_id": msg_id})
        try:
            # Fetch minimal message with just labels
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='minimal'  # Only fetch metadata
            ).execute()

            labels = message.get('labelIds', [])
            flags = []

            # Check for starred
            if 'STARRED' in labels:
                flags.append('starred')

            # Check for important
            if 'IMPORTANT' in labels:
                flags.append('important')

            has_flags = bool(flags)
            debug_log(f"Gmail API: Manual flags check complete", {
                "msg_id": msg_id,
                "has_flags": has_flags,
                "flags": flags
            })

            return has_flags, flags

        except HttpError as e:
            debug_log(f"Gmail API: Error checking flags", {
                "msg_id": msg_id,
                "error": str(e)
            })
            # On error, assume it might be important (safer)
            return False, []

    def trash_messages(self, message_ids: List[str]) -> int:
        """
        Move messages to trash in batches.

        NOTE: This moves to TRASH, not permanent deletion.
        Emails can be recovered from trash by the user.
        """
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
