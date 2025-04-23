#!/usr/bin/env python
"""Check that all public API components are decorated with @api_stable.

This script analyzes the Symphony API module and exits with a non-zero code
if any components in __all__ are missing the @api_stable decorator.
"""

import importlib
import inspect
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_api_exports():
    """Get the list of exports from __all__ by parsing the API file directly."""
    api_file = project_root / "symphony" / "api.py"
    
    with open(api_file, "r") as f:
        content = f.read()
    
    # Extract __all__ list using regex
    import re
    match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        print("Error: Could not find __all__ list in symphony/api.py")
        return []
    
    # Extract the names from the list
    all_list = match.group(1)
    names = re.findall(r"'([^']+)'", all_list)
    return names


def get_decorated_symbols():
    """Get all symbols that are decorated with @api_stable."""
    api_file = project_root / "symphony" / "api.py"
    decorated = set()
    
    with open(api_file, "r") as f:
        content = f.read()
    
    import re
    
    # Find class definitions with decorator
    class_matches = re.findall(r'@api_stable\([^)]*\)\s*class\s+([A-Za-z0-9_]+)', content, re.DOTALL)
    decorated.update(class_matches)
    
    # Find direct applications of api_stable decorator to variables
    var_matches = re.findall(r'([A-Za-z0-9_]+)\s*=\s*api_stable\(', content)
    decorated.update(var_matches)
    
    return decorated


def check_api_decorators():
    """Check which API components are missing @api_stable decorators."""
    exports = get_api_exports()
    if not exports:
        print("Error: Could not find exports in symphony.api")
        return ["Could not parse API module"]
    
    decorated = get_decorated_symbols()
    missing = []
    
    for name in exports:
        if name not in decorated:
            missing.append(name)
    
    return missing


if __name__ == "__main__":
    missing = check_api_decorators()
    
    if missing:
        print("The following API components are missing @api_stable decorators:")
        for name in missing:
            print(f"- {name}")
        sys.exit(1)
    else:
        print("All API components are properly decorated with @api_stable!")
        sys.exit(0)