#!/usr/bin/env python3
"""
Setup Validation Script
Checks if the Gmail Email Classifier is properly configured
"""

import os
import sys
from colorama import init, Fore, Style

init(autoreset=True)


def check_python_version():
    """Check Python version"""
    print(f"{Fore.CYAN}Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"{Fore.GREEN}✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"{Fore.RED}✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print(f"\n{Fore.CYAN}Checking dependencies...")
    required_packages = [
        "google.auth",
        "google_auth_oauthlib",
        "googleapiclient",
        "google.generativeai",
        "anthropic",
        "dotenv",
        "pydantic",
        "pandas",
        "matplotlib",
        "sklearn",
        "tqdm",
        "colorama",
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"{Fore.GREEN}✓ {package}")
        except ImportError:
            print(f"{Fore.RED}✗ {package} (run: pip install -r requirements.txt)")
            all_installed = False

    return all_installed


def check_env_file():
    """Check if .env file exists and has required variables"""
    print(f"\n{Fore.CYAN}Checking .env configuration...")

    if not os.path.exists('.env'):
        print(f"{Fore.RED}✗ .env file not found")
        print(f"{Fore.YELLOW}  Run: cp .env.example .env")
        return False

    print(f"{Fore.GREEN}✓ .env file exists")

    # Load and check for API keys
    from dotenv import load_dotenv
    load_dotenv()

    checks = []

    # Gmail credentials
    gmail_client_id = os.getenv('GMAIL_CLIENT_ID')
    if gmail_client_id and 'your-client-id' not in gmail_client_id:
        print(f"{Fore.GREEN}✓ GMAIL_CLIENT_ID set")
        checks.append(True)
    else:
        print(f"{Fore.YELLOW}⚠ GMAIL_CLIENT_ID not configured")
        checks.append(False)

    # AI provider (at least one required)
    gemini_key = os.getenv('GEMINI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')

    if gemini_key and 'your-' not in gemini_key:
        print(f"{Fore.GREEN}✓ GEMINI_API_KEY set")
        checks.append(True)
    elif anthropic_key and 'your-' not in anthropic_key:
        print(f"{Fore.GREEN}✓ ANTHROPIC_API_KEY set")
        checks.append(True)
    else:
        print(f"{Fore.RED}✗ No AI provider API key configured")
        print(f"{Fore.YELLOW}  Set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env")
        checks.append(False)

    return all(checks)


def check_gmail_credentials():
    """Check if Gmail OAuth credentials exist"""
    print(f"\n{Fore.CYAN}Checking Gmail credentials...")

    if os.path.exists('credentials.json'):
        print(f"{Fore.GREEN}✓ credentials.json exists")
        return True
    else:
        print(f"{Fore.YELLOW}⚠ credentials.json not found")
        print(f"{Fore.YELLOW}  Download from Google Cloud Console")
        print(f"{Fore.YELLOW}  See README.md for setup instructions")
        return False


def check_config_validation():
    """Check if config.py is valid"""
    print(f"\n{Fore.CYAN}Checking configuration validation...")

    try:
        import config
        print(f"{Fore.GREEN}✓ config.py validated successfully")
        print(f"{Fore.GREEN}  Protected domains loaded for all markets")
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ Configuration validation failed: {e}")
        return False


def check_directory_structure():
    """Check if required directories exist"""
    print(f"\n{Fore.CYAN}Checking directory structure...")

    dirs = ['logs', 'classification_results', 'plots']
    all_exist = True

    for d in dirs:
        if not os.path.exists(d):
            print(f"{Fore.YELLOW}⚠ Creating {d}/")
            os.makedirs(d, exist_ok=True)
        else:
            print(f"{Fore.GREEN}✓ {d}/")

    return True


def run_quick_tests():
    """Run quick functionality tests"""
    print(f"\n{Fore.CYAN}Running quick functionality tests...")

    try:
        # Test domain checker
        from config import Market
        from domain_checker import DomainChecker

        checker = DomainChecker(Market.ALL)
        result = checker.check_domain("alerts@zerodha.com")

        if result.is_protected and result.market.value == "india":
            print(f"{Fore.GREEN}✓ Domain checker working")
        else:
            print(f"{Fore.RED}✗ Domain checker test failed")
            return False

        # Test decision engine
        from decision_engine import DecisionEngine

        engine = DecisionEngine(checker)
        result = engine.evaluate(
            email_id="test",
            category="promotional",
            confidence=95.0,
            verified=True,
            from_address="alerts@zerodha.com",
            is_starred=False,
            is_important=False,
        )

        if result.decision.value == "rejected":
            print(f"{Fore.GREEN}✓ Decision engine working (protected domain correctly rejected)")
        else:
            print(f"{Fore.RED}✗ Decision engine test failed")
            return False

        print(f"{Fore.GREEN}✓ All functionality tests passed")
        return True

    except Exception as e:
        print(f"{Fore.RED}✗ Functionality test failed: {e}")
        return False


def print_summary(results):
    """Print validation summary"""
    print(f"\n{'='*80}")
    print(f"{Fore.CYAN}VALIDATION SUMMARY")
    print(f"{'='*80}\n")

    all_passed = all(results.values())

    for check, passed in results.items():
        status = f"{Fore.GREEN}✓" if passed else f"{Fore.RED}✗"
        print(f"{status} {check}")

    print(f"\n{'='*80}\n")

    if all_passed:
        print(f"{Fore.GREEN}✓ All checks passed! System is ready to use.")
        print(f"\n{Fore.CYAN}Next steps:")
        print(f"{Fore.WHITE}  1. Authenticate with Gmail: python gmail_client.py")
        print(f"{Fore.WHITE}  2. Run dry-run test: python email_classifier.py --max-emails 10")
        print(f"{Fore.WHITE}  3. Review results in classification_results/")
    else:
        print(f"{Fore.YELLOW}⚠ Some checks failed. Please fix the issues above.")
        print(f"\n{Fore.CYAN}Common fixes:")
        print(f"{Fore.WHITE}  - Dependencies: pip install -r requirements.txt")
        print(f"{Fore.WHITE}  - Environment: cp .env.example .env (then edit .env)")
        print(f"{Fore.WHITE}  - Gmail credentials: Download from Google Cloud Console")

    return all_passed


def main():
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Gmail Email Classifier - Setup Validation")
    print(f"{Fore.CYAN}{'='*80}\n")

    results = {
        "Python version": check_python_version(),
        "Dependencies installed": check_dependencies(),
        "Environment configured": check_env_file(),
        "Gmail credentials": check_gmail_credentials(),
        "Configuration valid": check_config_validation(),
        "Directory structure": check_directory_structure(),
        "Functionality tests": run_quick_tests(),
    }

    passed = print_summary(results)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
