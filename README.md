# Gmail 5-Category Email Classifier

Enterprise-grade AI-powered email classifier with safety-first deletion logic, dual-agent verification, and 5-category classification system.

## Contributors

**Sidharth Arora** - Project lead and developer
**Claude (Anthropic)** - AI pair programming assistant

---

## Features

- **5-Category Classification**: Promotional, Transactional, System/Security, Social/Platform, Personal/Human
- **Safety-First Architecture**: 5 mandatory deletion criteria - ALL must be met before any email is deleted
- **Multi-Provider AI**: Supports Gemini (2.5 Flash-Lite default) and Anthropic Claude
- **High-Throughput Batch Processing**: Classify 200 emails per API call - optimized for 4M TPM paid tier
- **Mandatory Verification for Promotional**: Every promotional email gets dual-agent verification before deletion consideration
- **Investment Platform Protection**: 64+ investment/brokerage domains (Zerodha, Groww, SBIMF, Schwab, Fidelity, etc.) - NEVER deleted
- **Domain Protection**: Banks, government, healthcare, utilities, education - automatically classified as Personal/Human
- **Manual Flag Safety**: Starred/Important emails NEVER deleted regardless of AI confidence
- **Decision Engine**: Tracks blocking factors (category, verification, confidence, domain, flags)
- **Fresh Classification Mode**: Cache disabled - every email classified fresh for complete audit trail
- **Progress Persistence**: Resume interrupted sessions with full audit history
- **Cost Optimized**: ~$1.35-2.03 per 100K emails with 4M TPM (30-40 minutes processing time)

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              Gmail 5-Category Classifier (Safety-First)           │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │ Gmail API    │  │ AI Classifier│  │ Decision Engine  │        │
│  │ OAuth 2.0    │  │ Flash-Lite   │  │ 5 Safety Checks  │        │
│  └──────────────┘  └──────────────┘  └──────────────────┘        │
│         │                 │                    │                  │
│         ▼                 ▼                    ▼                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Processing Pipeline                          │    │
│  │  1. Fetch emails (100 per Gmail API batch)               │    │
│  │  2. Check protected domains (banks, gov, investment)     │    │
│  │  3. **Batch AI classification (200 emails/call)**        │    │
│  │     → 5 categories: Promotional, Transactional,          │    │
│  │       System/Security, Social/Platform, Personal/Human   │    │
│  │  4. **Mandatory verification for ALL promotional**       │    │
│  │     → Dual-agent verification (catch false positives)    │    │
│  │  5. Decision Engine evaluates 5 deletion criteria:       │    │
│  │     ✓ Category = Promotional                             │    │
│  │     ✓ Verified = True                                    │    │
│  │     ✓ Confidence ≥ 90%                                   │    │
│  │     ✓ NOT protected domain                               │    │
│  │     ✓ NOT starred/important                              │    │
│  │  6. Save progress & audit trail (ALL emails logged)      │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
gmail-classifier-project/
├── config.py                  # Configuration: TPM=4M, 64 investment domains
├── decision_engine.py         # Safety-first deletion logic (5 criteria)
├── domain_checker.py          # Protected domain detection
├── gmail_client.py            # Gmail API operations + manual flag check
├── email_classifier.py        # Main 5-category classifier (batch AI)
├── keyword_matcher.py         # Bilingual keyword matching (optional)
├── test_decision_engine.py    # Decision engine test suite (8 tests)
├── test_keyword_matcher.py    # Keyword matcher tests
├── requirements.txt           # Python dependencies
├── credentials.json           # Gmail OAuth (you provide)
├── REFACTORING_SUMMARY.md     # Safety-first refactoring details
├── NO_CACHE_UPDATE.md         # Fresh classification mode details
└── README.md
```

## Dual-Agent System

### Agent 1: Primary Classifier (Batch Processing)
- Analyzes email subject, sender, and body preview
- Classifies into 5 categories with confidence score (0-100%)
- Processes 200 emails per API call for efficiency
- Categories: Promotional, Transactional, System/Security, Social/Platform, Personal/Human

### Agent 2: Verifier (Mandatory for Promotional)
- **ALWAYS triggered for promotional emails** (safety-first)
- Also triggered for low-confidence (<85%) classifications in other categories
- Reviews and potentially corrects Agent 1's decision
- **CRITICAL**: Catches investment platform misclassifications (Zerodha, Groww, SBIMF, etc.)
- Catches transactional emails mistaken for promotional (receipts, shipping confirmations)
- Batch verification (multiple emails per API call)
- ~10-15% correction rate typical

### 5 Deletion Criteria (ALL must be true)

Even if AI classifies an email as promotional with 99% confidence, it will NOT be deleted unless:

1. ✓ **Category = Promotional** (not transactional, system, social, or personal)
2. ✓ **Verified = True** (dual-agent verification completed)
3. ✓ **Confidence ≥ 90%** (high confidence threshold)
4. ✓ **NOT protected domain** (banks, investment, government, healthcare, etc.)
5. ✓ **NOT starred/important** (user manual flags respected)

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
- `🛡️` Protected domain (banks, gov, investment - classified as Personal/Human, bypass AI)
- `🔍` Verification agent ran (mandatory for promotional, optional for low-confidence)
- `✏️` Classification was corrected by verifier
- `✓` Classified as promotional
- `✗` Classified as non-promotional (transactional, system, social, or personal)

**Note**: Cache and keyword matching disabled - every email gets fresh AI classification for complete audit trail.

## Performance

| Metric | Typical Value |
|--------|---------------|
| Batch Size | 200 emails/API call |
| Protected Domain Rate | 10-20% (bypass AI entirely) |
| Verification Rate | 100% for promotional + 15-20% for others |
| Correction Rate | 10-15% of verified emails |
| Processing Speed | 3,000-4,000 emails/minute (theoretical) |
| Processing Time (100K) | 30-40 minutes |

### Cost Comparison (per 100k emails)

**With 4M TPM Paid Tier:**

| Provider | Model | Input Cost | Output Cost | Total Cost | Processing Time |
|----------|-------|------------|-------------|------------|-----------------|
| **Gemini** | **2.5 Flash-Lite** | **$0.075/1M** | **$0.30/1M** | **~$1.35-2.03** | **30-40 min** |
| Gemini | 2.5 Flash | $0.15/1M tokens | $0.60/1M tokens | ~$2.70-4.06 | 30-40 min |
| Anthropic | Haiku | $0.25/1M tokens | $1.25/1M tokens | ~$4.50-6.75 | 30-40 min |

*Fresh classification mode: No cache means more API calls, but 4M TPM handles 100K emails in 30-40 minutes*

### Paid Tier Configuration (4M TPM)

**Gemini 2.5 Flash-Lite Rate Limits:**
- **TPM**: 4,000,000 tokens per minute (16x free tier)
- **RPM**: 60 requests per minute (4x free tier)
- **RPD**: 10,000 requests per day (10x free tier)
- **Batch size**: 200 emails per API call (4x larger than free tier)
- **API delay**: 0.1s between calls (5x faster)

**Processing Capacity:**
- **Theoretical**: 3,000-4,000 emails/minute
- **100K emails**: ~30-40 minutes
- **Daily capacity**: Can process 500K-1M emails/day
- **No cache needed**: Fresh classification for complete audit trail

## Files Generated

| File | Description |
|------|-------------|
| `token.pickle` | Gmail OAuth token (auto-generated) |
| `classifier_progress.json` | Processing state for resume |
| `sender_cache.json` | Known sender classifications |
| `sender_summary.json` | Final statistics by sender |

## 5-Category Classification System

### 1. Promotional (deletion candidates)
- Marketing newsletters and campaigns
- Sales, discounts, and promotional offers
- Product announcements and launches
- Marketing automation emails
- Subscription digests and weekly roundups
- **Only category eligible for deletion** (with verification + 90% confidence)

### 2. Transactional (always kept)
- Purchase receipts and invoices
- Shipping and delivery confirmations
- Payment confirmations
- Booking confirmations (travel, restaurants, events)
- Order status updates

### 3. System/Security (always kept)
- Password reset requests
- Security alerts and notifications
- Two-factor authentication codes
- Account activity notifications
- Login alerts from new devices
- Account settings changes

### 4. Social/Platform (always kept)
- Social network notifications (LinkedIn, Twitter, Facebook)
- Friend requests and connection invitations
- Comments, mentions, and tags
- Platform updates and features
- Community activity notifications

### 5. Personal/Human (always kept)
- Direct human correspondence
- Work/business emails from colleagues
- Personal conversations
- Meeting invites and scheduling
- Project collaboration emails

### Protected Domains (always kept)
Emails from these domains are **automatically classified as Personal/Human** and bypass AI entirely:

| Category | Examples |
|----------|----------|
| **Banks** | Deutsche Bank, Sparkasse, Chase, PayPal, N26, Wise, HDFC, ICICI |
| **Investment Platforms** | **Zerodha, Groww, Upstox, Schwab, Fidelity, Vanguard, Robinhood** |
| **Mutual Funds** | **SBIMF, AxisMF, HDFC Fund, ICICI Pru AMC, Mirae Asset** |
| **Fund Registrars** | **KFintech, CAMS, Karvy** |
| **Stock Exchanges** | **NSE, BSE, NASDAQ, NYSE** |
| **Crypto Exchanges** | Coinbase, Kraken, Binance, Gemini |
| **Government** | .gov domains, Finanzamt, Arbeitsagentur, IRS |
| **Healthcare** | TK, AOK, Barmer, Allianz, health insurance |
| **Utilities** | Telekom, Vodafone, EON, energy providers |
| **Education** | .edu domains, universities, Hochschulen |

The full list includes **180+ protected domains** (64 investment platforms added) with regex patterns for automatic detection.

## Safety and Audit Features

The system prioritizes safety and complete audit trails over cost optimization:

1. **Protected Domains First**: 180+ domains (banks, investment, gov, healthcare, utilities, edu) bypass AI entirely
2. **Fresh Classification Every Time**: Cache disabled - every email gets fresh AI classification for consistent audit trail
3. **Mandatory Verification for Promotional**: Every promotional email gets dual-agent verification before deletion consideration
4. **5 Deletion Criteria**: ALL must be true - category, verification, confidence ≥90%, not protected, not starred
5. **Manual Flag Protection**: Starred/Important emails NEVER deleted regardless of AI classification
6. **Complete Audit Trail**: Every email logged with AI reasoning, confidence, and deletion decision
7. **High-Throughput Processing**: 4M TPM + 200 batch size = 30-40 min for 100K emails despite no cache

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
Create a safety-first Gmail email classifier with 5-category classification and mandatory
deletion criteria. This is a high-stakes system that must NEVER delete important emails
(banks, investment platforms, starred emails).

## Core Requirements

### 1. Gmail Integration
- OAuth 2.0 authentication with Gmail API
- Batch fetching (100 emails per Gmail API batch)
- Progress persistence for resume capability
- Manual flag detection (STARRED, IMPORTANT labels)

### 2. 5-Category Classification System
Classify emails into these categories:
- **PROMOTIONAL**: Marketing, newsletters, sales, discounts (ONLY category eligible for deletion)
- **TRANSACTIONAL**: Receipts, shipping confirmations, payment confirmations
- **SYSTEM_SECURITY**: Password resets, 2FA codes, security alerts
- **SOCIAL_PLATFORM**: Social network notifications, friend requests, mentions
- **PERSONAL_HUMAN**: Direct correspondence, work emails, personal messages

### 3. AI Classification (Batch Processing)
- Support Gemini (default) and Anthropic Claude
- Default: Gemini 2.5 Flash-Lite with 4M TPM (paid tier)
- **Batch size: 200 emails per API call**
- Rate limiting: 4M TPM, 60 RPM, 10K RPD
- Dual-agent system:
  * Agent 1: Primary classifier (batch classify 200 emails)
  * Agent 2: Verifier (MANDATORY for ALL promotional emails)
  * Also verify low-confidence (<85%) classifications for other categories

### 4. CRITICAL: Protected Domains (180+ domains)
**Investment Platforms (64 domains) - HIGHEST PRIORITY:**
- Indian: Zerodha, Groww, Upstox, ICICIDIRECT, 5paisa, AngelOne, Kotak Securities,
  HDFC Securities, SBI Smart, Axis Direct, Motilal Oswal
- Mutual Funds: SBIMF, AxisMF, HDFC Fund, ICICI Pru AMC, Mirae Asset, DSP, PPFAS,
  Value Research
- Fund Registrars: KFintech, CAMS, Karvy
- US: Schwab, Fidelity, Vanguard, E*TRADE, Robinhood, Interactive Brokers,
  TD Ameritrade
- Crypto: Coinbase, Kraken, Binance, Gemini, Crypto.com
- Exchanges: NSE, BSE, NASDAQ, NYSE

**Other Protected Categories:**
- Banks: Deutsche Bank, Sparkasse, Chase, PayPal, N26, Wise, HDFC, ICICI, SBI
- Government: .gov domains, Finanzamt, IRS, Arbeitsagentur
- Healthcare: TK, AOK, Barmer, Allianz, health insurance
- Utilities: Telekom, Vodafone, EON, energy providers
- Education: .edu domains, universities

Protected domains bypass AI classification entirely and are marked as PERSONAL_HUMAN.

### 5. CRITICAL: 5 Mandatory Deletion Criteria (DecisionEngine)
Create a DecisionEngine class that evaluates ALL 5 criteria.
Email is ONLY approved for deletion if ALL are true:

1. ✓ Category == PROMOTIONAL (not transactional, system, social, or personal)
2. ✓ Verified == True (dual-agent verification completed)
3. ✓ Confidence >= 90% (high confidence threshold)
4. ✓ NOT protected domain (banks, investment, government, healthcare, etc.)
5. ✓ NOT starred/important (user manual flags)

Even if AI says "promotional with 99% confidence", if ANY criterion fails,
email is NOT deleted.

The DecisionEngine should return:
- should_delete: bool
- reasons: List[str] (why it should be deleted)
- blocks: List[str] (why it should NOT be deleted)

Track statistics:
- total_evaluated
- approved_for_deletion
- blocked_by_category
- blocked_by_verification
- blocked_by_confidence
- blocked_by_domain
- blocked_by_manual_flags

### 6. Fresh Classification Mode (No Cache)
- Cache disabled - every email gets fresh AI classification
- Provides complete audit trail with AI reasoning for every email
- Cache file still saved in background for audit purposes (sender patterns)
- Ensures consistent classification without dependency on historical data

### 7. File Structure (7 files)
```
config.py              # TPM=4M, batch=200, 180+ protected domains
decision_engine.py     # 5 deletion criteria (CRITICAL)
domain_checker.py      # Protected domain detection
gmail_client.py        # Gmail API + has_manual_flags() method
email_classifier.py    # Main classifier with 5 categories, batch AI
keyword_matcher.py     # Optional bilingual keywords (currently unused)
test_decision_engine.py # Test suite for deletion logic
```

### 8. AI Prompts (CRITICAL)
**Classifier Prompt:**
- Classify into 5 categories
- CRITICAL warning about investment platforms
- Compact batch format: [{"idx":0,"cat":"promotional","c":85}]
- Process 200 emails per call

**Verifier Prompt:**
- CRITICAL section for investment platform false positives
- Reviews all promotional classifications (mandatory)
- Returns only corrections needed: [{"idx":0,"cat":"corrected","c":90}]
- If no corrections: return []

### 9. CLI Interface
```bash
--provider gemini/anthropic   # AI provider
--max-emails N                # Limit processing
--delete                      # Actually delete (dry-run by default)
--reset                       # Clear progress
--summary-only                # Show previous results
--debug                       # Enable debug logging
```

### 10. Output & Statistics
**Real-time indicators:**
- 🛡️ Protected domain (bypass AI)
- 🔍 Verified by dual-agent
- ✏️ Classification corrected
- ✓ Promotional
- ✗ Non-promotional

**Final statistics:**
- Emails by category (5 categories)
- Protected domain hits
- AI classifications count
- AI verifications count
- AI corrections count
- Correction rate
- Token usage and cost

### 11. Test Suite
Create test_decision_engine.py with tests for:
- Should delete when all 5 criteria met
- Should NOT delete non-promotional categories
- Should NOT delete unverified emails
- Should NOT delete low confidence (<90%)
- Should NOT delete protected domains (CRITICAL)
- Should NOT delete starred/important emails
- Investment platform scenario (AI says promotional 99%, domain check blocks it)

## Implementation Order

1. Create config.py with 4M TPM limits and 180+ protected domains
2. Create decision_engine.py with 5 deletion criteria
3. Create domain_checker.py with protected domain logic
4. Create gmail_client.py with has_manual_flags() method
5. Create email_classifier.py with 5-category batch classification
6. Create test_decision_engine.py and verify all tests pass
7. Test with 100 real emails before full deployment

## Success Criteria

**SAFETY (CRITICAL):**
- 0 investment/brokerage emails deleted
- 0 protected domain emails deleted
- 0 starred/important emails deleted
- All deletions require 90%+ confidence AND verification

**PERFORMANCE:**
- Process 100K emails in 30-40 minutes
- 200 emails per API call
- Handle 4M TPM efficiently

**AUDIT:**
- Every email has AI classification reasoning
- Complete deletion decision trail
- Statistics tracked for all blocking factors
```

## Running Tests

```bash
# Run decision engine tests (CRITICAL safety tests)
python test_decision_engine.py
# Expected: ALL TESTS PASSED ✓ (8/8 tests)

# Run keyword matcher tests (optional, keywords currently disabled)
python test_keyword_matcher.py
# Expected: 15/15 tests passed (5 EN + 5 DE + 5 control)

# Test with real Gmail data (recommended before full deployment)
python email_classifier.py --max-emails 100 --debug
```

## License

MIT License - Copyright (c) 2024 Sidharth Arora. See [LICENSE](LICENSE) for details.

---

*Built with Claude Code by Sidharth Arora*
