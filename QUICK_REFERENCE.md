# Quick Reference - New Features

## 🚀 Quick Start

### Basic Run (with logging & progress):
```bash
./venv/bin/python email_classifier.py --max-emails 100
```
**You get**: ✅ INFO logs, ✅ Progress bars, ✅ Log file

### Debug Run:
```bash
./venv/bin/python email_classifier.py --max-emails 50 --debug
```
**You get**: ✅ DEBUG logs (detailed), ✅ Full trace

### Resume Run:
```bash
./venv/bin/python email_classifier.py --max-emails 500 --resume
```
**You get**: ✅ Can interrupt (Ctrl+C) and resume later

---

## 📋 CLI Commands

### Logging:
```bash
--debug                         # Enable DEBUG level
--log-level INFO                # Set level (DEBUG|INFO|WARNING|ERROR)
```

### Resume:
```bash
--resume                        # Enable resume functionality
```

### Combined Example:
```bash
./venv/bin/python email_classifier.py \
  --max-emails 500 \
  --resume \
  --debug \
  --market india
```

---

## 📊 What You'll See

### Progress Bars:
```
Downloading emails: 100%|██████████| 500/500 [01:23<00:00, 6.0 email/s]
Classifying: 100%|████████████████| 500/500 [00:45<00:00, 11.2 email/s]
```

### Logging (colored):
```
INFO - Fetching emails with query: 'is:unread'
DEBUG - Fetching batch (page_token: None)
DEBUG - Fetched 500 message IDs
INFO - Successfully fetched 500 emails
```

### Retry Messages:
```
⚠️  Gmail API call failed (attempt 1/3): 503 Service Unavailable
   Retrying in 2 seconds...
```

### Resume Prompt:
```
RESUMABLE SESSION FOUND
Options:
  [r] Resume previous session
  [n] Start new session
  [s] Show details
Your choice [r/n/s]:
```

---

## 📁 Files Created

### Logs:
```
logs/classifier_20251229_081319.log
```

### State (during processing):
```
classification_results/current_state.json
```

### Completed (archived):
```
classification_results/completed_state_20251229_081319.json
```

---

## 🔍 Common Tasks

### See detailed logs:
```bash
./venv/bin/python email_classifier.py --max-emails 50 --debug
cat logs/classifier_*.log | tail -50
```

### Process large batch with resume:
```bash
./venv/bin/python email_classifier.py --max-emails 1000 --resume
# Can press Ctrl+C anytime, then resume later
```

### Quiet mode (warnings only):
```bash
./venv/bin/python email_classifier.py --log-level WARNING --max-emails 100
```

---

## 💡 Tips

1. **Always use --resume** for large batches (>200 emails)
2. **Use --debug** when troubleshooting
3. **Check logs/** for detailed traces
4. **Press Ctrl+C** safely - resume later with same command + --resume

---

## 🆘 Troubleshooting

### No progress bars?
```bash
pip install tqdm
```

### Resume not working?
Add `--resume` flag and check `classification_results/current_state.json` exists

### Want more detail?
```bash
--debug  # or --log-level DEBUG
```

---

## ✅ Features Summary

| Feature | Flag | Benefit |
|---------|------|---------|
| Debug Logging | `--debug` | See detailed trace |
| Custom Log Level | `--log-level INFO` | Control verbosity |
| Progress Bars | (automatic) | See real-time progress |
| Resume | `--resume` | Interrupt-safe processing |
| Log Files | (automatic) | Full audit trail |
| Retry | (automatic) | Auto-recover from failures |

---

**Ready to use! All features tested and working.** ✅
