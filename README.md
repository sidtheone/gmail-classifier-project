# Safety-First Gmail Email Classifier

Production-grade AI-powered email management system optimized for USA, India, and Germany markets with **zero false positive guarantee** on critical communications.

## Features

- **Multi-Regional Support**: Optimized protected domain lists for USA, India, and Germany
- **Bilingual Classification**: Native English and German language support
- **5-Gate Safety System**: ALL gates must pass before deletion
- **Dual-Agent Verification**: Classifier + Verifier for promotional emails
- **Three-Tier Confidence**: High (≥90%), Medium (70-89%), Low (<70%)
- **Human-in-the-Loop**: Medium confidence emails flagged for manual review
- **Precision-Recall Optimization**: Data-driven threshold tuning
- **Comprehensive Audit Trail**: Full decision logging with AI reasoning

## Critical Safety Guarantees

✅ **ZERO** investment/brokerage emails deleted (Zerodha, Schwab, Trade Republic, etc.)
✅ **ZERO** banking emails deleted (HDFC, Chase, Deutsche Bank, etc.)
✅ **ZERO** government emails deleted (.gov, .gov.in, Finanzamt)
✅ **ZERO** starred/important emails deleted
✅ **ZERO** deletions without dual-agent verification

## Quick Start

### 1. Installation

```bash
# Clone repository
cd email

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Gmail API Setup

#### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

#### Step 2: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure consent screen (if prompted):
   - User type: External (for personal use)
   - App name: "Gmail Email Classifier"
   - Add your email as test user
4. Application type: **Desktop app**
5. Download credentials JSON
6. Save as `credentials.json` in project root

#### Step 3: First Run Authentication
```bash
# First run will open browser for OAuth consent
python gmail_client.py

# This creates token.pickle for future use
```

### 3. AI Provider Setup

#### Option A: Gemini (Recommended - Faster & Cheaper)
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to `.env`:
```bash
GEMINI_API_KEY=your-gemini-api-key
```

#### Option B: Anthropic Claude (Higher Quality)
1. Get API key from [Anthropic Console](https://console.anthropic.com/)
2. Add to `.env`:
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 4. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Gmail API
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret

# AI Provider (choose one or both)
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key  # Optional

# Market & Language
TARGET_MARKET=all  # usa, india, germany, or all
SUPPORTED_LANGUAGES=both  # en, de, or both

# Safety Settings
DEFAULT_CONFIDENCE_THRESHOLD=90
ENABLE_HUMAN_REVIEW=true
AUTO_DELETE_HIGH_CONFIDENCE=false
```

## Usage

### Basic Commands

#### Dry-Run Mode (Safe - No Deletions)
```bash
# Process up to 100 emails (default: no deletion)
python email_classifier.py --max-emails 100

# Process all unread emails
python email_classifier.py --query "is:unread"

# Optimize for specific market
python email_classifier.py --market india --max-emails 50
```

#### Review & Deletion
```bash
# Show what would be deleted (dry-run)
python email_classifier.py --max-emails 100

# Actually delete approved emails (moves to trash, recoverable)
python email_classifier.py --max-emails 100 --delete

# Only delete high confidence (≥90%) emails
python email_classifier.py --delete-high-confidence --max-emails 100
```

#### Market-Specific Processing
```bash
# USA market optimization
python email_classifier.py --market usa --language en

# India market optimization
python email_classifier.py --market india --language en

# Germany market optimization (bilingual)
python email_classifier.py --market germany --language both
```

#### AI Provider Selection
```bash
# Use Gemini (default - faster, cheaper)
python email_classifier.py --provider gemini

# Use Claude (higher quality, more expensive)
python email_classifier.py --provider anthropic
```

#### Advanced Options
```bash
# Custom confidence threshold
python email_classifier.py --confidence-threshold 95

# Disable human review for medium confidence
python email_classifier.py --disable-human-review

# Debug mode with verbose logging
python email_classifier.py --debug --max-emails 10
```

### Complete Example

```bash
# Production-ready command for India market
python email_classifier.py \
  --market india \
  --language en \
  --provider gemini \
  --confidence-threshold 90 \
  --max-emails 500 \
  --delete-high-confidence
```

## Architecture

### Classification Categories

1. **PROMOTIONAL** (deletion eligible)
   - Marketing emails, newsletters, sales, discounts

2. **TRANSACTIONAL** (protected)
   - Receipts, shipping confirmations, payment notifications

3. **SYSTEM_SECURITY** (protected)
   - Password resets, 2FA codes, security alerts

4. **SOCIAL_PLATFORM** (protected)
   - Social network notifications, friend requests

5. **PERSONAL_HUMAN** (protected)
   - Direct correspondence, work emails, personal communications

### 5-Gate Safety System

ALL gates must pass for deletion approval:

1. **Gate 1: Category Check** - Must be PROMOTIONAL
2. **Gate 2: Verification Check** - Dual-agent verification passed
3. **Gate 3: Confidence Threshold** - Meets confidence requirement (default ≥90%)
4. **Gate 4: Protected Domain Check** - NOT from protected domain
5. **Gate 5: Manual Flags Check** - NOT starred or marked important

### Dual-Agent Verification

**Agent 1 (Classifier):**
- Batch classify emails in English/German
- Categorize into 5 categories with confidence scores

**Agent 2 (Verifier):**
- Review ALL promotional classifications
- Focus on investment/banking/government false positives
- Correct misclassifications

### Protected Domains by Market

**USA:**
- Investment: Schwab, Fidelity, Robinhood, E*TRADE, Vanguard
- Banking: Chase, Bank of America, Wells Fargo, Citi
- Government: .gov domains, IRS, USPS
- Healthcare: UnitedHealthcare, Anthem, Cigna

**India:**
- Investment: Zerodha, Groww, Upstox, Angel One
- Banking: HDFC, ICICI, SBI, Axis, Kotak
- Government: .gov.in, income tax, EPFO
- Digital: Paytm, PhonePe, Google Pay

**Germany:**
- Investment: Trade Republic, Scalable Capital, Flatex
- Banking: Deutsche Bank, Sparkasse, Commerzbank
- Government: .gov.de, Finanzamt
- Healthcare: TK, AOK, Barmer (Krankenkassen)

## Testing

### Run Unit Tests
```bash
# Test decision engine
python test_decision_engine.py

# Test individual components
python domain_checker.py
python decision_engine.py
python gmail_client.py
```

### Critical Safety Tests

The test suite includes critical safety tests for:
- Investment platform false positives (USA, India, Germany)
- Government email false positives
- Banking email false positives
- Starred/important email protection
- All 5 gates functioning correctly

## Precision-Recall Optimization

### Generate Analysis
```bash
# Run classifier to generate validation data first
python email_classifier.py --max-emails 500

# Analyze confidence thresholds
python confidence_analyzer.py
```

### Outputs
- `plots/precision_recall_curve.png` - PR curve
- `plots/f1_scores.png` - F1 scores by threshold
- `plots/deletion_rate.png` - Deletion rate vs threshold
- `plots/threshold_analysis.txt` - Detailed report

## File Structure

```
email/
├── config.py                    # Regional config & protected domains
├── domain_checker.py            # Domain protection & market ID
├── decision_engine.py           # 5-gate safety system
├── gmail_client.py              # Gmail API OAuth & email fetching
├── ai_classifier.py             # Dual-agent AI classification
├── confidence_analyzer.py       # Precision-recall optimization
├── email_classifier.py          # Main CLI application
├── test_decision_engine.py      # Comprehensive test suite
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── credentials.json             # Gmail OAuth credentials (gitignored)
├── token.pickle                 # Gmail access token (gitignored)
└── classification_results/      # Output directory
```

## Output & Results

### Console Output
- Real-time progress with color-coded status
- Category breakdown by market
- Decision engine statistics
- Gate failure analysis

### Saved Results
Results saved to `classification_results/classification_results_YYYYMMDD_HHMMSS.json`:

```json
{
  "email_id": "...",
  "from": "deals@shop.com",
  "subject": "50% OFF Sale",
  "category": "promotional",
  "confidence": 95.0,
  "language": "en",
  "verified": true,
  "decision": "approved",
  "confidence_level": "high",
  "final_reason": "All 5 safety gates passed",
  "gates": [...]
}
```

## Safety Best Practices

### Start Conservatively
1. Run in **dry-run mode** first (default)
2. Review flagged emails manually
3. Check protected domain coverage for your region
4. Start with small batches (--max-emails 50)
5. Use high confidence threshold (≥90%)

### Gradual Rollout
1. **Week 1**: Dry-run only, analyze results
2. **Week 2**: Delete high confidence only (≥95%)
3. **Week 3**: Lower to 90% if no false positives
4. **Week 4+**: Enable medium confidence with human review

### Monitoring
- Check `classification_results/` regularly
- Monitor false positive rate (<5% target)
- Update protected domains as needed
- Review correction rate from verifier agent

## Troubleshooting

### Gmail API Issues
```bash
# Delete token and re-authenticate
rm token.pickle
python gmail_client.py
```

### Rate Limits
- Gemini: 60 requests/minute (default)
- Claude: 50 requests/minute (tier-dependent)
- Gmail API: 250 queries/minute

Adjust in `config.py` if needed.

### Protected Domain Not Recognized
Add to `config.py` in appropriate market/category:
```python
PROTECTED_DOMAINS["india"]["investment_brokerage"].append("newbroker.com")
```

### False Positives Detected
1. Stop deletion immediately
2. Review `classification_results/` for pattern
3. Add domain to protected list
4. Increase confidence threshold
5. Re-run in dry-run mode

## Contributing

### Adding Protected Domains
1. Edit `config.py`
2. Add to appropriate market + category
3. Run validation: `python config.py`
4. Test: `python domain_checker.py`

### Adjusting AI Prompts
1. Edit prompts in `ai_classifier.py`
2. Test with sample emails
3. Verify no regression in safety tests

## License

This is a safety-critical system. Use at your own risk. Always start with dry-run mode and thoroughly test with your specific email patterns before enabling deletion.

## Support

For issues, feature requests, or questions:
1. Check existing classification results in `classification_results/`
2. Run tests: `python test_decision_engine.py`
3. Enable debug mode: `--debug`
4. Review logs for specific error messages

## Roadmap

- [ ] Web UI for human review workflow
- [ ] Adaptive learning from user feedback
- [ ] Multi-account support
- [ ] Email scheduling (run daily/weekly)
- [ ] Slack/email notifications for flagged emails
- [ ] A/B testing for prompt optimization
- [ ] Export to CSV/Excel for analysis

---

**Remember**: When in doubt, DO NOT DELETE. This system prioritizes safety over deletion efficiency.
