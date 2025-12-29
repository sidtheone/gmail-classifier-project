"""
Confidence Analyzer - Precision-Recall optimization and threshold analysis
Helps find optimal confidence thresholds balancing safety vs. deletion efficiency
"""

import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, f1_score, confusion_matrix
import numpy as np

from config import EmailCategory, ConfidenceLevel, CONFIDENCE_THRESHOLDS


@dataclass
class ThresholdAnalysis:
    """Analysis results for a specific threshold"""
    threshold: float
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    deletion_rate: float  # % of emails that would be deleted


@dataclass
class ValidationResult:
    """Single email validation result (ground truth + prediction)"""
    email_id: str
    predicted_category: EmailCategory
    actual_category: EmailCategory
    confidence: float
    from_address: str
    subject: str


class ConfidenceAnalyzer:
    """
    Analyze classification confidence and optimize thresholds.

    Uses precision-recall curves to find optimal balance between:
    - High precision (no false positives on critical emails)
    - High recall (delete most promotional emails)
    """

    def __init__(self, output_dir: str = "plots"):
        """
        Initialize confidence analyzer.

        Args:
            output_dir: Directory to save analysis plots
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def analyze_thresholds(
        self,
        validation_results: List[ValidationResult],
        thresholds: Optional[List[float]] = None,
    ) -> List[ThresholdAnalysis]:
        """
        Analyze performance across different confidence thresholds.

        Args:
            validation_results: List of validation results with ground truth
            thresholds: List of thresholds to test (default: 50-99 by 1%)

        Returns:
            List of ThresholdAnalysis for each threshold
        """
        if not thresholds:
            thresholds = list(range(50, 100, 1))  # 50% to 99%

        analyses = []

        for threshold in thresholds:
            analysis = self._analyze_single_threshold(validation_results, threshold)
            analyses.append(analysis)

        return analyses

    def _analyze_single_threshold(
        self,
        validation_results: List[ValidationResult],
        threshold: float,
    ) -> ThresholdAnalysis:
        """Analyze performance at a single threshold"""
        tp = fp = tn = fn = 0
        deletions = 0
        total = len(validation_results)

        for result in validation_results:
            # Ground truth: is this actually promotional?
            is_promotional_actual = (result.actual_category == EmailCategory.PROMOTIONAL)

            # Prediction: would we delete this? (predicted promotional + meets threshold)
            is_promotional_predicted = (
                result.predicted_category == EmailCategory.PROMOTIONAL
                and result.confidence >= threshold
            )

            if is_promotional_predicted:
                deletions += 1

            # Calculate confusion matrix
            if is_promotional_actual and is_promotional_predicted:
                tp += 1
            elif not is_promotional_actual and is_promotional_predicted:
                fp += 1  # FALSE POSITIVE - CRITICAL ERROR
            elif not is_promotional_actual and not is_promotional_predicted:
                tn += 1
            elif is_promotional_actual and not is_promotional_predicted:
                fn += 1

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        deletion_rate = (deletions / total * 100) if total > 0 else 0.0

        return ThresholdAnalysis(
            threshold=threshold,
            precision=precision,
            recall=recall,
            f1_score=f1,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            deletion_rate=deletion_rate,
        )

    def plot_precision_recall_curve(
        self,
        analyses: List[ThresholdAnalysis],
        filename: str = "precision_recall_curve.png",
    ):
        """
        Plot precision-recall curve.

        Args:
            analyses: List of threshold analyses
            filename: Output filename
        """
        thresholds = [a.threshold for a in analyses]
        precisions = [a.precision for a in analyses]
        recalls = [a.recall for a in analyses]

        plt.figure(figsize=(10, 6))
        plt.plot(recalls, precisions, marker='o', linewidth=2, markersize=4)
        plt.xlabel('Recall (% of promotional emails deleted)', fontsize=12)
        plt.ylabel('Precision (% of deletions that are correct)', fontsize=12)
        plt.title('Precision-Recall Curve for Email Deletion', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Annotate key thresholds
        for threshold in [70, 80, 90, 95]:
            analysis = next((a for a in analyses if a.threshold == threshold), None)
            if analysis:
                plt.annotate(
                    f'{threshold}%',
                    (analysis.recall, analysis.precision),
                    textcoords="offset points",
                    xytext=(5, 5),
                    fontsize=9,
                )

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        print(f"Saved precision-recall curve to {filepath}")
        plt.close()

    def plot_f1_scores(
        self,
        analyses: List[ThresholdAnalysis],
        filename: str = "f1_scores.png",
    ):
        """
        Plot F1 scores across thresholds.

        Args:
            analyses: List of threshold analyses
            filename: Output filename
        """
        thresholds = [a.threshold for a in analyses]
        f1_scores = [a.f1_score for a in analyses]

        plt.figure(figsize=(10, 6))
        plt.plot(thresholds, f1_scores, marker='o', linewidth=2, markersize=4)
        plt.xlabel('Confidence Threshold (%)', fontsize=12)
        plt.ylabel('F1 Score', fontsize=12)
        plt.title('F1 Score vs. Confidence Threshold', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Mark optimal threshold
        optimal = max(analyses, key=lambda a: a.f1_score)
        plt.axvline(optimal.threshold, color='red', linestyle='--', alpha=0.5)
        plt.annotate(
            f'Optimal: {optimal.threshold}%\nF1={optimal.f1_score:.3f}',
            (optimal.threshold, optimal.f1_score),
            textcoords="offset points",
            xytext=(10, -10),
            fontsize=10,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
        )

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        print(f"Saved F1 score plot to {filepath}")
        plt.close()

    def plot_deletion_rate(
        self,
        analyses: List[ThresholdAnalysis],
        filename: str = "deletion_rate.png",
    ):
        """
        Plot deletion rate vs. threshold.

        Args:
            analyses: List of threshold analyses
            filename: Output filename
        """
        thresholds = [a.threshold for a in analyses]
        deletion_rates = [a.deletion_rate for a in analyses]

        plt.figure(figsize=(10, 6))
        plt.plot(thresholds, deletion_rates, marker='o', linewidth=2, markersize=4)
        plt.xlabel('Confidence Threshold (%)', fontsize=12)
        plt.ylabel('Deletion Rate (% of emails deleted)', fontsize=12)
        plt.title('Email Deletion Rate vs. Confidence Threshold', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Mark current threshold
        current = CONFIDENCE_THRESHOLDS[ConfidenceLevel.HIGH]
        plt.axvline(current, color='green', linestyle='--', alpha=0.5)
        plt.annotate(
            f'Current: {current}%',
            (current, max(deletion_rates) * 0.9),
            textcoords="offset points",
            xytext=(5, 0),
            fontsize=10,
        )

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        print(f"Saved deletion rate plot to {filepath}")
        plt.close()

    def find_optimal_threshold(
        self,
        analyses: List[ThresholdAnalysis],
        min_precision: float = 0.99,
    ) -> ThresholdAnalysis:
        """
        Find optimal threshold maximizing recall while maintaining minimum precision.

        Args:
            analyses: List of threshold analyses
            min_precision: Minimum acceptable precision (default 99% - very conservative)

        Returns:
            Optimal ThresholdAnalysis
        """
        # Filter to analyses meeting minimum precision
        valid_analyses = [a for a in analyses if a.precision >= min_precision]

        if not valid_analyses:
            print(f"WARNING: No threshold achieves {min_precision*100}% precision")
            print("Falling back to highest precision threshold")
            return max(analyses, key=lambda a: a.precision)

        # Among valid analyses, choose one with highest recall
        optimal = max(valid_analyses, key=lambda a: a.recall)

        return optimal

    def generate_report(
        self,
        analyses: List[ThresholdAnalysis],
        output_file: str = "threshold_analysis.txt",
    ):
        """
        Generate text report of threshold analysis.

        Args:
            analyses: List of threshold analyses
            output_file: Output filename
        """
        optimal_f1 = max(analyses, key=lambda a: a.f1_score)
        optimal_precision = self.find_optimal_threshold(analyses, min_precision=0.99)

        report = []
        report.append("=" * 80)
        report.append("CONFIDENCE THRESHOLD ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Optimal by F1 score
        report.append("OPTIMAL THRESHOLD (by F1 Score):")
        report.append(f"  Threshold: {optimal_f1.threshold}%")
        report.append(f"  Precision: {optimal_f1.precision*100:.2f}%")
        report.append(f"  Recall: {optimal_f1.recall*100:.2f}%")
        report.append(f"  F1 Score: {optimal_f1.f1_score:.3f}")
        report.append(f"  Deletion Rate: {optimal_f1.deletion_rate:.2f}%")
        report.append(f"  False Positives: {optimal_f1.false_positives}")
        report.append("")

        # Optimal by precision (safety-focused)
        report.append("RECOMMENDED THRESHOLD (99%+ Precision - Safety First):")
        report.append(f"  Threshold: {optimal_precision.threshold}%")
        report.append(f"  Precision: {optimal_precision.precision*100:.2f}%")
        report.append(f"  Recall: {optimal_precision.recall*100:.2f}%")
        report.append(f"  F1 Score: {optimal_precision.f1_score:.3f}")
        report.append(f"  Deletion Rate: {optimal_precision.deletion_rate:.2f}%")
        report.append(f"  False Positives: {optimal_precision.false_positives}")
        report.append("")

        # Key thresholds table
        report.append("THRESHOLD COMPARISON:")
        report.append(f"{'Threshold':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'FP':>6} {'Del%':>8}")
        report.append("-" * 70)

        for threshold in [70, 75, 80, 85, 90, 95, 99]:
            analysis = next((a for a in analyses if a.threshold == threshold), None)
            if analysis:
                report.append(
                    f"{analysis.threshold:>9}% "
                    f"{analysis.precision*100:>9.2f}% "
                    f"{analysis.recall*100:>9.2f}% "
                    f"{analysis.f1_score:>9.3f} "
                    f"{analysis.false_positives:>6} "
                    f"{analysis.deletion_rate:>7.2f}%"
                )

        report.append("")
        report.append("=" * 80)

        # Write to file
        filepath = os.path.join(self.output_dir, output_file)
        with open(filepath, 'w') as f:
            f.write('\n'.join(report))

        print(f"Saved threshold analysis report to {filepath}")

        # Also print to console
        print('\n'.join(report))

    def identify_false_positives(
        self,
        validation_results: List[ValidationResult],
        threshold: float,
    ) -> List[ValidationResult]:
        """
        Identify false positives at given threshold.

        Args:
            validation_results: Validation results
            threshold: Confidence threshold

        Returns:
            List of false positive results
        """
        false_positives = []

        for result in validation_results:
            is_promotional_actual = (result.actual_category == EmailCategory.PROMOTIONAL)
            is_promotional_predicted = (
                result.predicted_category == EmailCategory.PROMOTIONAL
                and result.confidence >= threshold
            )

            # False positive: predicted promotional, actually not
            if is_promotional_predicted and not is_promotional_actual:
                false_positives.append(result)

        return false_positives

    def save_validation_results(
        self,
        validation_results: List[ValidationResult],
        filename: str = "validation_results.json",
    ):
        """Save validation results to JSON for later analysis"""
        data = [
            {
                "email_id": r.email_id,
                "predicted_category": r.predicted_category.value,
                "actual_category": r.actual_category.value,
                "confidence": r.confidence,
                "from_address": r.from_address,
                "subject": r.subject,
            }
            for r in validation_results
        ]

        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Saved validation results to {filepath}")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Create synthetic validation data for testing
    np.random.seed(42)

    validation_results = []

    # True promotional emails (should be deleted)
    for i in range(100):
        confidence = np.random.beta(8, 2) * 100  # Skewed toward high confidence
        validation_results.append(
            ValidationResult(
                email_id=f"promo_{i}",
                predicted_category=EmailCategory.PROMOTIONAL,
                actual_category=EmailCategory.PROMOTIONAL,
                confidence=confidence,
                from_address="marketing@shop.com",
                subject="Sale! 50% off",
            )
        )

    # True non-promotional emails (should NOT be deleted)
    for i in range(100):
        # Most correctly classified as non-promotional
        if i < 95:
            validation_results.append(
                ValidationResult(
                    email_id=f"nonpromo_{i}",
                    predicted_category=EmailCategory.PERSONAL_HUMAN,
                    actual_category=EmailCategory.PERSONAL_HUMAN,
                    confidence=np.random.beta(6, 2) * 100,
                    from_address="friend@email.com",
                    subject="Catch up soon?",
                )
            )
        # A few false positives (DANGER)
        else:
            validation_results.append(
                ValidationResult(
                    email_id=f"fp_{i}",
                    predicted_category=EmailCategory.PROMOTIONAL,
                    actual_category=EmailCategory.PERSONAL_HUMAN,
                    confidence=np.random.uniform(70, 85),  # Medium confidence
                    from_address="alerts@zerodha.com",
                    subject="Dividend credited",
                )
            )

    # Run analysis
    print("Running Confidence Threshold Analysis...")
    print("=" * 80)

    analyzer = ConfidenceAnalyzer()

    # Analyze thresholds
    analyses = analyzer.analyze_thresholds(validation_results)

    # Generate plots
    analyzer.plot_precision_recall_curve(analyses)
    analyzer.plot_f1_scores(analyses)
    analyzer.plot_deletion_rate(analyses)

    # Generate report
    analyzer.generate_report(analyses)

    # Find false positives at 90% threshold
    false_positives = analyzer.identify_false_positives(validation_results, threshold=90)
    print(f"\nFalse Positives at 90% threshold: {len(false_positives)}")
    for fp in false_positives:
        print(f"  - {fp.from_address}: {fp.subject} (confidence: {fp.confidence:.1f}%)")

    # Save results
    analyzer.save_validation_results(validation_results)

    print("\n" + "=" * 80)
    print("Analysis complete! Check the 'plots' directory for visualizations.")
