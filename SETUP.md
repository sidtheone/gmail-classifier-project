# Quick Start Guide

## Prerequisites

- Python 3.8+
- Google Cloud account with Gmail API enabled
- Anthropic API key

## Step 1: Install Dependencies

```bash
cd gmail-classifier-project
pip install -r requirements.txt
```

## Step 2: Set Up Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Gmail API**:
   - APIs & Services > Library > Search "Gmail API" > Enable
4. Create OAuth credentials:
   - APIs & Services > Credentials > Create Credentials > OAuth client ID
   - Application type: **Desktop app**
   - Download JSON and save as `credentials.json` in this directory

## Step 3: Set Anthropic API Key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or pass via command line:
```bash
python email_classifier.py --api-key "your-key-here"
```

## Step 4: Run the Classifier

**First run (processes all emails):**
```bash
python email_classifier.py
```

**Limit to first 100 emails (testing):**
```bash
python email_classifier.py --max-emails 100
```

**Actually delete promotional emails:**
```bash
python email_classifier.py --delete
```

## Common Issues

**"credentials.json not found"**
- Ensure you downloaded OAuth credentials from Google Cloud Console
- Place the file in the same directory as `email_classifier.py`

**"Token refresh failed"**
- Delete `token.pickle` and re-authenticate

**Rate limiting errors**
- The script handles this automatically with exponential backoff
- For heavy usage, wait a few minutes before retrying

## Command Line Options

| Flag | Description |
|------|-------------|
| `--max-emails N` | Process only N emails |
| `--no-cache` | Disable sender caching |
| `--no-verify` | Disable dual-agent verification |
| `--delete` | Actually delete promotional emails |
| `--reset` | Clear progress and start fresh |
| `--summary-only` | Show results without processing |
