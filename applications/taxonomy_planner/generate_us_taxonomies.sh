#!/bin/bash
# Generate US compliance taxonomies with the specified OpenAI and SerpAPI keys

# Set API keys from environment or .env file if available
# DO NOT hardcode API keys in scripts - use environment variables instead
[ -f .env ] && source .env
OPENAI_API_KEY=${OPENAI_API_KEY:-"YOUR_OPENAI_API_KEY"}
SERAPI_API_KEY=${SERAPI_API_KEY:-"YOUR_SERAPI_API_KEY"}

# Export for script usage
export OPENAI_API_KEY
export SERAPI_API_KEY

# Create output directories if they don't exist
mkdir -p output/us_jurisdictions
mkdir -p storage/us_jurisdictions

# Check if category is provided
if [ -z "$1" ]
then
    echo "Error: Root category must be specified"
    echo "Usage: $0 <root_category>"
    echo "Example: $0 'Nudity'"
    exit 1
fi

# Run the taxonomy generator with US jurisdictions
echo "Generating US compliance taxonomy for $1..."
python generate_taxonomy.py "$1" \
    --jurisdictions "USA" \
    --output-dir "output/us_jurisdictions" \
    --storage-dir "storage/us_jurisdictions" \
    --max-depth 4 \
    --breadth-limit 10 \
    --strategy "parallel" \
    --planner-model "o1-mini" \
    --explorer-model "gpt-4o-mini" \
    --compliance-model "gpt-4o-mini" \
    --legal-model "gpt-4o-mini"

if [ $? -eq 0 ]; then
    echo "Successfully generated taxonomy for $1"
    # Convert to lowercase without using lowercase expansion (for wider shell compatibility)
    CATEGORY_LOWER=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    echo "Output saved to output/us_jurisdictions/${CATEGORY_LOWER}_taxonomy.json"
else
    echo "Error generating taxonomy"
    exit 1
fi