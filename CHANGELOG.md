# Changelog

All notable changes to the Gmail Email Classifier will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-28

### Added
- **Core Classification System**
  - Multi-regional support for USA, India, and Germany markets
  - Bilingual classification (English and German)
  - 5 email categories (PROMOTIONAL, TRANSACTIONAL, SYSTEM_SECURITY, SOCIAL_PLATFORM, PERSONAL_HUMAN)

- **Safety Architecture**
  - 5-gate safety system with mandatory checks
  - Dual-agent verification (Classifier + Verifier)
  - Three-tier confidence system (High ≥90%, Medium 70-89%, Low <70%)
  - Comprehensive protected domain lists (300+ domains across 3 markets)
  - Protected categories: investment/brokerage, banking, government, healthcare, utilities, education

- **AI Integration**
  - Gemini 2.0 Flash support (default, faster & cheaper)
  - Anthropic Claude Sonnet 4.5 support (alternative, higher quality)
  - Batch processing with rate limiting
  - Bilingual prompt engineering

- **Gmail API Integration**
  - OAuth 2.0 authentication
  - Batch email fetching
  - Manual flag detection (starred/important)
  - Trash-based deletion (recoverable)

- **Decision Engine**
  - Multi-criteria evaluation with 5 mandatory gates
  - Gate 1: Category check (must be PROMOTIONAL)
  - Gate 2: Dual-agent verification
  - Gate 3: Confidence threshold
  - Gate 4: Protected domain check
  - Gate 5: Manual flags check
  - Statistics tracking and reporting

- **Analysis & Optimization**
  - Precision-recall curve generation
  - F1-score optimization
  - Confidence threshold analysis
  - False positive identification
  - Validation result tracking

- **Human-in-the-Loop**
  - Interactive review workflow for flagged emails
  - Approve/reject/skip decisions
  - Decision tracking and export
  - Batch execution of approved deletions

- **CLI Interface**
  - Dry-run mode (default, safe)
  - Market-specific optimization (--market usa|india|germany)
  - Language filtering (--language en|de|both)
  - AI provider selection (--provider gemini|anthropic)
  - Confidence threshold tuning (--confidence-threshold N)
  - High-confidence-only deletion mode
  - Gmail query support
  - Debug mode

- **Testing**
  - Comprehensive test suite for decision engine
  - Critical false positive prevention tests
  - Edge case coverage
  - Boundary condition tests
  - Domain checker validation

- **Documentation**
  - Complete README with setup instructions
  - Quick start guide (10-minute setup)
  - Usage examples (programmatic API)
  - Makefile for common tasks
  - Inline code documentation

### Security Features
- Zero false positives on critical domains (investment, banking, government)
- Fail-safe defaults (when in doubt, don't delete)
- Recoverable deletions (trash, not permanent)
- Comprehensive audit trail
- Protected domain bypass (never classified by AI)

### Performance Features
- Batch processing for efficiency
- Rate limiting compliance
- Progress persistence
- Concurrent API calls where safe
- Optimized for 200K+ email processing

### Regional Coverage

**USA:**
- 14 investment brokerages (Schwab, Fidelity, Robinhood, etc.)
- 17 banks and digital payment platforms
- Government (.gov) domains
- 7+ healthcare providers
- Major utilities and telecoms
- Education (.edu) domains

**India:**
- 14 investment brokerages (Zerodha, Groww, Upstox, etc.)
- 12 banks and digital payment platforms
- Government (.gov.in, .nic.in) domains
- Healthcare providers
- Major telecoms
- Education (.ac.in, .edu.in) domains

**Germany:**
- 10 investment brokers (Trade Republic, Scalable Capital, etc.)
- 10 banks including Sparkasse, Deutsche Bank
- Government (.gov.de) domains
- 8 health insurance providers (TK, AOK, Barmer, etc.)
- Major utilities and telecoms
- Education institutions

### Known Limitations
- Gmail API quota: 250 queries/minute
- Gemini rate limit: 60 requests/minute
- Claude rate limit: 50 requests/minute (tier-dependent)
- Email body limited to 1000 characters for classification
- Requires manual OAuth setup for Gmail

### Future Enhancements (Roadmap)
- [ ] Web UI for human review workflow
- [ ] Adaptive learning from user feedback
- [ ] Multi-account support
- [ ] Scheduled runs (daily/weekly automation)
- [ ] Slack/email notifications for flagged emails
- [ ] A/B testing for prompt optimization
- [ ] Export to CSV/Excel
- [ ] Docker containerization
- [ ] Prometheus metrics export
- [ ] Real-time classification API

## [Unreleased]

### Planned for 1.1.0
- Web-based review interface
- User feedback integration
- Improved prompt templates based on production data
- Additional protected domains from user feedback
- Performance optimizations for large inboxes (1M+ emails)

---

## Version History

- **1.0.0** (2025-12-28) - Initial release with full safety system
