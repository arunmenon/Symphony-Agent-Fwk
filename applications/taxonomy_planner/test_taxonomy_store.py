#!/usr/bin/env python
"""A simple test script for the TaxonomyStore class."""

import os
import json
from persistence import TaxonomyStore

def main():
    """Run a simple test of the TaxonomyStore."""
    # Create output directories
    os.makedirs("output/test", exist_ok=True)
    
    # Create a store
    store = TaxonomyStore(storage_path="output/test/weapons_store.json")
    
    # Add some categories
    store.add_node("Weapons")  # Root
    
    # Level 1 categories
    store.add_node("Firearms", parent="Weapons")
    store.add_node("Bladed Weapons", parent="Weapons")
    store.add_node("Explosives", parent="Weapons")
    
    # Level 2 categories
    store.add_node("Handguns", parent="Firearms")
    store.add_node("Rifles", parent="Firearms")
    store.add_node("Shotguns", parent="Firearms")
    
    store.add_node("Knives", parent="Bladed Weapons")
    store.add_node("Swords", parent="Bladed Weapons")
    
    store.add_node("Grenades", parent="Explosives")
    store.add_node("Mines", parent="Explosives")
    
    # Add some compliance mappings
    store.add_compliance_mapping("Firearms", "USA", {
        "regulations": ["ATF Regulations", "NFA Restrictions"],
        "standards": ["BATFE Standards"]
    })
    
    store.add_legal_mapping("Firearms", "USA", {
        "laws": ["Second Amendment", "Gun Control Act of 1968"],
        "restrictions": ["State and local laws vary"]
    })
    
    # Save the store
    store.save()
    
    # Generate the taxonomy tree
    taxonomy = store.get_taxonomy_tree("Weapons")
    
    # Add metadata
    taxonomy["metadata"] = {
        "generated_at": "2024-04-08T12:34:56.789012",
        "max_depth": 4,
        "jurisdictions": ["USA"],
        "note": "This is a test taxonomy generated with o1-mini planner and gpt-4o-mini exploration"
    }
    
    # Save the taxonomy as JSON
    output_path = "output/test/weapons_taxonomy.json"
    with open(output_path, 'w') as f:
        json.dump(taxonomy, f, indent=2)
    
    print(f"Generated test taxonomy with {len(taxonomy['subcategories'])} top-level categories")
    print(f"Saved to {output_path}")
    
    # Print the structure
    print("\nTaxonomy Structure:")
    print(f"- {taxonomy['category']}")
    for cat in taxonomy['subcategories']:
        print(f"  - {cat['category']}")
        for subcat in cat.get('subcategories', []):
            print(f"    - {subcat['category']}")
    
    # Check compliance mappings
    print("\nCompliance Mappings:")
    for cat_name, cat_data in [("Firearms", "Firearms")]:
        compliance = store.get_compliance_mapping(cat_data, "USA")
        if compliance:
            print(f"  - {cat_name}: {compliance}")
    
    return taxonomy

if __name__ == "__main__":
    main()