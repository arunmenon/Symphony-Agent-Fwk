#!/bin/bash
# Generate US compliance taxonomies for regulated domains

# Set API keys from environment or .env file if available
# DO NOT hardcode API keys in scripts - use environment variables instead
[ -f .env ] && source .env
OPENAI_API_KEY=${OPENAI_API_KEY:-"YOUR_OPENAI_API_KEY"}
SERAPI_API_KEY=${SERAPI_API_KEY:-"YOUR_SERAPI_API_KEY"}

# Export for script usage
export OPENAI_API_KEY
export SERAPI_API_KEY

# Check if enhanced mode flag is provided
ENHANCED=false
if [ "$1" == "--enhanced" ] || [ "$1" == "-e" ]; then
    ENHANCED=true
    shift
fi

# Check if category is provided
if [ -z "$1" ]
then
    echo "Error: Root category must be specified"
    echo "Usage: $0 [--enhanced|-e] <root_category>"
    echo "Example: $0 'Alcohol'"
    echo "Example with enhanced mode: $0 --enhanced 'Alcohol'"
    echo ""
    echo "Common regulatory domains:"
    echo "  - Alcohol"
    echo "  - Weapons"
    echo "  - Pharmaceuticals"
    echo "  - Gambling"
    echo "  - Tobacco"
    echo "  - Financial Securities"
    exit 1
fi

# Set up command
CMD="python generate_taxonomy.py \"$1\" --jurisdictions \"USA\" --max-depth 4 --breadth-limit 10 --strategy \"parallel\" --output-dir \"output/us_jurisdictions\""

# Add enhanced flag if needed
if [ "$ENHANCED" = true ]; then
    echo "Generating ENHANCED US compliance taxonomy for $1 with additional fields..."
    CMD="$CMD --enhanced"
else
    echo "Generating standard US compliance taxonomy for $1..."
fi

# Run the taxonomy generator
eval $CMD

if [ $? -eq 0 ]; then
    echo "Successfully generated taxonomy for $1"
    # Convert to lowercase without using lowercase expansion (for wider shell compatibility)
    CATEGORY_LOWER=$(echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    OUTPUT_PATH="output/us_jurisdictions/${CATEGORY_LOWER}_taxonomy.json"
    
    echo "Output saved to $OUTPUT_PATH"
    
    # Optionally visualize the taxonomy if the visualize script exists
    if [ -f "visualize_taxonomy.py" ]; then
        echo ""
        echo "To visualize this taxonomy, run:"
        echo "python visualize_taxonomy.py $OUTPUT_PATH"
    fi
else
    echo "Error generating taxonomy"
    exit 1
fi