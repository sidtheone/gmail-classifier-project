# Gmail Promotional Email Classifier

Enterprise-grade AI-powered email classifier with dual-agent verification for identifying and managing promotional emails.

## Contributors

**Sidharth Arora** - Project lead and developer
**Claude (Anthropic)** - AI pair programming assistant

---

## Features

- **Dual-Agent AI System**: Primary classifier + verification agent for high accuracy
- **Keyword Matching**: 100+ promotional keywords in English and German for fast pre-filtering
- **Smart Sender Caching**: 60-80% cache hit rate for cost optimization
- **Bilingual Support**: English and German email analysis
- **Progress Persistence**: Resume interrupted sessions
- **Batch Processing**: Handle 100k+ emails efficiently
- **Cost Optimized**: ~$2-4 for 100k emails using Claude Haiku

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Gmail Classifier                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Gmail API    │  │ AI Classifier│  │ Sender Cache │       │
│  │ OAuth 2.0    │  │ Claude Haiku │  │ JSON Storage │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Processing Pipeline                     │    │
│  │  1. Fetch emails (100 per batch)                    │    │
│  │  2. Check sender cache                               │    │
│  │  3. Keyword matching (100+ EN/DE keywords)          │    │
│  │  4. AI classification (if not cached/matched)       │    │
│  │  5. Verification (if confidence < 85%)              │    │
│  │  6. Update cache & save progress                    │    │
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

# Set up credentials (see SETUP.md)
# Place credentials.json in project directory

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Basic Classification
```bash
python email_classifier.py
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
| `--project-dir`, `-d` | Project directory (default: current) |
| `--api-key`, `-k` | Anthropic API key |
| `--max-emails`, `-m` | Limit emails to process |
| `--no-cache` | Disable sender caching |
| `--no-verify` | Disable verification agent |
| `--delete` | Delete promotional emails |
| `--reset` | Clear progress, start fresh |
| `--summary-only` | Show summary without processing |

## Output Indicators

During processing, you'll see:
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
| Cost per 100k emails | $2-4 |

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

## Cost Optimization

The system uses multiple strategies to minimize API costs:

1. **Sender Caching**: After classifying emails from a sender, future emails are auto-classified without AI calls
2. **Keyword Matching**: 100+ promotional keywords in English/German catch obvious promos before AI
3. **Claude Haiku**: Uses the most cost-effective model (20x cheaper than Sonnet)
4. **Selective Verification**: Only verifies uncertain classifications (<85% confidence)
5. **Pattern Matching**: Known promotional sender patterns skip AI entirely

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

2. **Classification System**:
   - Dual-agent AI system using Claude Haiku
   - Primary classifier with confidence scoring
   - Verification agent for low-confidence (<85%) classifications
   - Support for both English and German emails

3. **Optimization Features**:
   - Sender caching (classify once, reuse for same sender)
   - Keyword matching with 50+ promotional keywords per language
   - Keywords should include: unsubscribe signals, urgency words, discount terms,
     call-to-action phrases, newsletter indicators, and sales event terms
   - Pattern matching for known promotional sender addresses

4. **Code Structure** (Python best practices):
   - config.py: All configuration constants
   - keyword_matcher.py: Bilingual keyword matching class
   - email_classifier.py: Main application
   - test_keyword_matcher.py: Test suite with sample emails
   - Proper type hints throughout

5. **CLI Interface**:
   - Options for max emails, dry run, delete, reset, summary
   - Progress indicators during processing
   - Final statistics with cost estimation

6. **Output**:
   - Real-time progress with emoji indicators
   - Summary by sender with email counts
   - Token usage and cost estimation

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
