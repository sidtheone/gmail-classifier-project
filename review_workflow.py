"""
Human-in-the-Loop Review Workflow
Interactive CLI for reviewing flagged emails (medium confidence)
"""

import json
import os
from typing import List, Dict
from datetime import datetime

from colorama import init, Fore, Style

init(autoreset=True)


class ReviewWorkflow:
    """
    Interactive workflow for reviewing medium-confidence flagged emails.
    Allows users to approve/reject flagged deletions with feedback.
    """

    def __init__(self, results_file: str):
        """
        Initialize review workflow.

        Args:
            results_file: Path to classification results JSON
        """
        self.results_file = results_file
        self.results = self._load_results()
        self.decisions = {
            "approved": [],
            "rejected": [],
            "skipped": [],
        }

    def _load_results(self) -> List[Dict]:
        """Load classification results from JSON file"""
        if not os.path.exists(self.results_file):
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, 'r') as f:
            return json.load(f)

    def get_flagged_emails(self) -> List[Dict]:
        """Get all emails flagged for review"""
        return [r for r in self.results if r.get("decision") == "flagged"]

    def review_email(self, email_data: Dict) -> str:
        """
        Present single email for review.

        Args:
            email_data: Email data dictionary

        Returns:
            Decision: 'approve', 'reject', or 'skip'
        """
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}FLAGGED EMAIL FOR REVIEW")
        print(f"{Fore.CYAN}{'='*80}\n")

        # Email details
        print(f"{Fore.WHITE}From: {Fore.GREEN}{email_data['from']}")
        print(f"{Fore.WHITE}Subject: {Fore.GREEN}{email_data['subject']}")
        print(f"{Fore.WHITE}Category: {Fore.YELLOW}{email_data['category'].upper()}")
        print(f"{Fore.WHITE}Confidence: {Fore.YELLOW}{email_data['confidence']}%")
        print(f"{Fore.WHITE}Language: {email_data['language']}")

        # Classification details
        print(f"\n{Fore.CYAN}Classification Details:")
        print(f"{Fore.WHITE}Verified: {Fore.GREEN if email_data['verified'] else Fore.RED}{email_data['verified']}")
        print(f"{Fore.WHITE}Reason: {email_data.get('final_reason', 'N/A')}")

        # Gate results
        print(f"\n{Fore.CYAN}Safety Gates:")
        for gate in email_data.get('gates', []):
            status = f"{Fore.GREEN}PASS" if gate['passed'] else f"{Fore.RED}FAIL"
            print(f"  {status} {Fore.WHITE}Gate {gate['gate_number']}: {gate['gate_name']} - {gate['reason']}")

        # User decision
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}What would you like to do?")
        print(f"  {Fore.GREEN}[a] Approve deletion (move to trash)")
        print(f"  {Fore.RED}[r] Reject deletion (keep email)")
        print(f"  {Fore.YELLOW}[s] Skip (decide later)")
        print(f"  {Fore.CYAN}[q] Quit review")

        while True:
            choice = input(f"\n{Fore.WHITE}Your choice [a/r/s/q]: ").strip().lower()

            if choice in ['a', 'approve']:
                return 'approve'
            elif choice in ['r', 'reject']:
                return 'reject'
            elif choice in ['s', 'skip']:
                return 'skip'
            elif choice in ['q', 'quit']:
                return 'quit'
            else:
                print(f"{Fore.RED}Invalid choice. Please enter a, r, s, or q.")

    def run_review(self):
        """Run interactive review workflow"""
        flagged = self.get_flagged_emails()

        if not flagged:
            print(f"{Fore.GREEN}No emails flagged for review!")
            return

        print(f"\n{Fore.CYAN}Starting Human Review Workflow")
        print(f"{Fore.WHITE}Found {len(flagged)} emails flagged for review\n")

        for i, email_data in enumerate(flagged, 1):
            print(f"\n{Fore.CYAN}Email {i} of {len(flagged)}")

            decision = self.review_email(email_data)

            if decision == 'quit':
                print(f"\n{Fore.YELLOW}Review session ended by user.")
                break

            # Record decision
            email_id = email_data['email_id']
            if decision == 'approve':
                self.decisions['approved'].append(email_id)
                print(f"{Fore.GREEN}✓ Approved for deletion")
            elif decision == 'reject':
                self.decisions['rejected'].append(email_id)
                print(f"{Fore.RED}✗ Rejected - will keep email")
            elif decision == 'skip':
                self.decisions['skipped'].append(email_id)
                print(f"{Fore.YELLOW}⊙ Skipped")

        # Summary
        self._print_summary()

        # Save decisions
        self._save_decisions()

    def _print_summary(self):
        """Print review summary"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}REVIEW SUMMARY")
        print(f"{Fore.CYAN}{'='*80}\n")

        print(f"{Fore.GREEN}Approved for deletion: {len(self.decisions['approved'])}")
        print(f"{Fore.RED}Rejected (keep): {len(self.decisions['rejected'])}")
        print(f"{Fore.YELLOW}Skipped (undecided): {len(self.decisions['skipped'])}")

    def _save_decisions(self):
        """Save review decisions to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_decisions_{timestamp}.json"

        output_data = {
            "review_date": timestamp,
            "source_file": self.results_file,
            "decisions": self.decisions,
            "summary": {
                "total_reviewed": len(self.decisions['approved']) + len(self.decisions['rejected']) + len(self.decisions['skipped']),
                "approved": len(self.decisions['approved']),
                "rejected": len(self.decisions['rejected']),
                "skipped": len(self.decisions['skipped']),
            }
        }

        filepath = os.path.join("classification_results", filename)
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n{Fore.GREEN}✓ Review decisions saved to {filepath}")

    def execute_deletions(self, gmail_client):
        """
        Execute approved deletions.

        Args:
            gmail_client: Authenticated GmailClient instance
        """
        if not self.decisions['approved']:
            print(f"{Fore.YELLOW}No approved deletions to execute")
            return

        print(f"\n{Fore.RED}Executing {len(self.decisions['approved'])} approved deletions...")

        results = gmail_client.batch_delete_emails(
            self.decisions['approved'],
            use_trash=True
        )

        print(f"{Fore.GREEN}✓ Successfully deleted: {results['success']}")
        if results['failed'] > 0:
            print(f"{Fore.RED}✗ Failed to delete: {results['failed']}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Human-in-the-Loop Review Workflow")
    parser.add_argument(
        "results_file",
        help="Path to classification results JSON file"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute approved deletions after review"
    )

    args = parser.parse_args()

    # Run review
    workflow = ReviewWorkflow(args.results_file)
    workflow.run_review()

    # Execute deletions if requested
    if args.execute and workflow.decisions['approved']:
        print(f"\n{Fore.RED}Execute deletions? This will move emails to trash (recoverable)")
        confirm = input(f"{Fore.WHITE}Type 'yes' to confirm: ").strip().lower()

        if confirm == 'yes':
            from gmail_client import GmailClient

            client = GmailClient()
            if client.authenticate():
                workflow.execute_deletions(client)
        else:
            print(f"{Fore.YELLOW}Deletion cancelled")


if __name__ == "__main__":
    main()
