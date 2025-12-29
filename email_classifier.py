"""
Main Email Classifier - Production-grade Gmail classifier with safety guarantees
Orchestrates all components: Gmail API, AI classification, domain checking, decision engine
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import asdict

from dotenv import load_dotenv
from tqdm import tqdm
from colorama import init, Fore, Style

from config import Market, Language, EmailCategory, ConfidenceLevel, get_confidence_level
from domain_checker import DomainChecker
from decision_engine import DecisionEngine, DeletionDecision
from gmail_client import GmailClient, EmailMessage
from ai_classifier import AIClassifier, AIProvider, ClassificationResult
from confidence_analyzer import ConfidenceAnalyzer, ValidationResult
from logger import setup_logger, get_logger
from resume_manager import ResumeManager, print_resume_prompt, get_resume_choice

# Initialize colorama for colored terminal output
init(autoreset=True)

# Load environment variables
load_dotenv()


class EmailClassifierApp:
    """
    Main application orchestrating the email classification and deletion workflow.
    """

    def __init__(
        self,
        market: Market = Market.ALL,
        language: Language = Language.BOTH,
        provider: AIProvider = AIProvider.GEMINI,
        confidence_threshold: float = 90.0,
        enable_human_review: bool = True,
        dry_run: bool = True,
        log_level: str = "INFO",
    ):
        """
        Initialize email classifier application.

        Args:
            market: Target market (usa, india, germany, or all)
            language: Language filter (en, de, or both)
            provider: AI provider (gemini or anthropic)
            confidence_threshold: Minimum confidence for deletion
            enable_human_review: Enable human review for medium confidence
            dry_run: If True, don't actually delete emails
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.market = market
        self.language = language
        self.provider = provider
        self.confidence_threshold = confidence_threshold
        self.enable_human_review = enable_human_review
        self.dry_run = dry_run

        # Setup logging
        self.logger = setup_logger('EmailClassifier', log_level=log_level)

        # Initialize components
        print(f"{Fore.CYAN}Initializing Email Classifier...")
        self.logger.info(f"Market: {market.value}, Language: {language.value}, Provider: {provider.value}")
        self.logger.info(f"Confidence Threshold: {confidence_threshold}%")
        self.logger.info(f"Dry Run: {dry_run}")
        self.logger.info(f"Log Level: {log_level}")

        self.gmail_client = GmailClient()
        self.domain_checker = DomainChecker(market)
        self.decision_engine = DecisionEngine(
            self.domain_checker,
            confidence_threshold=confidence_threshold,
            enable_human_review=enable_human_review,
        )
        self.ai_classifier = AIClassifier(provider=provider)
        self.analyzer = ConfidenceAnalyzer()
        self.resume_manager = ResumeManager()

        # Results storage
        self.results: List[Dict] = []
        self.results_dir = "classification_results"
        os.makedirs(self.results_dir, exist_ok=True)

        self.logger.debug("Initialization complete")

    def run(
        self,
        max_emails: Optional[int] = None,
        query: str = "",
        delete_approved: bool = False,
        delete_high_confidence_only: bool = False,
        resume: bool = False,
    ):
        """
        Run the complete email classification and deletion workflow with resume support.

        Args:
            max_emails: Maximum number of emails to process
            query: Gmail search query
            delete_approved: Actually delete approved emails (not dry-run)
            delete_high_confidence_only: Only delete high confidence emails
            resume: Enable resume functionality
        """
        self.logger.info("Starting email classification workflow")

        # Check for resumable session
        can_resume = self.resume_manager.can_resume()

        if can_resume and resume:
            print_resume_prompt()

            if self.resume_manager.load_existing_session():
                summary = self.resume_manager.get_progress_summary()
                print(f"\n{Fore.CYAN}Previous Session Details:")
                print(f"  Session ID: {summary['session_id']}")
                print(f"  Started: {summary['started_at']}")
                print(f"  Processed: {summary['processed']} emails")
                print(f"  Approved: {summary['approved']}, Rejected: {summary['rejected']}, Flagged: {summary['flagged']}")

            choice = get_resume_choice()

            if choice == 's':
                return  # Just showed details
            elif choice == 'n':
                self.logger.info("Starting new session (discarding previous)")
                can_resume = False
            elif choice == 'r':
                self.logger.info("Resuming previous session")
                # Continue with existing session
        else:
            can_resume = False

        # Start new session if not resuming
        if not can_resume:
            session_id = self.resume_manager.start_new_session(
                query=query,
                max_emails=max_emails,
                market=self.market.value,
                language=self.language.value,
                provider=self.provider.value,
            )
            self.logger.info(f"Started new session: {session_id}")

        # Step 1: Authenticate with Gmail
        if not self._authenticate():
            return

        # Step 2: Fetch emails
        emails = self._fetch_emails(max_emails, query)
        if not emails:
            self.logger.warning("No emails found")
            print(f"{Fore.YELLOW}No emails found.")
            return

        self.resume_manager.update_progress(total_found=len(emails), fetched=len(emails))

        # Filter out already processed emails if resuming
        if can_resume:
            original_count = len(emails)
            emails = [e for e in emails if not self.resume_manager.is_email_processed(e.id)]
            skipped = original_count - len(emails)
            if skipped > 0:
                self.logger.info(f"Skipped {skipped} already processed emails")
                print(f"{Fore.YELLOW}Skipped {skipped} already processed emails (resuming)\n")

        if not emails:
            self.logger.info("All emails already processed")
            print(f"{Fore.GREEN}All emails already processed!")
            self.resume_manager.complete_session()
            return

        # Step 3: Classify emails with AI (dual-agent)
        classifications = self._classify_emails(emails)
        self.resume_manager.update_progress(classified=len(classifications))

        # Step 4: Make deletion decisions (5-gate safety system)
        decisions = self._make_decisions(emails, classifications)
        self.resume_manager.update_progress(decided=len(decisions))

        # Mark emails as processed
        for d in decisions:
            self.resume_manager.mark_email_processed(d["email"].id)

        # Update result counts
        approved = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.APPROVED)
        rejected = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.REJECTED)
        flagged = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.FLAGGED_FOR_REVIEW)
        self.resume_manager.update_results(approved, rejected, flagged)

        # Step 5: Review flagged emails (if human review enabled)
        if self.enable_human_review:
            decisions = self._review_flagged_emails(decisions)

        # Step 6: Delete approved emails (if enabled)
        if delete_approved and not self.dry_run:
            self._delete_emails(decisions, high_confidence_only=delete_high_confidence_only)

        # Step 7: Generate report
        self._generate_report(decisions)

        # Step 8: Save results
        self._save_results(decisions)

        # Complete session
        self.logger.info("Classification workflow completed")
        self.resume_manager.complete_session()
        print(f"\n{Fore.GREEN}✓ Session completed successfully")

    def _authenticate(self) -> bool:
        """Authenticate with Gmail"""
        print(f"{Fore.CYAN}Authenticating with Gmail...")
        success = self.gmail_client.authenticate()
        if success:
            print(f"{Fore.GREEN}✓ Authentication successful\n")
        else:
            print(f"{Fore.RED}✗ Authentication failed\n")
        return success

    def _fetch_emails(self, max_emails: Optional[int], query: str) -> List[EmailMessage]:
        """Fetch emails from Gmail"""
        print(f"{Fore.CYAN}Fetching emails from Gmail...")
        if query:
            print(f"Query: {query}")

        emails = self.gmail_client.fetch_emails(query=query, max_results=max_emails)

        print(f"{Fore.GREEN}✓ Fetched {len(emails)} emails\n")
        return emails

    def _classify_emails(self, emails: List[EmailMessage]) -> List[ClassificationResult]:
        """Classify emails using AI with dual-agent verification"""
        print(f"{Fore.CYAN}Classifying emails with AI (dual-agent system)...")

        # Prepare email data for AI
        email_data = [
            {
                "from": email.from_address,
                "subject": email.subject,
                "body": email.body[:1000],  # Limit body length
            }
            for email in emails
        ]

        # Classify with progress bar
        with tqdm(total=len(emails), desc="Classifying", unit="email") as pbar:
            classifications = self.ai_classifier.classify_batch(email_data)
            pbar.update(len(emails))

        print(f"{Fore.GREEN}✓ Classification complete\n")
        return classifications

    def _make_decisions(
        self,
        emails: List[EmailMessage],
        classifications: List[ClassificationResult],
    ) -> List[Dict]:
        """Make deletion decisions using 5-gate safety system"""
        print(f"{Fore.CYAN}Evaluating emails with 5-gate safety system...")

        decisions = []

        for email, classification in zip(emails, classifications):
            # Evaluate with decision engine
            result = self.decision_engine.evaluate(
                email_id=email.id,
                category=classification.category.value,
                confidence=classification.confidence,
                verified=classification.verified,
                from_address=email.from_address,
                is_starred=email.is_starred,
                is_important=email.is_important,
                metadata={
                    "subject": email.subject,
                    "from": email.from_address,
                    "language": classification.language,
                },
            )

            # Store decision with full context
            decisions.append({
                "email": email,
                "classification": classification,
                "decision": result,
            })

        print(f"{Fore.GREEN}✓ Evaluation complete\n")
        return decisions

    def _review_flagged_emails(self, decisions: List[Dict]) -> List[Dict]:
        """Human review of flagged emails (medium confidence)"""
        flagged = [d for d in decisions if d["decision"].decision == DeletionDecision.FLAGGED_FOR_REVIEW]

        if not flagged:
            return decisions

        print(f"{Fore.YELLOW}Found {len(flagged)} emails flagged for human review\n")

        # In a real implementation, this would present a UI for review
        # For now, we just show the flagged emails
        for i, decision_data in enumerate(flagged, 1):
            email = decision_data["email"]
            classification = decision_data["classification"]
            decision = decision_data["decision"]

            print(f"{Fore.YELLOW}Flagged Email {i}/{len(flagged)}:")
            print(f"  From: {email.from_address}")
            print(f"  Subject: {email.subject}")
            print(f"  Category: {classification.category.value}")
            print(f"  Confidence: {classification.confidence}%")
            print(f"  Reason: {classification.reason}")
            print()

        return decisions

    def _delete_emails(self, decisions: List[Dict], high_confidence_only: bool = False):
        """Delete approved emails"""
        # Filter to approved decisions
        to_delete = [
            d for d in decisions
            if d["decision"].decision == DeletionDecision.APPROVED
        ]

        # Further filter to high confidence only if specified
        if high_confidence_only:
            to_delete = [
                d for d in to_delete
                if d["decision"].confidence_level == ConfidenceLevel.HIGH
            ]

        if not to_delete:
            print(f"{Fore.YELLOW}No emails approved for deletion\n")
            return

        print(f"{Fore.RED}Deleting {len(to_delete)} approved emails...")

        message_ids = [d["email"].id for d in to_delete]

        # Batch delete (move to trash for safety)
        results = self.gmail_client.batch_delete_emails(message_ids, use_trash=True)

        print(f"{Fore.GREEN}✓ Deleted {results['success']} emails")
        if results['failed'] > 0:
            print(f"{Fore.RED}✗ Failed to delete {results['failed']} emails")
        print()

    def _generate_report(self, decisions: List[Dict]):
        """Generate summary report"""
        print(f"\n{'='*80}")
        print(f"{Fore.CYAN}CLASSIFICATION SUMMARY")
        print(f"{'='*80}")

        # Overall stats
        total = len(decisions)
        approved = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.APPROVED)
        rejected = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.REJECTED)
        flagged = sum(1 for d in decisions if d["decision"].decision == DeletionDecision.FLAGGED_FOR_REVIEW)

        print(f"\nTotal Emails: {total}")
        print(f"{Fore.GREEN}Approved for Deletion: {approved} ({approved/total*100:.1f}%)")
        print(f"{Fore.RED}Rejected (Protected): {rejected} ({rejected/total*100:.1f}%)")
        print(f"{Fore.YELLOW}Flagged for Review: {flagged} ({flagged/total*100:.1f}%)")

        # Category breakdown
        print(f"\n{Fore.CYAN}Category Breakdown:")
        category_counts = {}
        for d in decisions:
            cat = d["classification"].category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, count in sorted(category_counts.items()):
            print(f"  {cat}: {count}")

        # Market breakdown (protected domains)
        print(f"\n{Fore.CYAN}Protected Domain Breakdown:")
        market_stats = self.domain_checker.get_market_stats(
            [d["email"].from_address for d in decisions]
        )
        print(f"  Total Protected: {market_stats['protected']}")
        print(f"  USA: {market_stats['usa']}")
        print(f"  India: {market_stats['india']}")
        print(f"  Germany: {market_stats['germany']}")

        # Decision engine stats
        print(f"\n{Fore.CYAN}Decision Engine Statistics:")
        self.decision_engine.print_stats()

    def _save_results(self, decisions: List[Dict]):
        """Save results to JSON file and flagged emails to separate file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"classification_results_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)

        # Prepare data for JSON serialization
        results = []
        flagged_results = []

        for d in decisions:
            email = d["email"]
            classification = d["classification"]
            decision = d["decision"]

            result_data = {
                "email_id": email.id,
                "from": email.from_address,
                "subject": email.subject,
                "category": classification.category.value,
                "confidence": classification.confidence,
                "language": classification.language,
                "verified": classification.verified,
                "decision": decision.decision.value,
                "confidence_level": decision.confidence_level.value,
                "final_reason": decision.final_reason,
                "gates": [
                    {
                        "gate_number": g.gate_number,
                        "gate_name": g.gate_name,
                        "passed": g.passed,
                        "reason": g.reason,
                    }
                    for g in decision.gates
                ],
            }

            results.append(result_data)

            # Collect flagged emails separately
            if decision.decision.value == "flagged":
                flagged_results.append(result_data)

        # Save all results
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n{Fore.GREEN}✓ Results saved to {filepath}")

        # Save flagged emails to separate file
        if flagged_results:
            flagged_filename = f"flagged_for_review_{timestamp}.json"
            flagged_filepath = os.path.join(self.results_dir, flagged_filename)

            with open(flagged_filepath, 'w') as f:
                json.dump(flagged_results, f, indent=2)

            print(f"{Fore.YELLOW}✓ {len(flagged_results)} flagged emails saved to {flagged_filepath}")

        print()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Safety-First Gmail Email Classifier with Multi-Regional Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Basic options
    parser.add_argument(
        "--max-emails",
        type=int,
        default=None,
        help="Maximum number of emails to process (default: all)",
    )

    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Gmail search query (e.g., 'is:unread', 'from:example.com')",
    )

    # Market and language
    parser.add_argument(
        "--market",
        type=str,
        choices=["usa", "india", "germany", "all"],
        default="all",
        help="Target market for protected domain optimization (default: all)",
    )

    parser.add_argument(
        "--language",
        type=str,
        choices=["en", "de", "both"],
        default="both",
        help="Language filter (default: both)",
    )

    # AI provider
    parser.add_argument(
        "--provider",
        type=str,
        choices=["gemini", "anthropic"],
        default="gemini",
        help="AI provider for classification (default: gemini)",
    )

    # Safety options
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=90.0,
        help="Minimum confidence threshold for deletion (default: 90%%)",
    )

    parser.add_argument(
        "--disable-human-review",
        action="store_true",
        help="Disable human review for medium confidence emails",
    )

    # Deletion options
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete approved emails (not dry-run)",
    )

    parser.add_argument(
        "--delete-high-confidence",
        action="store_true",
        help="Only delete high confidence emails (≥90%%)",
    )

    # Analysis options
    parser.add_argument(
        "--analyze-thresholds",
        action="store_true",
        help="Generate precision-recall curves and threshold analysis",
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show summary of previous results without processing new emails",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (sets log level to DEBUG)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Enable resume functionality (continue from interrupted session)",
    )

    args = parser.parse_args()

    # Determine log level
    log_level = "DEBUG" if args.debug else args.log_level

    # Validate environment
    provider_key = "GEMINI_API_KEY" if args.provider == "gemini" else "ANTHROPIC_API_KEY"
    if not os.getenv(provider_key):
        print(f"{Fore.RED}ERROR: {provider_key} not set in environment")
        print(f"Please set it in .env file or export {provider_key}=your-api-key")
        sys.exit(1)

    # Initialize app
    app = EmailClassifierApp(
        market=Market(args.market),
        language=Language(args.language),
        provider=AIProvider(args.provider),
        confidence_threshold=args.confidence_threshold,
        enable_human_review=not args.disable_human_review,
        dry_run=not args.delete,
        log_level=log_level,
    )

    # Run
    if args.summary_only:
        print(f"{Fore.YELLOW}Summary-only mode not yet implemented")
        return

    if args.analyze_thresholds:
        print(f"{Fore.YELLOW}Threshold analysis mode not yet implemented")
        print("Run classifier first to generate validation data")
        return

    # Run main workflow
    app.run(
        max_emails=args.max_emails,
        query=args.query,
        delete_approved=args.delete or args.delete_high_confidence,
        delete_high_confidence_only=args.delete_high_confidence,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
