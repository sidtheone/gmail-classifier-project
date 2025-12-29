"""
AI Classifier - Bilingual email classification with dual-agent verification
Supports Gemini 2.0 Flash and Anthropic Claude
English and German language support
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from anthropic import Anthropic

from config import EmailCategory, AI_PROVIDERS, RATE_LIMITS, BATCH_CONFIG


def retry_ai_call(func: Callable, *args, **kwargs):
    """
    Retry AI API call with exponential backoff.

    Args:
        func: Function to retry
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result
    """
    max_retries = BATCH_CONFIG['max_retries']
    base_delay = BATCH_CONFIG['retry_delay']
    backoff = BATCH_CONFIG['retry_backoff']

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed
                raise

            # Calculate delay with exponential backoff
            delay = base_delay * (backoff ** attempt)

            print(f"⚠️  AI API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            print(f"   Retrying in {delay} seconds...")

            time.sleep(delay)

    raise RuntimeError(f"Failed after {max_retries} attempts")


class AIProvider(str, Enum):
    """Supported AI providers"""
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


@dataclass
class ClassificationResult:
    """Single email classification result"""
    idx: int
    category: EmailCategory
    confidence: float
    reason: str
    language: str
    verified: bool = False


class AIClassifier:
    """
    Bilingual AI classifier with dual-agent verification.

    Agent 1 (Classifier): Batch classify emails in English/German
    Agent 2 (Verifier): Review PROMOTIONAL classifications for false positives
    """

    def __init__(
        self,
        provider: AIProvider = AIProvider.GEMINI,
        gemini_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize AI classifier.

        Args:
            provider: AI provider to use (gemini or anthropic)
            gemini_api_key: Gemini API key (or from env)
            anthropic_api_key: Anthropic API key (or from env)
        """
        self.provider = provider

        # Initialize API clients
        if provider == AIProvider.GEMINI:
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("Gemini API key required")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(AI_PROVIDERS['gemini']['model'])
            self.client = None

        elif provider == AIProvider.ANTHROPIC:
            api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Anthropic API key required")
            self.client = Anthropic(api_key=api_key)
            self.model = None

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60 / RATE_LIMITS[provider.value]  # seconds

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def classify_batch(
        self,
        emails: List[Dict],
        batch_size: Optional[int] = None,
    ) -> List[ClassificationResult]:
        """
        Classify batch of emails with dual-agent verification.

        Args:
            emails: List of email dictionaries with 'subject', 'from', 'body'
            batch_size: Number of emails per API request

        Returns:
            List of ClassificationResult with verified flag
        """
        batch_size = batch_size or BATCH_CONFIG['classifier_batch_size']

        all_results = []

        # Process in batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]

            # Agent 1: Classify
            classifications = self._agent_1_classify(batch, start_idx=i)

            # Agent 2: Verify promotional classifications
            verified_classifications = self._agent_2_verify(batch, classifications, start_idx=i)

            all_results.extend(verified_classifications)

        return all_results

    def _agent_1_classify(
        self,
        emails: List[Dict],
        start_idx: int = 0,
    ) -> List[ClassificationResult]:
        """
        Agent 1: Batch classify emails into categories.
        Supports English and German.

        Args:
            emails: List of email dictionaries
            start_idx: Starting index for idx field

        Returns:
            List of ClassificationResult
        """
        prompt = self._build_classifier_prompt(emails)

        self._rate_limit()

        try:
            if self.provider == AIProvider.GEMINI:
                def _call_gemini():
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=AI_PROVIDERS['gemini']['temperature'],
                            max_output_tokens=AI_PROVIDERS['gemini']['max_tokens'],
                        )
                    )
                    return response.text

                response_text = retry_ai_call(_call_gemini)

            elif self.provider == AIProvider.ANTHROPIC:
                def _call_claude():
                    response = self.client.messages.create(
                        model=AI_PROVIDERS['anthropic']['model'],
                        max_tokens=AI_PROVIDERS['anthropic']['max_tokens'],
                        temperature=AI_PROVIDERS['anthropic']['temperature'],
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text

                response_text = retry_ai_call(_call_claude)

            # Parse JSON response
            results = self._parse_classification_response(response_text, start_idx)
            return results

        except Exception as e:
            print(f"Error in Agent 1 classification: {e}")
            # Fail-safe: classify all as PERSONAL_HUMAN
            return [
                ClassificationResult(
                    idx=start_idx + i,
                    category=EmailCategory.PERSONAL_HUMAN,
                    confidence=0.0,
                    reason=f"Classification error: {e}",
                    language="unknown",
                    verified=False,
                )
                for i in range(len(emails))
            ]

    def _agent_2_verify(
        self,
        emails: List[Dict],
        classifications: List[ClassificationResult],
        start_idx: int = 0,
    ) -> List[ClassificationResult]:
        """
        Agent 2: Verify promotional classifications for safety errors.
        Focus on investment/banking/government false positives.

        Args:
            emails: Original email batch
            classifications: Results from Agent 1
            start_idx: Starting index

        Returns:
            Updated classifications with verified flag
        """
        # Filter only promotional classifications for verification
        promotional_indices = [
            i for i, c in enumerate(classifications)
            if c.category == EmailCategory.PROMOTIONAL
        ]

        if not promotional_indices:
            # No promotional emails to verify - mark all as verified
            for c in classifications:
                c.verified = True
            return classifications

        # Build verification prompt
        prompt = self._build_verifier_prompt(emails, classifications, promotional_indices)

        self._rate_limit()

        try:
            if self.provider == AIProvider.GEMINI:
                def _call_gemini_verify():
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=AI_PROVIDERS['gemini']['temperature'],
                            max_output_tokens=AI_PROVIDERS['gemini']['max_tokens'],
                        )
                    )
                    return response.text

                response_text = retry_ai_call(_call_gemini_verify)

            elif self.provider == AIProvider.ANTHROPIC:
                def _call_claude_verify():
                    response = self.client.messages.create(
                        model=AI_PROVIDERS['anthropic']['model'],
                        max_tokens=AI_PROVIDERS['anthropic']['max_tokens'],
                        temperature=AI_PROVIDERS['anthropic']['temperature'],
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text

                response_text = retry_ai_call(_call_claude_verify)

            # Parse corrections
            corrections = self._parse_verifier_response(response_text, start_idx)

            # Apply corrections
            for correction in corrections:
                # Find original classification by idx
                for i, c in enumerate(classifications):
                    if c.idx == correction.idx:
                        classifications[i] = correction
                        break

            # Mark all as verified
            for c in classifications:
                c.verified = True

            return classifications

        except Exception as e:
            print(f"Error in Agent 2 verification: {e}")
            # Fail-safe: mark promotional emails as unverified
            for i in promotional_indices:
                classifications[i].verified = False
            return classifications

    # ========================================================================
    # PROMPT BUILDERS
    # ========================================================================

    def _build_classifier_prompt(self, emails: List[Dict]) -> str:
        """Build Agent 1 classification prompt"""
        email_list = []
        for i, email in enumerate(emails):
            email_str = f"""
Email {i}:
From: {email.get('from', 'unknown')}
Subject: {email.get('subject', '(no subject)')}
Body: {email.get('body', '')[:500]}
"""
            email_list.append(email_str.strip())

        emails_text = "\n\n".join(email_list)

        return f"""You are classifying Gmail emails in ENGLISH or GERMAN into 5 categories.

CRITICAL SAFETY RULES - READ CAREFULLY:

Before classifying ANY email as PROMOTIONAL, check if it matches these PROTECTED PATTERNS:

1. FINANCIAL SERVICES (Always → PERSONAL_HUMAN, NEVER promotional):
   
   **English Terms:**
   - Domain contains: "bank", "securities", "invest", "trading", "brokerage", "fund", "capital", "wealth", "finance", "insurance", "life", "prudential", "asset", "mutual"
   - Subject/content mentions: portfolio, mutual fund, stocks, shares, trading account, investment, securities, policy, premium, claim, demat, SIP, NAV, ELSS, dividend, equity, bonds
   - Contains regulatory language: "risk disclosure", "past performance", "consult advisor", "SEBI", "SEC", "BaFin", "market risk"
   - Financial account identifiers: account number, policy number, folio number, client ID
   
   **German Terms:**
   - Domain contains: "bank", "sparkasse", "volksbank", "finanz", "versicherung", "kapital", "vermögen", "fonds", "depot", "wertpapier"
   - Subject/content mentions: Depot, Wertpapiere, Aktien, Fonds, Investition, Anlage, Versicherungspolice, Prämie, Rendite, Dividende, Portfolio, Kapitalanlage
   - Contains regulatory language: "Risikohinweis", "vergangene Wertentwicklung", "Anlageberatung", "BaFin"

2. BANKING (Always → PERSONAL_HUMAN, NEVER promotional):
   
   **English Terms:**
   - Domain ends with: .bank, or contains "bank", "credit union", "sparkasse", "volksbank"
   - Subject/content mentions: account balance, transaction, transfer, loan, credit card, debit card, statement, IFSC, IBAN, SWIFT, overdraft, mortgage, wire transfer
   - Security alerts: unusual activity, login from new device, OTP, suspicious transaction, fraud alert
   
   **German Terms:**
   - Domain contains: "bank", "sparkasse", "volksbank", "raiffeisenbank", "sparda", "postbank"
   - Subject/content mentions: Kontostand, Überweisung, Transaktion, Kredit, Kreditkarte, Girokonto, Sparkonto, Kontoauszug, TAN, Dauerauftrag, Lastschrift, Disposition
   - Security alerts: ungewöhnliche Aktivität, verdächtige Transaktion, Sicherheitswarnung, Betrugswarnung

3. GOVERNMENT (Always → PERSONAL_HUMAN, NEVER promotional):
   
   **English Terms:**
   - Domain ends with: .gov, .gov.in, .gov.de, .gov.uk, or from known government departments
   - Official communications about: taxes, benefits, licenses, permits, civic services, voting, census, social security
   
   **German Terms:**
   - Domain ends with: .de (from government), contains "amt", "bundesamt", "landesamt", "behoerde", "verwaltung"
   - Subject/content mentions: Finanzamt, Arbeitsamt, Bürgeramt, Steuer, Steuerbescheid, Einkommensteuererklärung, Sozialversicherung, Aufenthaltstitel, Visa, Behörde, Bescheid, Antrag, Genehmigung
   - Common agencies: Finanzamt, Ausländerbehörde, Arbeitsagentur, Bundesagentur, Jobcenter, Einwohnermeldeamt

4. HEALTHCARE (Always → PERSONAL_HUMAN, NEVER promotional):
   
   **English Terms:**
   - Domain contains: "health", "medical", "hospital", "clinic", "pharmacy", "doctor", "patient", "1mg", "pharmeasy", "netmeds", "apollo", "care", "medic"
   - Subject/content mentions: appointment, prescription, lab results, insurance claim, treatment, diagnosis, medical records, test results, vaccination, medicine order
   - Protected health information indicators
   
   **German Terms:**
   - Domain contains: "gesundheit", "kranken", "klinik", "arzt", "apotheke", "medizin", "pflege", "therapie"
   - Healthcare providers: "TK" (Techniker Krankenkasse), "AOK", "Barmer", "DAK", "IKK", "BKK"
   - Subject/content mentions: Termin, Rezept, Krankenkasse, Versichertenkarte, Arzttermin, Behandlung, Krankmeldung, Arbeitsunfähigkeitsbescheinigung, Medikament, Apotheke, Gesundheitsakte, Impfung, Befund, Laborergebnisse
   - Insurance terms: Krankenversicherung, Zuzahlung, Erstattung, Leistungsanspruch

5. UTILITIES & ESSENTIAL SERVICES (Usually → PERSONAL_HUMAN):
   
   **English Terms:**
   - Domain contains: "energy", "power", "electric", "gas", "water", "telecom", "mobile", "broadband"
   - Subject/content mentions: bill, meter reading, service interruption, payment due, connection
   
   **German Terms:**
   - Domain contains: "stadtwerke", "energie", "strom", "gas", "wasser", "telekom", "vodafone"
   - Subject/content mentions: Rechnung, Zählerstand, Abschlag, Stromrechnung, Gasrechnung, Wasserrechnung, Vertrag, Tarif, Verbrauch, Anschluss

6. EDUCATION/EMPLOYMENT (Usually → PERSONAL_HUMAN unless clearly promotional):
   
   **English Terms:**
   - Domain ends with .edu or from universities/schools
   - Work-related emails from company domains
   - Direct job offers or employment communications
   
   **German Terms:**
   - Domain ends with: .edu, or contains "uni", "hochschule", "schule", "bildung"
   - Subject/content mentions: Universität, Hochschule, Studium, Vorlesung, Prüfung, Zeugnis, Abschluss, Immatrikulation, Semestergebühren
   - Universities: TU (Technische Universität), LMU, FU, Fachhochschule

7. LEGAL & TAX (Always → PERSONAL_HUMAN):
   
   **English Terms:**
   - Subject/content mentions: tax return, assessment, legal notice, court, lawsuit
   
   **German Terms:**
   - Subject/content mentions: Steuerbescheid, Einkommensteuererklärung, Umsatzsteuer, Gewerbesteuer, Mahnung, Gerichtsbescheid, Vollstreckung, Anwalt, Rechtsanwalt, Urteil

DECISION LOGIC:
- If email matches ANY protected pattern above → classify as PERSONAL_HUMAN (even if content looks promotional)
- Check BOTH English AND German terms for multilingual emails
- If domain contains German financial/government terms → automatically protected
- If unsure whether it's a financial/healthcare institution → default to PERSONAL_HUMAN
- ONLY classify as PROMOTIONAL if you're certain it's pure marketing with NO financial/banking/healthcare/government connection

Categories:

1. PROMOTIONAL - Pure marketing (retail, entertainment, general newsletters, deals, discounts)
   Examples: Amazon deals, restaurant promotions, clothing sales, streaming service recommendations, Reiseangebote, Shopping-Newsletter, Rabattaktionen
   
2. TRANSACTIONAL - Purchase confirmations, delivery updates, receipts
   Examples: "Your order has shipped", "Payment received", "Booking confirmation", "Bestellung versendet", "Zahlungsbestätigung", "Lieferbenachrichtigung"
   
3. SYSTEM_SECURITY - Authentication, security alerts, password resets
   Examples: "New login detected", "Reset your password", "2FA code: 123456", "Neuer Login erkannt", "Passwort zurücksetzen", "Sicherheitswarnung"
   
4. SOCIAL_PLATFORM - Social network notifications
   Examples: Facebook friend requests, LinkedIn connection invites, Reddit replies, Medium recommendations, nebenan.de notifications
   
5. PERSONAL_HUMAN - Direct personal/professional correspondence + ALL PROTECTED CATEGORIES above
   Examples: Emails from colleagues, friends, family + anything from banks, investments, healthcare, government, utilities
   Examples DE: E-Mails von Kollegen, Freunden, Familie + alles von Banken, Versicherungen, Gesundheitswesen, Behörden, Stadtwerken

Classify these emails:

{emails_text}

OUTPUT FORMAT - CRITICAL JSON RULES:
- Return ONLY valid JSON array (no markdown, no code blocks)
- NO line breaks in strings
- NO quotes inside strings (use single quotes if needed)
- Use plain ASCII where possible (avoid umlauts in JSON strings)

CORRECT format:
[{{"idx":0,"cat":"promotional","c":85,"reason":"Retail discount offer, no financial/protected indicators (checked EN+DE patterns)","lang":"en"}}, ...]

Fields:
- idx: email index (0, 1, 2, ...)
- cat: category (promotional, transactional, system_security, social_platform, personal_human)
- c: confidence 0-100
- reason: brief explanation INCLUDING why not protected (if promotional) OR which protection triggered (if personal_human). MUST mention checking both EN+DE patterns for bilingual support.
- lang: language code (en or de)

CRITICAL SAFETY RULES: 
- When in doubt about financial/banking/healthcare/government → classify as PERSONAL_HUMAN to be safe
- Check BOTH English AND German patterns for every email
- German government/financial institutions are equally critical as English ones
- Healthcare emails in German (Krankenkasse, Arzttermin) must NEVER be promotional
"""

    def _build_verifier_prompt(
        self,
        emails: List[Dict],
        classifications: List[ClassificationResult],
        promotional_indices: List[int],
    ) -> str:
        """Build Agent 2 verification prompt"""
        promotional_emails = []
        for i in promotional_indices:
            email = emails[i]
            classification = classifications[i]

            email_str = f"""
Email {classification.idx}:
From: {email.get('from', 'unknown')}
Subject: {email.get('subject', '(no subject)')}
Body: {email.get('body', '')[:300]}
Classified as: PROMOTIONAL (confidence: {classification.confidence}%)
Reason: {classification.reason}
"""
            promotional_emails.append(email_str.strip())

        emails_text = "\n\n".join(promotional_emails)

        return f"""Review these PROMOTIONAL classifications for CRITICAL safety errors.

This is a MANDATORY SAFETY CHECK to prevent catastrophic false positives where protected emails are incorrectly classified as promotional.

⚠️ CRITICAL REVIEW PATTERNS - Check EVERY promotional email against these:

1. FINANCIAL SERVICES PATTERNS (MUST be personal_human, NEVER promotional):
   
   **English Patterns:**
   - Domain contains: bank, securities, invest, trading, brokerage, fund, capital, wealth, finance, insurance, life, prudential, asset, mutual
   - Content mentions: portfolio, stocks, shares, mutual fund, trading account, demat, SIP, NAV, dividend, bonds, policy, premium, folio number
   - Regulatory terms: risk disclosure, past performance, SEBI, SEC, BaFin, market risk
   
   **German Patterns:**
   - Domain contains: bank, sparkasse, volksbank, finanz, versicherung, kapital, fonds, depot, wertpapier
   - Content mentions: Depot, Wertpapiere, Aktien, Fonds, Versicherungspolice, Rendite, Dividende, Kapitalanlage
   - Regulatory terms: Risikohinweis, BaFin, Anlageberatung

2. BANKING PATTERNS (MUST be personal_human):
   
   **English Patterns:**
   - Domain contains: bank, credit union
   - Content mentions: account balance, transaction, IBAN, SWIFT, credit card, debit card, loan, mortgage
   - Security alerts: OTP, fraud alert, suspicious transaction
   
   **German Patterns:**
   - Domain contains: bank, sparkasse, volksbank, raiffeisenbank, postbank, sparda
   - Content mentions: Kontostand, Ueberweisung, Girokonto, TAN, Lastschrift, Kreditkarte
   - Security: Sicherheitswarnung, verdaechtige Transaktion

3. GOVERNMENT PATTERNS (MUST be personal_human):
   
   **English Patterns:**
   - Domain ends with: .gov, .gov.in, .gov.de, .gov.uk, .nic.in
   - Content about: taxes, IRS, EPFO, benefits, licenses, permits, voting
   
   **German Patterns:**
   - Domain contains: amt, bundesamt, behoerde, verwaltung
   - Content mentions: Finanzamt, Arbeitsamt, Steuerbescheid, Auslaenderbehoerde, Arbeitsagentur, Bescheid, Genehmigung

4. HEALTHCARE PATTERNS (MUST be personal_human):
   
   **English Patterns:**
   - Domain contains: health, medical, hospital, clinic, pharmacy, doctor, 1mg, pharmeasy, netmeds, apollo
   - Content mentions: appointment, prescription, lab results, medicine, diagnosis, treatment
   
   **German Patterns:**
   - Domain contains: kranken, gesundheit, klinik, arzt, apotheke, medizin
   - Healthcare providers: TK, AOK, Barmer, DAK, IKK
   - Content mentions: Krankenkasse, Arzttermin, Rezept, Krankmeldung, Versichertenkarte, Medikament

5. UTILITIES PATTERNS (Usually personal_human):
   
   **English Patterns:**
   - Domain contains: energy, power, electric, gas, water, telecom
   - Content: bill, payment due, service interruption
   
   **German Patterns:**
   - Domain contains: stadtwerke, energie, strom, gas, telekom, vodafone
   - Content: Rechnung, Stromrechnung, Zaehlerstand, Vertrag

6. EDUCATION PATTERNS (Usually personal_human):
   
   **English Patterns:**
   - Domain ends with: .edu, .ac.in
   - Content: enrollment, grades, tuition, exam
   
   **German Patterns:**
   - Domain contains: uni, hochschule, schule
   - Content: Universitaet, Studium, Pruefung, Immatrikulation

REVIEW INSTRUCTIONS:

For EACH email classified as promotional, check if domain or content matches ANY protected pattern above (English OR German).

If YES → CORRECT to personal_human

Emails to review:
{emails_text}

OUTPUT FORMAT - CRITICAL JSON RULES:
- Return ONLY a valid JSON array
- Keep reason text SHORT (max 50 chars)
- NO line breaks in strings
- NO quotes inside strings (use single quotes if needed)
- Use plain ASCII where possible (avoid umlauts in JSON strings)

CORRECT format:
[{{"idx":0,"cat":"personal_human","c":95,"reason":"Domain has fund+life pattern","lang":"en"}},{{"idx":2,"cat":"personal_human","c":90,"reason":"Healthcare domain pattern","lang":"de"}}]

If all classifications are correct:
[]

Examples of GOOD reasons:
- "Domain has bank pattern"
- "Contains investment terms"
- "Sparkasse detected"
- "Health insurance provider"
- "Government domain .gov.in"

Examples of BAD reasons (will cause errors):
- "Reason with "quotes" inside" (DO NOT USE)
- "Reason with
newline" (DO NOT USE)
- "Überweisung from Sparkasse" (avoid umlauts)

Return ONLY the JSON array, no markdown, no explanations:"""

    # ========================================================================
    # RESPONSE PARSERS
    # ========================================================================

    def _parse_classification_response(
        self,
        response_text: str,
        start_idx: int = 0,
    ) -> List[ClassificationResult]:
        """Parse Agent 1 classification response"""
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('```')[1]
                if cleaned.startswith('json'):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            # Parse JSON
            results_json = json.loads(cleaned)

            results = []
            for item in results_json:
                try:
                    category = EmailCategory(item['cat'].lower())
                except ValueError:
                    # Invalid category - default to PERSONAL_HUMAN
                    category = EmailCategory.PERSONAL_HUMAN

                results.append(
                    ClassificationResult(
                        idx=start_idx + item['idx'],
                        category=category,
                        confidence=float(item['c']),
                        reason=item['reason'],
                        language=item.get('lang', 'unknown'),
                        verified=False,
                    )
                )

            return results

        except Exception as e:
            print(f"Error parsing classification response: {e}")
            print(f"Response: {response_text[:200]}")
            return []

    def _parse_verifier_response(
        self,
        response_text: str,
        start_idx: int = 0,
    ) -> List[ClassificationResult]:
        """Parse Agent 2 verification response (corrections only)"""
        try:
            # Clean response
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('```')[1]
                if cleaned.startswith('json'):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            # Parse JSON
            corrections_json = json.loads(cleaned)

            if not corrections_json:
                # Empty array = no corrections needed
                return []

            corrections = []
            for item in corrections_json:
                try:
                    category = EmailCategory(item['cat'].lower())
                except ValueError:
                    category = EmailCategory.PERSONAL_HUMAN

                corrections.append(
                    ClassificationResult(
                        idx=item['idx'],  # Use absolute idx from response
                        category=category,
                        confidence=float(item['c']),
                        reason=item['reason'],
                        language=item.get('lang', 'unknown'),
                        verified=True,
                    )
                )

            return corrections

        except Exception as e:
            print(f"Error parsing verifier response: {e}")
            print(f"Response: {response_text[:200]}")
            return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test with sample emails (English and German)
    test_emails = [
        {
            "from": "deals@shop.com",
            "subject": "50% OFF Summer Sale!",
            "body": "Don't miss our biggest sale of the year. Use code SUMMER50 for 50% off everything!",
        },
        {
            "from": "alerts@zerodha.com",
            "subject": "Your dividend has been credited",
            "body": "Dear investor, Rs. 1,234 dividend from XYZ Ltd has been credited to your account.",
        },
        {
            "from": "no-reply@amazon.com",
            "subject": "Your order has been shipped",
            "body": "Your order #12345 has been shipped and will arrive by tomorrow.",
        },
        {
            "from": "service@deutsche-bank.de",
            "subject": "Ihre Kontoauszug ist bereit",
            "body": "Sehr geehrter Kunde, Ihr monatlicher Kontoauszug steht jetzt zum Download bereit.",
        },
        {
            "from": "newsletter@techblog.com",
            "subject": "This week in tech news",
            "body": "Top stories: AI breakthrough, new smartphone launch, and more...",
        },
    ]

    print("AI Classifier Test - Dual Agent System")
    print("=" * 80)

    # Test with Gemini (if API key available)
    if os.getenv('GEMINI_API_KEY'):
        print("\nTesting with Gemini 2.0 Flash...")
        classifier = AIClassifier(provider=AIProvider.GEMINI)

        results = classifier.classify_batch(test_emails)

        print(f"\nClassified {len(results)} emails:\n")
        for result in results:
            verified_str = " [VERIFIED]" if result.verified else " [NOT VERIFIED]"
            print(f"{result.idx}. {result.category.value.upper()}{verified_str}")
            print(f"   Confidence: {result.confidence}%")
            print(f"   Language: {result.language}")
            print(f"   Reason: {result.reason}")
            print()

    else:
        print("\nSkipping test - GEMINI_API_KEY not set")

    print("=" * 80)
