# Makefile for Gmail Email Classifier

.PHONY: help install test run-dry run-delete clean setup

help:
	@echo "Gmail Email Classifier - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete setup (venv + dependencies + .env)"
	@echo "  make install        - Install Python dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run comprehensive test suite"
	@echo "  make test-domains   - Test domain checker"
	@echo "  make test-gates     - Test decision engine gates"
	@echo ""
	@echo "Classification:"
	@echo "  make run-dry        - Dry run (no deletion, 50 emails)"
	@echo "  make run-delete     - Delete approved emails (high confidence only)"
	@echo "  make run-unread     - Process unread emails only"
	@echo ""
	@echo "Analysis:"
	@echo "  make analyze        - Generate precision-recall analysis"
	@echo "  make review         - Review flagged emails (interactive)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean generated files"
	@echo "  make auth           - Test Gmail authentication"
	@echo ""

setup:
	@echo "Setting up Gmail Email Classifier..."
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file - please add your API keys"; \
	fi
	@echo "Setup complete! Next steps:"
	@echo "1. Add API keys to .env file"
	@echo "2. Download credentials.json from Google Cloud Console"
	@echo "3. Run: make auth"

install:
	pip install -r requirements.txt

test:
	@echo "Running comprehensive test suite..."
	python test_decision_engine.py -v

test-domains:
	@echo "Testing domain checker..."
	python domain_checker.py

test-gates:
	@echo "Testing decision engine gates..."
	python decision_engine.py

run-dry:
	@echo "Running dry-run classification (no deletion)..."
	python email_classifier.py --max-emails 50

run-delete:
	@echo "WARNING: This will delete emails (move to trash)"
	@read -p "Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		python email_classifier.py --delete-high-confidence --max-emails 100; \
	else \
		echo "Cancelled"; \
	fi

run-unread:
	@echo "Processing unread emails (dry-run)..."
	python email_classifier.py --query "is:unread" --max-emails 200

analyze:
	@echo "Generating precision-recall analysis..."
	python confidence_analyzer.py

review:
	@echo "Starting human review workflow..."
	@latest=$$(ls -t classification_results/classification_results_*.json | head -1); \
	if [ -n "$$latest" ]; then \
		python review_workflow.py $$latest; \
	else \
		echo "No classification results found. Run 'make run-dry' first."; \
	fi

auth:
	@echo "Testing Gmail authentication..."
	python gmail_client.py

clean:
	@echo "Cleaning generated files..."
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf plots/*.png
	rm -rf classification_results/*.json
	@echo "Clean complete!"

# Development targets
dev-install:
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8

format:
	black *.py

lint:
	flake8 *.py --max-line-length=100

# Market-specific runs
run-usa:
	python email_classifier.py --market usa --language en --max-emails 50

run-india:
	python email_classifier.py --market india --language en --max-emails 50

run-germany:
	python email_classifier.py --market germany --language both --max-emails 50
