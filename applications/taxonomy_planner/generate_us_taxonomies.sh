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

# Check if category is provided
if [ -z "$1" ]
then
    echo "Error: Root category must be specified"
    echo "Usage: $0 <root_category>"
    echo "Example: $0 'Alcohol'"
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

# Run the compliance taxonomy generator
echo "Generating US compliance taxonomy for $1..."
python generate_compliance_taxonomies.py "$1" \
    --jurisdictions "USA" \
    --max-depth 4 \
    --breadth-limit 10 \
    --strategy "parallel"

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