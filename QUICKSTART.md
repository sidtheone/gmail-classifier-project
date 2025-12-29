# Quick Start Guide

Get your Gmail classifier running in **10 minutes**.

## Prerequisites
- Python 3.8+
- Gmail account
- Gemini API key (free from Google AI Studio)

## 5-Step Setup

### Step 1: Install Dependencies (2 min)
```bash
cd email
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Get Gemini API Key (2 min)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

### Step 3: Configure Environment (1 min)
```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```bash
GEMINI_API_KEY=your-api-key-here
```

### Step 4: Setup Gmail API (3 min)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json` in project root

### Step 5: Test Run (2 min)
```bash
# First run - authenticate with Gmail (opens browser)
python gmail_client.py

# Test classification (dry-run, no deletion)
python email_classifier.py --max-emails 10
```

## First Classification

### Dry-Run (Safe - No Deletions)
```bash
# Classify 50 emails, show what would be deleted
python email_classifier.py --max-emails 50
```

**Output:**
- ✅ Shows classification for each email
- ✅ Displays safety gate results
- ✅ Generates summary report
- ✅ **NO actual deletions**

### Review Results
```bash
# Check classification_results/ folder
ls -lh classification_results/

# View latest results
cat classification_results/classification_results_*.json | jq '.[0]'
```

### Human Review of Flagged Emails
```bash
# If medium-confidence emails were flagged
python review_workflow.py classification_results/classification_results_YYYYMMDD_HHMMSS.json
```

## Enable Deletion (When Ready)

### High Confidence Only (Safest)
```bash
# Only delete emails with ≥90% confidence
python email_classifier.py --delete-high-confidence --max-emails 100
```

### Full Deletion
```bash
# Delete all approved emails (high confidence + reviewed flagged)
python email_classifier.py --delete --max-emails 100
```

**Note:** Deletions move emails to **Trash** (recoverable for 30 days), not permanent deletion.

## Market-Specific Usage

### USA Market
```bash
python email_classifier.py --market usa --language en --max-emails 100
```

### India Market
```bash
python email_classifier.py --market india --language en --max-emails 100
```

### Germany Market
```bash
python email_classifier.py --market germany --language both --max-emails 100
```

## Common Queries

### Unread Emails Only
```bash
python email_classifier.py --query "is:unread" --max-emails 200
```

### Emails from Last Week
```bash
python email_classifier.py --query "newer_than:7d" --max-emails 500
```

### Specific Sender
```bash
python email_classifier.py --query "from:marketing@company.com"
```

## Safety Checks

### Verify Protected Domains
```bash
# Test domain checker
python domain_checker.py
```

Expected output should show PROTECTED for:
- Investment platforms (Zerodha, Schwab, Trade Republic)
- Banks (HDFC, Chase, Deutsche Bank)
- Government (.gov, .gov.in, Finanzamt)

### Run Safety Tests
```bash
# Run comprehensive test suite
python test_decision_engine.py -v
```

All tests should **PASS**, especially:
- `test_critical_false_positive_prevention_investment`
- `test_critical_false_positive_prevention_government`

## Troubleshooting

### "GEMINI_API_KEY not set"
```bash
# Check .env file exists
cat .env | grep GEMINI_API_KEY

# If missing, add it
echo "GEMINI_API_KEY=your-key" >> .env
```

### "Credentials file not found"
```bash
# Verify credentials.json exists
ls -l credentials.json

# If missing, download from Google Cloud Console
```

### "Authentication failed"
```bash
# Delete old token and re-authenticate
rm token.pickle
python gmail_client.py
```

### Rate Limit Errors
```bash
# Reduce batch size
python email_classifier.py --max-emails 50
```

Wait a few minutes and try again.

## Next Steps

1. **Review Results**: Check `classification_results/` folder
2. **Verify Safety**: Ensure no false positives in dry-run
3. **Add Protected Domains**: Edit `config.py` if needed
4. **Enable Deletion**: Start with `--delete-high-confidence`
5. **Automate**: Set up cron job for daily runs

## Daily Automation (Optional)

### Linux/Mac Cron
```bash
# Edit crontab
crontab -e

# Add daily run at 2 AM
0 2 * * * cd /path/to/email && source venv/bin/activate && python email_classifier.py --delete-high-confidence --max-emails 200 >> logs/classifier.log 2>&1
```

### Windows Task Scheduler
1. Create batch file `run_classifier.bat`:
```batch
cd C:\path\to\email
call venv\Scripts\activate
python email_classifier.py --delete-high-confidence --max-emails 200
```

2. Schedule in Task Scheduler to run daily

## Support

- **Check Logs**: `classification_results/` folder
- **Run Tests**: `python test_decision_engine.py`
- **Debug Mode**: `python email_classifier.py --debug`
- **Review README**: Full documentation in `README.md`

---

**Remember:** Always start with dry-run mode and verify results before enabling deletion!
