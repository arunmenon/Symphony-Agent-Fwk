#!/usr/bin/env python
"""Runner script for Symphony integration tests.

This script runs integration tests for Symphony patterns using OpenAI models.
It requires a valid OpenAI API key to be set in the environment.
"""

import os
import sys
import argparse
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Symphony integration tests")
    parser.add_argument(
        "--pattern", "-p", 
        help="Run tests for a specific pattern (e.g. 'chain_of_thought')"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true", 
        help="Show which tests would run without executing them"
    )
    return parser.parse_args()


def check_environment():
    """Check if the environment is properly configured."""
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Create a .env file based on .env.example or set it directly.")
        return False
    return True


def run_integration_tests(pattern=None, verbose=False, dry_run=False):
    """Run the integration tests."""
    test_path = "tests/integration"
    if pattern:
        test_path += f" -k {pattern}"
    
    cmd = ["python", "-m", "pytest", test_path]
    if verbose:
        cmd.append("-v")
    if dry_run:
        cmd.append("--collect-only")
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    """Main entry point."""
    args = parse_args()
    
    if not check_environment():
        return 1
    
    print("Running Symphony Integration Tests")
    print("=================================")
    
    return run_integration_tests(
        pattern=args.pattern,
        verbose=args.verbose,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    sys.exit(main())