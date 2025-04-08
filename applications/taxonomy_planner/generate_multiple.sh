#!/bin/bash
# Generate multiple taxonomies in one go

# Set API keys from environment or .env file if available
# DO NOT hardcode API keys in scripts - use environment variables instead
[ -f .env ] && source .env
OPENAI_API_KEY=${OPENAI_API_KEY:-"YOUR_OPENAI_API_KEY"}
SERAPI_API_KEY=${SERAPI_API_KEY:-"YOUR_SERAPI_API_KEY"}

# Export for script usage
export OPENAI_API_KEY
export SERAPI_API_KEY

# Check if categories are provided
if [ -z "$1" ]; then
    echo "Error: Categories must be specified"
    echo "Usage: $0 \"Category1,Category2,Category3\" [output_dir]"
    echo "Example: $0 \"Sports,Finance,Technology\""
    exit 1
fi

# Set output directory
OUTPUT_DIR="output/multiple"
if [ ! -z "$2" ]; then
    OUTPUT_DIR="$2"
fi

# Create output directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "storage/multiple"

echo "Starting generation of taxonomies for: $1"
echo "Output will be saved to: $OUTPUT_DIR"

# Run the Python script with the provided categories
python generate_multiple.py "$1" \
    --output-dir "$OUTPUT_DIR" \
    --storage-dir "storage/multiple" \
    --jurisdictions "USA" \
    --max-depth 4 \
    --breadth-limit 10 \
    --strategy "parallel" \
    --planner-model "o1-mini" \
    --explorer-model "gpt-4o-mini" \
    --compliance-model "gpt-4o-mini" \
    --legal-model "gpt-4o-mini"

if [ $? -eq 0 ]; then
    echo "Successfully generated all taxonomies!"
    echo "Output saved to $OUTPUT_DIR"
    
    # List the generated taxonomies
    echo ""
    echo "Generated taxonomies:"
    ls -la "$OUTPUT_DIR"/*_taxonomy.json
    
    # Create analysis directory
    mkdir -p "analysis/$OUTPUT_DIR"
    
    # Analyze all trace files
    echo ""
    echo "Analyzing trace files..."
    for trace in traces/taxonomy_generation/trace_*.jsonl; do
        if [ -f "$trace" ]; then
            filename=$(basename "$trace" .jsonl)
            echo "Analyzing $trace..."
            python analyze_traces.py "$trace" --output-dir "analysis/$OUTPUT_DIR" --prefix "$filename"
        fi
    done
    
    echo ""
    echo "All done! Analysis results available in analysis/$OUTPUT_DIR"
else
    echo "Error generating taxonomies"
    exit 1
fi