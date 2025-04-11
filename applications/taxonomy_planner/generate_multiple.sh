#!/bin/bash
# Generate multiple enhanced taxonomies using the correct Symphony agent execution pattern

# Set API keys from environment or .env file if available
[ -f .env ] && source .env
OPENAI_API_KEY=${OPENAI_API_KEY:-"YOUR_OPENAI_API_KEY"}
SERAPI_API_KEY=${SERAPI_API_KEY:-"YOUR_SERAPI_API_KEY"}

# Export for script usage
export OPENAI_API_KEY
export SERAPI_API_KEY

# Function to display usage
function show_usage {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --categories      List of categories to generate (comma-separated)"
    echo "  -j, --jurisdictions   List of jurisdictions to consider (comma-separated, default: USA,EU,International)"
    echo "  -e, --enhanced        Use enhanced taxonomy with additional fields (default: false)" 
    echo "  -o, --output-dir      Output directory (default: output/multiple)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Example: $0 --categories 'Alcohol,Weapons,Nudity' --enhanced"
    exit 1
}

# Default values
CATEGORIES=""
JURISDICTIONS="USA,EU,International"
ENHANCED=false
OUTPUT_DIR="output/multiple"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -c|--categories)
        CATEGORIES="$2"
        shift 2
        ;;
        -j|--jurisdictions)
        JURISDICTIONS="$2"
        shift 2
        ;;
        -e|--enhanced)
        ENHANCED=true
        shift
        ;;
        -o|--output-dir)
        OUTPUT_DIR="$2"
        shift 2
        ;;
        -h|--help)
        show_usage
        ;;
        *)
        echo "Unknown option: $1"
        show_usage
        ;;
    esac
done

# Check if categories are provided
if [ -z "$CATEGORIES" ]; then
    echo "Error: No categories specified."
    show_usage
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Convert comma-separated list to array
IFS=',' read -ra CATEGORY_ARRAY <<< "$CATEGORIES"

# Generate taxonomies for each category
for category in "${CATEGORY_ARRAY[@]}"; do
    echo ""
    echo "=========================================="
    echo "Generating taxonomy for: $category"
    echo "Using jurisdictions: $JURISDICTIONS"
    echo "Enhanced mode: $ENHANCED"
    echo "=========================================="
    
    # Prepare command
    CMD="python generate_taxonomy.py \"$category\" --jurisdictions \"$JURISDICTIONS\" --output-dir \"$OUTPUT_DIR\""
    
    # Add enhanced flag if enabled
    if [ "$ENHANCED" = true ]; then
        CMD="$CMD --enhanced"
    fi
    
    # Execute command
    echo "Running: $CMD"
    eval $CMD
    
    # Check if successful
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Successfully generated taxonomy for $category"
    else
        echo ""
        echo "❌ Failed to generate taxonomy for $category"
    fi
done

echo ""
echo "=========================================="
echo "Taxonomy generation complete!"
echo "Generated taxonomies saved to: $OUTPUT_DIR"
echo "=========================================="

# List generated taxonomies
ls -la "$OUTPUT_DIR"/*.json