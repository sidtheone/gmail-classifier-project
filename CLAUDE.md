# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gmail promotional email classifier with AI-powered dual-agent verification and batch processing. Classifies promotional vs. non-promotional emails using a multi-stage pipeline: protected domain check → sender cache → keyword matching → **batch AI classification** (50 emails/call) → batch verification. Optimized for Gemini 2.5 Flash-Lite (1K RPD, 250K TPM) with 60s rate limit backoff.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run classifier (uses Gemini by default)
python email_classifier.py

# Use Anthropic Claude instead
python email_classifier.py --provider anthropic

# Test run with limited emails
python email_classifier.py --max-emails 100

# Enable debug logging
python email_classifier.py --debug

# Run keyword matcher tests
python test_keyword_matcher.py
```

## Architecture

```
email_classifier.py    # Main application - all core classes
├── DomainChecker      # Protected domain detection (banks, gov, healthcare)
├── GmailService       # Gmail API OAuth and operations
├── EmailParser        # Email content extraction
├── SenderCache        # Classification cache (JSON persistence)
├── AIClassifier       # Dual-agent AI system (Gemini/Anthropic)
├── ProgressTracker    # Resume capability and results tracking
└── GmailClassifier    # Main orchestrator

config.py              # All configuration constants
├── AI provider settings (GEMINI_MODEL='gemini-2.5-flash-lite', ANTHROPIC_MODEL)
├── Batch processing (BATCH_SIZE=100, AI_BATCH_SIZE=50)
├── Rate limits (1K RPD, 250K TPM, ~15 RPM, 60s backoff)
├── Protected domains (100+ banks, gov, healthcare, utilities, education incl. India)
├── Promotional keywords (100+ English and German)
└── Thresholds and verification settings

keyword_matcher.py     # Bilingual keyword matching class
```

## Key Processing Pipeline

1. **Protected domains** (🛡️) - Banks, government, healthcare never marked promotional
2. **Sender cache** (💾) - Reuse prior classifications for known senders
3. **Keyword matching** (🔑) - 100+ EN/DE keywords with threshold check
4. **Batch AI classification** (✓/✗) - Classify 50 emails per API call (optimized for 250K TPM)
5. **Batch verification** (🔍/✏️) - Verify low-confidence (<85%) classifications in batch

**Rate Limiting**: Gemini 2.5 Flash-Lite has generous limits (1K RPD, 250K TPM). The system:
- Tracks tokens and requests per minute/day
- Auto-waits when approaching limits
- Waits 60 seconds when rate limited (429 errors)
- Processes 400-800 batches for 100K emails

**Free Tier**: With batch processing (50 emails/call) and 60-80% cache hit rate, can process 100K+ emails completely free within the 1,000 requests/day limit!

## Environment Variables

```bash
GEMINI_API_KEY      # For Gemini (default provider)
ANTHROPIC_API_KEY   # For Anthropic Claude
```

## Generated Files

- `token.pickle` - Gmail OAuth token
- `credentials.json` - Gmail OAuth credentials (user-provided)
- `sender_cache.json` - Sender classification cache
- `classifier_progress.json` - Processing state for resume
- `sender_summary.json` - Final results by sender
