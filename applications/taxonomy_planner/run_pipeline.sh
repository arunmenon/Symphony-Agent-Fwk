#!/bin/bash
# Run the full taxonomy generation pipeline with API keys

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
OUTPUT_DIR="pipeline_output_$(date +%Y%m%d_%H%M%S)"
if [ ! -z "$2" ]; then
    OUTPUT_DIR="$2"
fi

echo "Starting full taxonomy pipeline for: $1"
echo "Output will be saved to: $OUTPUT_DIR"

# Run the Python pipeline script
python run_full_pipeline.py "$1" \
    --output-dir "$OUTPUT_DIR" \
    --jurisdictions "USA" \
    --max-depth 4 \
    --breadth-limit 10 \
    --strategy "parallel" \
    --planner-model "o1-mini" \
    --explorer-model "gpt-4o-mini" \
    --compliance-model "gpt-4o-mini" \
    --legal-model "gpt-4o-mini"

if [ $? -eq 0 ]; then
    echo "Pipeline completed successfully!"
    
    # Open the visualization index if it exists
    VISUALIZATION_INDEX="$OUTPUT_DIR/visualizations/index.html"
    if [ -f "$VISUALIZATION_INDEX" ]; then
        echo "You can view the taxonomies by opening:"
        echo "$VISUALIZATION_INDEX"
        
        # Try to open it automatically if we're on macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "$VISUALIZATION_INDEX"
        fi
    fi
    
    # Print analysis location
    ANALYSIS_DIR="$OUTPUT_DIR/analysis"
    if [ -d "$ANALYSIS_DIR" ]; then
        echo "Analysis results available in:"
        echo "$ANALYSIS_DIR"
    fi
else
    echo "Pipeline failed. Check the logs for details."
    exit 1
fi