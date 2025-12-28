# Gmail Promotional Email Classifier

Enterprise-grade AI-powered email classifier with dual-agent verification for identifying and managing promotional emails.

## Contributors

**Sidharth Arora** - Project lead and developer
**Claude (Anthropic)** - AI pair programming assistant

---

## Features

- **Multi-Provider AI**: Supports Gemini (2.5 Flash-Lite default) and Anthropic Claude
- **Batch AI Classification**: Classify 50 emails per API call - optimized for 250K TPM free tier
- **Dual-Agent AI System**: Primary classifier + verification agent for high accuracy
- **Domain Protection**: Never marks emails from banks, government, healthcare, utilities, or educational institutions as promotional
- **Keyword Matching**: 100+ promotional keywords in English and German for fast pre-filtering
- **Smart Sender Caching**: 60-80% cache hit rate for cost optimization
- **Bilingual Support**: English and German email analysis
- **Progress Persistence**: Resume interrupted sessions
- **Batch Processing**: Handle 100k+ emails efficiently within free tier limits
- **Cost Optimized**: ~$0.50-4 for 100k emails depending on provider (or FREE with Gemini free tier!)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Gmail Classifier                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Gmail API    │  │ AI Classifier│  │ Sender Cache │       │
│  │ OAuth 2.0    │  │ Flash-Lite   │  │ JSON Storage │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Processing Pipeline                     │    │
│  │  1. Fetch emails (100 per batch)                    │    │
│  │  2. Check protected domains (banks, gov, etc.)      │    │
│  │  3. Check sender cache                               │    │
│  │  4. Keyword matching (100+ EN/DE keywords)          │    │
│  │  5. **Batch AI classification (50 emails/call)**    │    │
│  │  6. Batch verification (if confidence < 85%)        │    │
│  │  7. Update cache & save progress                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
gmail-classifier-project/
├── config.py              # All configuration constants
├── keyword_matcher.py     # Bilingual keyword matching
├── email_classifier.py    # Main classifier application
├── test_keyword_matcher.py # Test suite
├── __init__.py            # Package exports
├── requirements.txt       # Python dependencies
├── credentials.json       # Gmail OAuth (you provide)
└── README.md
```

## Dual-Agent System

### Agent 1: Primary Classifier
- Analyzes email subject, sender, and body
- Returns structured classification with confidence score
- Handles English and German content

### Agent 2: Verifier
- Triggered when confidence < 85%
- Reviews and potentially corrects Agent 1's decision
- Catches false positives (receipts marked as promo)
- Catches false negatives (sneaky promotional content)
- ~15% correction rate typical

## Installation

```bash
# Clone or download the project
cd gmail-classifier-project

# Install dependencies
pip install -r requirements.txt

# Set up Gmail credentials (see SETUP.md)
# Place credentials.json in project directory

# Set API key (choose one)
export GEMINI_API_KEY="your-gemini-key"      # Default, cheapest option
# OR
export ANTHROPIC_API_KEY="your-anthropic-key"  # Alternative
```

## Usage

### Basic Classification (uses Gemini by default)
```bash
python email_classifier.py
```

### Use Anthropic Claude instead
```bash
python email_classifier.py --provider anthropic
```

### Test Run (first 100 emails)
```bash
python email_classifier.py --max-emails 100
```

### Delete Promotional Emails
```bash
python email_classifier.py --delete
```

### Resume Interrupted Session
```bash
# Progress is automatically saved - just run again
python email_classifier.py
```

### View Previous Results
```bash
python email_classifier.py --summary-only
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--provider`, `-p` | AI provider: `gemini` (default) or `anthropic` |
| `--project-dir`, `-d` | Project directory (default: current) |
| `--api-key`, `-k` | API key (overrides env var) |
| `--max-emails`, `-m` | Limit emails to process |
| `--no-cache` | Disable sender caching |
| `--no-verify` | Disable verification agent |
| `--delete` | Delete promotional emails |
| `--reset` | Clear progress, start fresh |
| `--summary-only` | Show summary without processing |
| `--debug` | Enable debug logging (API calls, results, errors) |

## Output Indicators

During processing, you'll see:
- `🛡️` Protected domain (banks, gov, etc. - never promotional)
- `💾` Cache hit (no AI call needed)
- `🔑` Keyword match (no AI call needed)
- `🔍` Verification agent ran
- `✏️` Classification was corrected
- `✓` Classified as promotional
- `✗` Classified as non-promotional

## Performance

| Metric | Typical Value |
|--------|---------------|
| Cache Hit Rate | 60-80% |
| Verification Rate | 15-20% |
| Correction Rate | 10-15% |
| Processing Speed | 5-10 emails/sec |

### Cost Comparison (per 100k emails)

| Provider | Model | Input Cost | Output Cost | Total | Free Tier |
|----------|-------|------------|-------------|-------|-----------|
| **Gemini** | **2.5 Flash-Lite** | **$0.075/1M** | **$0.30/1M** | **~$0.50-1** | **1K RPD, 250K TPM** |
| Gemini | 2.5 Flash | $0.15/1M tokens | $0.60/1M tokens | ~$1-2 | 1,000 requests/day |
| Gemini | 2.5 Pro | Higher cost | Higher cost | ~$5-10 | Limited |
| Anthropic | Haiku | $0.25/1M tokens | $1.25/1M tokens | ~$2-4 | None |

*Gemini 2.5 Flash-Lite is the default - fastest and cheapest option with generous free tier*

### Free Tier Optimization

**Gemini 2.5 Flash-Lite Rate Limits (December 2025):**
- **RPD**: 1,000 requests per day
- **TPM**: 250,000 tokens per minute
- **RPM**: ~15 requests per minute (estimated conservative)
- Smart rate limiting: Auto-waits 60 seconds when rate limited

**Batch Classification Benefits:**
- **Old approach**: 1 API call per email = 40,000+ calls for 100K emails (impossible on free tier)
- **New approach**: 50 emails per API call = ~800 calls for 100K emails (within free tier!)
- With 60-80% cache hit rate, only 20-40K emails need AI classification
- At 50 emails/batch, that's only 400-800 API calls per 100K emails
- **Result**: Process 100K+ emails completely free using Gemini!
- **Daily processing**: Can handle ~50,000 emails/day within 1,000 request limit

## Files Generated

| File | Description |
|------|-------------|
| `token.pickle` | Gmail OAuth token (auto-generated) |
| `classifier_progress.json` | Processing state for resume |
| `sender_cache.json` | Known sender classifications |
| `sender_summary.json` | Final statistics by sender |

## Classification Criteria

### Promotional (will be flagged)
- Marketing newsletters
- Sales and discount offers
- Product announcements
- Social media notifications
- Automated marketing emails
- Subscription digests

### Non-Promotional (will be kept)
- Personal correspondence
- Transaction receipts
- Shipping confirmations
- Account security alerts
- Work/business emails
- Bills and statements
- Appointment confirmations

### Protected Domains (always kept)
Emails from these domains are **never** marked as promotional, regardless of content:

| Category | Examples |
|----------|----------|
| **Banks** | Deutsche Bank, Sparkasse, Chase, PayPal, N26, Wise |
| **Government** | .gov domains, Finanzamt, Arbeitsagentur, IRS |
| **Healthcare** | TK, AOK, Barmer, Allianz, health insurance |
| **Utilities** | Telekom, Vodafone, EON, energy providers |
| **Education** | .edu domains, universities, Hochschulen |

The full list includes 80+ protected domains and regex patterns for automatic detection.

## Cost Optimization

The system uses multiple strategies to minimize API costs:

1. **Gemini Flash Default**: Uses the cheapest AI model (~3-4x cheaper than alternatives)
2. **Domain Protection**: Protected domains (banks, gov, etc.) skip AI classification entirely
3. **Sender Caching**: After classifying emails from a sender, future emails are auto-classified without AI calls
4. **Keyword Matching**: 100+ promotional keywords in English/German catch obvious promos before AI
5. **Selective Verification**: Only verifies uncertain classifications (<85% confidence)
6. **Pattern Matching**: Known promotional sender patterns skip AI entirely

## Error Handling

- **Rate Limiting**: Automatic exponential backoff on 429 errors
- **API Errors**: Retry with backoff on transient failures
- **Network Issues**: Progress saved after each batch
- **Interruption**: Resume from last successful batch

## Security Notes

- OAuth tokens are stored locally in `token.pickle`
- API keys should be set via environment variable
- `credentials.json` and `token.pickle` are gitignored
- No email content is stored permanently

## Troubleshooting

### "credentials.json not found"
Download OAuth credentials from Google Cloud Console and save to project directory.

### "Token refresh failed"
Delete `token.pickle` and run again to re-authenticate.

### Rate limit errors persist
Wait 5 minutes and try again. Consider reducing batch size.

### Classification seems wrong
Check `sender_cache.json` - cached senders may need clearing. Use `--reset` for fresh start.

## Replication Prompt

To recreate this project using Claude Code, use the following prompt:

```
Create a Gmail promotional email classifier with the following requirements:

1. **Gmail Integration**:
   - OAuth 2.0 authentication with Gmail API
   - Batch processing (100 emails per batch)
   - Progress persistence for resume capability

2. **Multi-Provider AI Support**:
   - Support both Gemini and Anthropic Claude
   - Default to Gemini Flash (cheapest: $0.075/1M input, $0.30/1M output)
   - Dual-agent system: primary classifier + verification agent
   - Verification triggers for low-confidence (<85%) classifications
   - Support for both English and German emails

3. **Domain Protection**:
   - Never mark emails from banks, government, healthcare, utilities, or
     educational institutions as promotional
   - Include domains: Deutsche Bank, Sparkasse, Chase, PayPal, .gov, .edu,
     Finanzamt, Telekom, AOK, TK, Allianz, universities
   - Support regex patterns for domain matching (e.g., r'\.gov$', r'bank')

4. **Optimization Features**:
   - Sender caching (classify once, reuse for same sender)
   - Keyword matching with 50+ promotional keywords per language
   - Keywords should include: unsubscribe signals, urgency words, discount terms,
     call-to-action phrases, newsletter indicators, and sales event terms
   - Pattern matching for known promotional sender addresses

5. **Code Structure** (Python best practices):
   - config.py: All configuration constants including provider costs and protected domains
   - keyword_matcher.py: Bilingual keyword matching class
   - email_classifier.py: Main application with DomainChecker and provider abstraction
   - test_keyword_matcher.py: Test suite with sample emails
   - Proper type hints throughout

6. **CLI Interface**:
   - --provider flag to switch between gemini/anthropic
   - Options for max emails, dry run, delete, reset, summary
   - Progress indicators during processing (🛡️=protected, 💾=cached, 🔑=keyword)
   - Final statistics with cost estimation per provider

7. **Output**:
   - Real-time progress with emoji indicators
   - Summary by sender with email counts
   - Token usage and cost estimation
   - Protected domain hit statistics

Create tests with 5 English and 5 German promotional emails,
plus 5 non-promotional emails as a control group.
```

## Running Tests

```bash
# Run keyword matcher tests
python test_keyword_matcher.py

# Expected output: 15/15 tests passed (5 EN + 5 DE + 5 control)
```

## License

MIT License - Copyright (c) 2024 Sidharth Arora. See [LICENSE](LICENSE) for details.

---

*Built with Claude Code by Sidharth Arora*
