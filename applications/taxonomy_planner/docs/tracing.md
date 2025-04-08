# LLM Tracing and Analysis in Taxonomy Planner

The Taxonomy Planner includes a robust tracing system for monitoring, debugging, and analyzing model calls. This document explains how to use and extend these capabilities.

## Overview

The tracing system captures detailed information about:
- Model requests (prompts, parameters)
- Model responses (content, timing)
- Errors and exceptions
- Performance metrics

All trace data is stored in JSONL (JSON Lines) format for easy processing and analysis.

## Trace Generation

Tracing is enabled by default when generating taxonomies. Each taxonomy generation session creates a unique trace file in the `traces/taxonomy_generation/` directory.

### Trace File Format

Trace files use the following format:
```
{"type": "session_start", "timestamp": "2025-04-08T19:41:59.345040", "session_id": "7f5cdcdc-afcc-46be-8f38-9c59c541392b"}
{"type": "llm_request", "timestamp": "2025-04-08T19:42:01.123456", "session_id": "7f5cdcdc-afcc-46be-8f38-9c59c541392b", "data": {...}}
{"type": "llm_response", "timestamp": "2025-04-08T19:42:05.678901", "session_id": "7f5cdcdc-afcc-46be-8f38-9c59c541392b", "data": {...}}
{"type": "session_end", "timestamp": "2025-04-08T19:42:10.234567", "session_id": "7f5cdcdc-afcc-46be-8f38-9c59c541392b", "duration_seconds": 10.889527}
```

Each line is a complete JSON object representing a single event in the tracing session.

## Analyzing Traces

### Command Line Tool

The `analyze_traces.py` script generates insights and visualizations from trace files:

```bash
# Basic usage
python analyze_traces.py traces/taxonomy_generation/trace_123abc.jsonl

# Custom output directory
python analyze_traces.py traces/taxonomy_generation/trace_123abc.jsonl --output-dir "analysis/custom"

# Custom prefix for output files
python analyze_traces.py traces/taxonomy_generation/trace_123abc.jsonl --prefix "finance_taxonomy"
```

### Analysis Output

The analysis generates:

1. **Summary Report** - A text file with key metrics:
   - Request/response counts
   - Error counts
   - Response time statistics
   - Models used

2. **Visualizations**:
   - Response time distribution histogram
   - Model usage bar chart

### Batch Analysis

You can analyze multiple trace files at once using the `generate_multiple.sh` script, which automatically runs analysis on all generated taxonomies:

```bash
# Generate and analyze multiple taxonomies
./generate_multiple.sh "Sports,Finance,Technology"
```

## Using the Tracing Plugin

### Basic Usage

The LLM tracing plugin can be used as a decorator in your code:

```python
from llm_tracing_plugin import LLMTracingPlugin

# Create a tracer instance
tracer = LLMTracingPlugin(trace_dir="my_traces")

# Use as a decorator
@tracer.trace_model_call
async def my_model_function(model, prompt):
    # Your model calling code here
    return response
```

### Advanced Integration

For more advanced integration, you can use the event system:

```python
# Log custom events
tracer.log_event("custom_event", {
    "category": "taxonomy_processing",
    "node_count": 25,
    "depth": 3
})

# Add custom session metadata
with open(tracer.trace_file, 'a') as f:
    metadata = {
        "type": "session_metadata",
        "timestamp": datetime.now().isoformat(),
        "session_id": tracer.session_id,
        "data": {
            "user": "researcher1",
            "project": "finance_taxonomy",
            "version": "1.2.3"
        }
    }
    f.write(json.dumps(metadata) + "\n")
```

## Symphony Framework Integration

The `LLMTracingPlugin` is designed to integrate with Symphony's plugin architecture:

```python
from symphony.core.container import Container
from symphony.core.events import EventBus
from llm_tracing_plugin import LLMTracingPlugin

# Create a Symphony container
container = Container()
event_bus = EventBus()

# Register the plugin
tracer = LLMTracingPlugin()
tracer.initialize(container, event_bus)

# The plugin now subscribes to all LLM events
```

## Extending the Tracing System

You can extend the tracing system in several ways:

1. **Add New Metrics**:
   Modify the `analyze_traces.py` script to calculate additional metrics.

2. **Create Custom Visualizations**:
   Add new visualization functions to generate additional charts and graphs.

3. **Integrate with External Tools**:
   Export trace data to formats compatible with tools like Weights & Biases, TensorBoard, or custom dashboards.

4. **Real-time Monitoring**:
   Implement a real-time monitoring system that processes trace events as they occur.

## Comparing Model Performance

The tracing system makes it easy to compare different models:

```bash
# Generate taxonomies with different models
./generate_us_taxonomies.sh "Technology" --planner-model "gpt-4"
./generate_us_taxonomies.sh "Technology" --planner-model "o1-mini"

# Analyze and compare the traces
python analyze_traces.py traces/taxonomy_generation/trace_*.jsonl --output-dir "analysis/comparison"
```

Then manually compare the output metrics to determine which model performs better for your specific use case.

## Troubleshooting

If you encounter issues with tracing:

1. **Missing Trace Files**: Ensure the traces directory exists and is writable.
2. **Empty Trace Files**: Check that the model calls are properly decorated with the tracer.
3. **Analysis Errors**: Verify the trace files contain valid JSONL data.

For more specific issues, check the application logs or contact the maintainers.