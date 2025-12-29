# New Features - Logging, Progress & Resume

## Overview

Three major features have been added to the Gmail Email Classifier:

1. **Debug & Info Logging** - Comprehensive logging system
2. **Progress Indicators** - Visual progress bars for downloading and classification
3. **Resume Functionality** - Continue from interrupted sessions

---

## 1. Debug & Info Logging

### Features

- **Colored console output** - Easy-to-read INFO, DEBUG, WARNING, ERROR messages
- **File logging** - Detailed logs saved to `logs/classifier_YYYYMMDD_HHMMSS.log`
- **Component-level logging** - Separate loggers for GmailClient, EmailClassifier, etc.

### Usage

#### Info Level (default):
```bash
./venv/bin/python email_classifier.py --max-emails 50
```

#### Debug Level:
```bash
./venv/bin/python email_classifier.py --max-emails 50 --debug
```

Or:
```bash
./venv/bin/python email_classifier.py --max-emails 50 --log-level DEBUG
```

#### Other Levels:
```bash
# Warning only
./venv/bin/python email_classifier.py --log-level WARNING

# Error only
./venv/bin/python email_classifier.py --log-level ERROR
```

### Log Output Example

**Console** (colored):
```
INFO - Fetching emails with query: 'is:unread'
INFO - Estimated 342 emails found
INFO - Successfully fetched 342 emails
DEBUG - Fetching batch (page_token: None)
DEBUG - Fetched 500 message IDs
```

**File** (detailed):
```
2025-12-28 22:45:12 - GmailClient - INFO - Fetching emails with query: 'is:unread'
2025-12-28 22:45:13 - GmailClient - DEBUG - Fetching batch (page_token: None)
2025-12-28 22:45:14 - GmailClient - DEBUG - Fetched 500 message IDs
2025-12-28 22:45:15 - EmailClassifier - INFO - Classification workflow completed
```

### Log Files Location

All logs are saved in `logs/` directory:
```
logs/
├── classifier_20251228_224512.log
├── classifier_20251228_225103.log
└── classifier_20251228_230045.log
```

---

## 2. Progress Indicators

### Features

- **Email Download Progress** - Shows downloading progress with tqdm
- **Classification Progress** - Shows AI classification progress
- **Real-time estimates** - Time remaining, emails/second

### Visual Output

#### Download Progress:
```
Downloading emails: 100%|██████████████████| 500/500 [01:23<00:00, 6.02 email/s]
```

#### Classification Progress:
```
Classifying: 100%|████████████████████████████| 500/500 [00:45<00:00, 11.2 email/s]
```

### Features

- **Green progress bars** - Easy to see
- **Time estimates** - ETA and elapsed time
- **Speed tracking** - Emails processed per second
- **Automatic sizing** - Fits terminal width

---

## 3. Resume Functionality

### Features

- **Interrupt-safe** - Press Ctrl+C safely, resume later
- **State persistence** - Saves progress to JSON file
- **Skip processed** - Automatically skips already classified emails
- **Session management** - Track multiple sessions

### How It Works

1. **First Run** - Creates session, processes emails
2. **Interrupt** (Ctrl+C) - State saved automatically
3. **Resume** - Continues from where it left off

### Usage

#### Enable Resume:
```bash
./venv/bin/python email_classifier.py --max-emails 500 --resume
```

#### Resume Session:
If you run with `--resume` and there's an incomplete session:

```
================================================================================
RESUMABLE SESSION FOUND
================================================================================

A previous incomplete session was detected.
You can resume from where you left off.

Options:
  [r] Resume previous session
  [n] Start new session (discard previous)
  [s] Show previous session details
================================================================================

Your choice [r/n/s]: r
```

**Options:**
- `r` - Resume previous session
- `n` - Start new session (discards previous)
- `s` - Show details and exit

### Session Details:

```
Previous Session Details:
  Session ID: 20251228_223045
  Started: 2025-12-28T22:30:45
  Processed: 342 emails
  Approved: 234, Rejected: 98, Flagged: 10
```

### State Files

Resume state is saved in `classification_results/`:

```
classification_results/
├── current_state.json          ← Active session (deleted when complete)
└── completed_state_*.json      ← Archived completed sessions
```

### State File Contents:

```json
{
  "session_id": "20251228_223045",
  "started_at": "2025-12-28T22:30:45",
  "last_updated": "2025-12-28T22:35:12",
  "query": "is:unread",
  "max_emails": 500,
  "total_emails_found": 500,
  "emails_fetched": 500,
  "emails_classified": 342,
  "emails_decided": 342,
  "processed_email_ids": ["msg_1", "msg_2", ...],
  "approved_count": 234,
  "rejected_count": 98,
  "flagged_count": 10
}
```

### How Resume Works

1. **Checks for existing session** - Looks for `current_state.json`
2. **Loads processed email IDs** - Knows which emails were already classified
3. **Fetches all emails** - Gets full list from Gmail
4. **Filters processed** - Skips emails already in processed_email_ids
5. **Continues** - Classifies only remaining emails
6. **Updates state** - Saves progress after each batch
7. **Completes** - Archives state when done

### Example Resume Workflow

#### First Run (interrupted):
```bash
$ ./venv/bin/python email_classifier.py --max-emails 500 --resume

Downloading emails: 100%|██████| 500/500 [01:20<00:00]
Classifying: 68%|████████   | 342/500 [00:30<00:15]
^C  # User presses Ctrl+C

# State saved: 342 emails processed
```

#### Resume Run:
```bash
$ ./venv/bin/python email_classifier.py --max-emails 500 --resume

RESUMABLE SESSION FOUND
Your choice [r/n/s]: r

Skipped 342 already processed emails (resuming)

Classifying: 100%|██████████| 158/158 [00:14<00:00]
✓ Session completed successfully
```

---

## Combined Usage Examples

### Debug + Resume:
```bash
./venv/bin/python email_classifier.py \
  --max-emails 1000 \
  --resume \
  --debug
```

### Info + Progress (default):
```bash
./venv/bin/python email_classifier.py --max-emails 500
```

### Quiet Mode (warnings only):
```bash
./venv/bin/python email_classifier.py \
  --max-emails 500 \
  --log-level WARNING
```

---

## Files Created

### New Python Files:
- `logger.py` - Logging configuration with colored output
- `resume_manager.py` - Session state management

### Modified Files:
- `gmail_client.py` - Added progress bars, logging
- `ai_classifier.py` - Added logging for AI calls
- `email_classifier.py` - Added logging, resume support

### State Files:
- `logs/` - Log files directory
- `classification_results/current_state.json` - Active session
- `classification_results/completed_state_*.json` - Archived sessions

---

## Configuration

### Batch Config (config.py):
```python
BATCH_CONFIG = {
    "gmail_fetch_batch_size": 500,  # 500 emails at once
    "max_retries": 3,                # Retry 3 times
    "retry_delay": 2,                # 2s initial delay
    "retry_backoff": 2,              # Exponential backoff
}
```

---

## Benefits

### Logging:
- **Debugging** - Trace issues with DEBUG level
- **Monitoring** - Track progress with INFO level
- **Production** - Use WARNING/ERROR for clean output
- **Audit trail** - Full logs saved to files

### Progress:
- **Visibility** - See real-time progress
- **Time estimates** - Know when it will finish
- **Speed monitoring** - Track performance

### Resume:
- **Reliability** - Safe to interrupt anytime
- **Efficiency** - Don't reprocess emails
- **Flexibility** - Pause and continue later
- **Safety** - No lost work on crashes

---

## Testing

### Test Logging:
```bash
# Info level
./venv/bin/python email_classifier.py --max-emails 10

# Debug level
./venv/bin/python email_classifier.py --max-emails 10 --debug

# Check log file
cat logs/classifier_*.log | tail -20
```

### Test Progress:
```bash
# Should show green progress bars
./venv/bin/python email_classifier.py --max-emails 50
```

### Test Resume:
```bash
# Start processing
./venv/bin/python email_classifier.py --max-emails 100 --resume

# Press Ctrl+C after ~20 emails

# Resume
./venv/bin/python email_classifier.py --max-emails 100 --resume
# Choose [r] to resume
```

---

## Troubleshooting

### No Progress Bars?
- Make sure `tqdm` is installed: `pip install tqdm`
- Check terminal supports ANSI colors

### Resume Not Working?
- Check `classification_results/current_state.json` exists
- Use `--resume` flag
- Make sure you're using same query/max-emails

### Logs Not Appearing?
- Check `logs/` directory exists
- Verify log level (use --debug for verbose)
- Check file permissions

---

## CLI Reference

```bash
# Logging options
--debug                      # Enable DEBUG level
--log-level [DEBUG|INFO|WARNING|ERROR]  # Set log level

# Resume option
--resume                     # Enable resume functionality

# Combined
./venv/bin/python email_classifier.py \
  --max-emails 500 \
  --resume \
  --debug \
  --market india
```

---

**All features are production-ready and tested!** 🚀
