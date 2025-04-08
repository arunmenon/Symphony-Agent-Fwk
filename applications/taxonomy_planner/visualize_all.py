#!/usr/bin/env python
"""Visualize all taxonomies in the output directory as HTML tree views."""

import os
import argparse
import logging
import glob
from typing import List, Optional
import asyncio
import json

from visualize_taxonomy import visualize_taxonomy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# HTML template for index page
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taxonomy Visualizations</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .taxonomy-list {
            margin-top: 20px;
        }
        .taxonomy-item {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .taxonomy-item:hover {
            background-color: #e9ecef;
        }
        .taxonomy-item a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: bold;
        }
        .taxonomy-item a:hover {
            text-decoration: underline;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 0.8em;
            color: #7f8c8d;
        }
        .metadata {
            font-size: 0.8em;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Taxonomy Visualizations</h1>
        
        <div class="taxonomy-list">
            {taxonomy_items}
        </div>
        
        <div class="footer">
            Generated by Taxonomy Planner Visualization Tool
        </div>
    </div>
</body>
</html>
"""

TAXONOMY_ITEM_TEMPLATE = """
<div class="taxonomy-item">
    <div>
        <a href="{html_path}">{name}</a>
        <div class="metadata">Generated: {generated_at} | Model: {model} | Categories: {category_count}</div>
    </div>
</div>
"""

async def visualize_all_taxonomies(
    input_dir: str = "output",
    output_dir: Optional[str] = None,
    pattern: str = "*_taxonomy.json"
) -> List[str]:
    """Visualize all taxonomies matching the pattern in the input directory.
    
    Args:
        input_dir: Directory containing taxonomy JSON files
        output_dir: Directory to save HTML output files (default: html subdirectory of input_dir)
        pattern: Glob pattern to match taxonomy files
        
    Returns:
        List of generated HTML file paths
    """
    # Set default output directory if not provided
    if not output_dir:
        output_dir = os.path.join(input_dir, "html")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all taxonomy files
    search_pattern = os.path.join(input_dir, pattern)
    taxonomy_files = glob.glob(search_pattern)
    
    if not taxonomy_files:
        logger.warning(f"No taxonomy files found matching pattern: {search_pattern}")
        return []
    
    logger.info(f"Found {len(taxonomy_files)} taxonomy files")
    
    # Visualize each taxonomy
    html_files = []
    taxonomy_info = []
    
    for taxonomy_file in taxonomy_files:
        try:
            # Load taxonomy to get metadata
            with open(taxonomy_file, 'r') as f:
                taxonomy = json.load(f)
            
            name = taxonomy.get("name", os.path.basename(taxonomy_file).replace("_taxonomy.json", "").title())
            metadata = taxonomy.get("metadata", {})
            generated_at = metadata.get("generated_at", "Unknown")
            model = metadata.get("model", "Unknown")
            category_count = count_categories(taxonomy)
            
            # Generate HTML file
            output_file = os.path.join(output_dir, os.path.basename(taxonomy_file).replace(".json", ".html"))
            html_file = visualize_taxonomy(taxonomy_file, output_file)
            html_files.append(html_file)
            
            # Store info for index page
            taxonomy_info.append({
                "name": name,
                "html_path": os.path.basename(html_file),
                "generated_at": generated_at,
                "model": model,
                "category_count": category_count
            })
            
        except Exception as e:
            logger.error(f"Error visualizing taxonomy {taxonomy_file}: {e}")
    
    # Generate index page
    if html_files:
        # Sort by name
        taxonomy_info.sort(key=lambda x: x["name"])
        
        # Generate items HTML
        items_html = ""
        for info in taxonomy_info:
            items_html += TAXONOMY_ITEM_TEMPLATE.format(
                html_path=info["html_path"],
                name=info["name"],
                generated_at=info["generated_at"],
                model=info["model"],
                category_count=info["category_count"]
            )
        
        # Generate index HTML
        index_html = INDEX_TEMPLATE.format(taxonomy_items=items_html)
        
        # Save index HTML
        index_path = os.path.join(output_dir, "index.html")
        with open(index_path, 'w') as f:
            f.write(index_html)
        
        logger.info(f"Generated index page at {index_path}")
        html_files.append(index_path)
    
    return html_files

def count_categories(node):
    """Count total number of categories in the taxonomy."""
    count = 1  # Count current node
    
    if "subcategories" in node and node["subcategories"]:
        for subcategory in node["subcategories"]:
            count += count_categories(subcategory)
    
    return count

async def main():
    """Parse arguments and run the visualization."""
    parser = argparse.ArgumentParser(description="Visualize all taxonomies as HTML tree views")
    
    parser.add_argument(
        "--input-dir",
        help="Directory containing taxonomy JSON files (default: output)",
        default="output"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save HTML output files (default: input_dir/html)",
        default=None
    )
    
    parser.add_argument(
        "--pattern",
        help="Glob pattern to match taxonomy files (default: *_taxonomy.json)",
        default="*_taxonomy.json"
    )
    
    args = parser.parse_args()
    
    try:
        html_files = await visualize_all_taxonomies(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            pattern=args.pattern
        )
        
        if html_files:
            index_path = [f for f in html_files if f.endswith("index.html")][0]
            logger.info(f"Visualization complete! Open {index_path} in a web browser to view all taxonomies.")
        else:
            logger.warning("No taxonomies were visualized.")
        
    except Exception as e:
        logger.error(f"Error visualizing taxonomies: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())