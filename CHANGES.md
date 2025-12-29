# Recent Changes

## Summary

Updated the Gmail Email Classifier with the following improvements:

### 1. Increased Gmail Fetch Batch Size
- **Changed**: Gmail API batch size from 100 to **500 emails per call**
- **File**: `config.py`
- **Benefit**: Fetch up to 500 emails in a single API call, reducing API usage and improving performance

### 2. Added Retry Mechanisms with Exponential Backoff
- **Added to**: All API calls (Gmail API and AI providers)
- **Files**: `gmail_client.py`, `ai_classifier.py`
- **Features**:
  - Automatic retry on failure (default: 3 attempts)
  - Exponential backoff (2s, 4s, 8s delays)
  - **Print statements when retrying** with attempt number and delay
  - Configurable retry settings in `config.py`

#### Retry Output Example:
```
⚠️  API call failed (attempt 1/3): 429 Rate Limit Exceeded
   Retrying in 2 seconds...
```

### 3. Export Flagged Emails to Separate File
- **Added**: Automatic export of human-flagged emails
- **File**: `email_classifier.py`
- **Output**: Creates `flagged_for_review_YYYYMMDD_HHMMSS.json` in addition to main results
- **Benefit**: Easy review of medium-confidence emails requiring human approval

## Configuration Changes

### `config.py`
```python
BATCH_CONFIG = {
    "classifier_batch_size": 20,   # Emails per AI classification request
    "gmail_fetch_batch_size": 500, # Emails to fetch per Gmail API call (max)
    "max_retries": 3,              # Retry failed API calls
    "retry_delay": 2,              # Seconds between retries
    "retry_backoff": 2,            # Exponential backoff multiplier
}
```

## File Changes

### Modified Files:
1. **config.py**
   - Increased `gmail_fetch_batch_size` to 500
   - Added `retry_backoff` configuration

2. **gmail_client.py**
   - Added `retry_with_backoff()` function
   - Wrapped all Gmail API calls with retry mechanism
   - Added print statements for retry attempts

3. **ai_classifier.py**
   - Added `retry_ai_call()` function
   - Wrapped Gemini and Claude API calls with retry mechanism
   - Added print statements for retry attempts

4. **email_classifier.py**
   - Modified `_save_results()` to export flagged emails separately
   - Creates `flagged_for_review_*.json` file automatically

## Usage

### Run Classifier (fetches up to 500 emails now):
```bash
./venv/bin/python email_classifier.py --max-emails 500
```

### Retry Example:
If an API call fails, you'll see:
```
⚠️  Gmail API call failed (attempt 1/3): 503 Service Unavailable
   Retrying in 2 seconds...
⚠️  Gmail API call failed (attempt 2/3): 503 Service Unavailable
   Retrying in 4 seconds...
✓ Success on attempt 3!
```

### Flagged Emails Output:
After running, check:
- **All results**: `classification_results/classification_results_20251228_223045.json`
- **Flagged only**: `classification_results/flagged_for_review_20251228_223045.json`

## Benefits

### Performance
- **Fewer API calls**: 500 emails in 1 call vs. 5 calls of 100 emails
- **Cost savings**: Reduced Gmail API quota usage
- **Faster processing**: Less network overhead

### Reliability
- **Automatic recovery**: Transient failures handled automatically
- **Exponential backoff**: Prevents overwhelming rate-limited APIs
- **Visibility**: Print statements show retry attempts in real-time

### Usability
- **Easy review**: Flagged emails in dedicated file
- **Better workflow**: Reviewers can focus on just the flagged items
- **Audit trail**: Separate file for compliance/tracking

## Testing

Run tests to ensure everything works:
```bash
./venv/bin/python test_decision_engine.py
```

All 22 tests should pass ✓

## Notes

- Gmail API allows up to 500 emails per request (we now use max)
- Retry mechanism respects rate limits with exponential backoff
- Flagged file only created if there are emails needing review
- Print statements appear during classification for transparency
