"""
Resume Manager - Save and restore processing state for interrupted runs
Allows resuming classification from where it left off
"""

import json
import os
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ProcessingState:
    """State of email processing"""
    session_id: str
    started_at: str
    last_updated: str
    query: str
    max_emails: Optional[int]
    market: str
    language: str
    provider: str

    # Progress tracking
    total_emails_found: int
    emails_fetched: int
    emails_classified: int
    emails_decided: int

    # Processed email IDs (to skip on resume)
    processed_email_ids: Set[str]

    # Results
    approved_count: int
    rejected_count: int
    flagged_count: int


class ResumeManager:
    """
    Manages saving and loading processing state for resume functionality.
    """

    def __init__(self, state_dir: str = "classification_results"):
        """
        Initialize resume manager.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.state_file = os.path.join(state_dir, "current_state.json")
        self.state: Optional[ProcessingState] = None

    def start_new_session(
        self,
        query: str,
        max_emails: Optional[int],
        market: str,
        language: str,
        provider: str,
    ) -> str:
        """
        Start a new processing session.

        Args:
            query: Gmail query
            max_emails: Max emails to process
            market: Target market
            language: Language filter
            provider: AI provider

        Returns:
            Session ID
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        now = datetime.now().isoformat()

        self.state = ProcessingState(
            session_id=session_id,
            started_at=now,
            last_updated=now,
            query=query,
            max_emails=max_emails,
            market=market,
            language=language,
            provider=provider,
            total_emails_found=0,
            emails_fetched=0,
            emails_classified=0,
            emails_decided=0,
            processed_email_ids=set(),
            approved_count=0,
            rejected_count=0,
            flagged_count=0,
        )

        self.save_state()
        return session_id

    def load_existing_session(self) -> bool:
        """
        Load existing session from state file.

        Returns:
            True if session loaded successfully
        """
        if not os.path.exists(self.state_file):
            return False

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # Convert processed_email_ids back to set
            data['processed_email_ids'] = set(data['processed_email_ids'])

            self.state = ProcessingState(**data)
            return True

        except Exception as e:
            print(f"Error loading state: {e}")
            return False

    def save_state(self):
        """Save current state to file"""
        if not self.state:
            return

        self.state.last_updated = datetime.now().isoformat()

        # Convert set to list for JSON serialization
        data = asdict(self.state)
        data['processed_email_ids'] = list(data['processed_email_ids'])

        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def mark_email_processed(self, email_id: str):
        """Mark an email as processed"""
        if self.state:
            self.state.processed_email_ids.add(email_id)

    def is_email_processed(self, email_id: str) -> bool:
        """Check if email was already processed"""
        if not self.state:
            return False
        return email_id in self.state.processed_email_ids

    def update_progress(
        self,
        total_found: Optional[int] = None,
        fetched: Optional[int] = None,
        classified: Optional[int] = None,
        decided: Optional[int] = None,
    ):
        """Update progress counters"""
        if not self.state:
            return

        if total_found is not None:
            self.state.total_emails_found = total_found
        if fetched is not None:
            self.state.emails_fetched = fetched
        if classified is not None:
            self.state.emails_classified = classified
        if decided is not None:
            self.state.emails_decided = decided

        self.save_state()

    def update_results(self, approved: int, rejected: int, flagged: int):
        """Update result counts"""
        if not self.state:
            return

        self.state.approved_count = approved
        self.state.rejected_count = rejected
        self.state.flagged_count = flagged
        self.save_state()

    def complete_session(self):
        """Mark session as complete and archive state"""
        if not self.state:
            return

        # Archive completed session
        archive_file = os.path.join(
            self.state_dir,
            f"completed_state_{self.state.session_id}.json"
        )

        data = asdict(self.state)
        data['processed_email_ids'] = list(data['processed_email_ids'])
        data['completed_at'] = datetime.now().isoformat()

        with open(archive_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Remove current state file
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

        self.state = None

    def get_progress_summary(self) -> Dict:
        """Get progress summary for display"""
        if not self.state:
            return {}

        return {
            "session_id": self.state.session_id,
            "started_at": self.state.started_at,
            "last_updated": self.state.last_updated,
            "total_found": self.state.total_emails_found,
            "fetched": self.state.emails_fetched,
            "classified": self.state.emails_classified,
            "decided": self.state.emails_decided,
            "processed": len(self.state.processed_email_ids),
            "approved": self.state.approved_count,
            "rejected": self.state.rejected_count,
            "flagged": self.state.flagged_count,
        }

    def can_resume(self) -> bool:
        """Check if there's a resumable session"""
        return os.path.exists(self.state_file)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_resume_prompt():
    """Print resume prompt for user"""
    print("\n" + "=" * 80)
    print("RESUMABLE SESSION FOUND")
    print("=" * 80)
    print("\nA previous incomplete session was detected.")
    print("You can resume from where you left off.\n")
    print("Options:")
    print("  [r] Resume previous session")
    print("  [n] Start new session (discard previous)")
    print("  [s] Show previous session details")
    print("=" * 80)


def get_resume_choice() -> str:
    """Get user's choice for resume"""
    while True:
        choice = input("\nYour choice [r/n/s]: ").strip().lower()
        if choice in ['r', 'n', 's', 'resume', 'new', 'show']:
            return choice[0]
        print("Invalid choice. Please enter 'r', 'n', or 's'")


if __name__ == "__main__":
    # Test resume manager
    manager = ResumeManager()

    # Create test session
    session_id = manager.start_new_session(
        query="is:unread",
        max_emails=100,
        market="usa",
        language="en",
        provider="gemini"
    )

    print(f"Started session: {session_id}")

    # Simulate progress
    manager.update_progress(total_found=100, fetched=50, classified=30, decided=30)
    manager.mark_email_processed("email_1")
    manager.mark_email_processed("email_2")
    manager.update_results(approved=20, rejected=8, flagged=2)

    print("\nProgress summary:")
    summary = manager.get_progress_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Test resume
    print(f"\nCan resume: {manager.can_resume()}")

    # Load existing
    manager2 = ResumeManager()
    if manager2.load_existing_session():
        print("\nLoaded existing session:")
        print(f"  Session ID: {manager2.state.session_id}")
        print(f"  Processed emails: {len(manager2.state.processed_email_ids)}")

    # Complete session
    manager.complete_session()
    print(f"\nSession completed. Can resume: {manager.can_resume()}")
