#!/usr/bin/env python
"""
Test script for externalized prompts integration.

This script tests the patterns that have been refactored to use 
externalized prompt templates from YAML files.
"""

import os
import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.integration.test_patterns_integration import (
    test_self_consistency_pattern,
    test_expert_panel_pattern,
    test_few_shot_pattern,
    symphony_with_agent
)


async def main():
    """Run integration tests for externalized prompts."""
    
    parser = argparse.ArgumentParser(description='Run pattern integration tests with externalized prompts')
    parser.add_argument('--pattern', choices=['self_consistency', 'expert_panel', 'few_shot', 'all'], 
                        default='all', help='Which pattern to test (default: all)')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                        help='Model to use for testing (default: gpt-4o-mini)')
    args = parser.parse_args()
    
    # Set model for testing
    os.environ["INTEGRATION_TEST_MODEL"] = args.model
    
    # Create Symphony instance with agent
    print(f"Initializing Symphony with model: {args.model}")
    sym_agent = await symphony_with_agent()
    
    # Run tests
    if args.pattern == 'all' or args.pattern == 'self_consistency':
        print("\nTesting Self-Consistency pattern...")
        await test_self_consistency_pattern(sym_agent)
    
    if args.pattern == 'all' or args.pattern == 'expert_panel':
        print("\nTesting Expert Panel pattern...")
        await test_expert_panel_pattern(sym_agent)
    
    if args.pattern == 'all' or args.pattern == 'few_shot':
        print("\nTesting Few-Shot Learning pattern...")
        await test_few_shot_pattern(sym_agent)
    
    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())