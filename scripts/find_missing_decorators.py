#!/usr/bin/env python
"""Find API components missing stability decorators.

This script analyzes the __all__ list in symphony/api.py and compares it with
the components that have been decorated with @api_stable.
"""

import os
import sys
import re
from typing import List, Dict, Set

def parse_all_exports(api_file: str) -> Set[str]:
    """Parse the __all__ list from the API file."""
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Find the __all__ list
    match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        return set()
    
    # Extract the names from the list
    all_list = match.group(1)
    names = re.findall(r"'([^']+)'", all_list)
    return set(names)

def parse_decorated_components(api_file: str) -> Set[str]:
    """Parse components that have been decorated with @api_stable."""
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Find direct applications of api_stable decorator to variables 
    decorated = set(re.findall(r'([A-Za-z0-9_]+)\s*=\s*api_stable\(', content))
    
    # Find class definitions with decorator
    class_matches = re.findall(r'@api_stable\([^)]*\)\s*class\s+([A-Za-z0-9_]+)', content, re.DOTALL)
    decorated.update(class_matches)
    
    # Find Symphony class specifically (special case)
    if 'Symphony' not in decorated and '@api_stable' in content and 'class Symphony' in content:
        decorated.add('Symphony')
    
    return decorated

def main():
    """Main function."""
    if not os.path.exists('symphony/api.py'):
        print("Error: Cannot find symphony/api.py. Run from the project root directory.")
        sys.exit(1)
    
    all_exports = parse_all_exports('symphony/api.py')
    decorated = parse_decorated_components('symphony/api.py')
    
    missing = all_exports - decorated
    
    if missing:
        print("The following API components are missing @api_stable decorators:")
        for name in sorted(missing):
            print(f"- {name}")
        sys.exit(1)
    else:
        print("All API components in __all__ are properly decorated with @api_stable!")
        sys.exit(0)

if __name__ == "__main__":
    main()