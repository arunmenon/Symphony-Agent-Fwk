#!/usr/bin/env python
"""Analyze trace data from taxonomy generation to provide insights."""

import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import statistics
import matplotlib.pyplot as plt
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def load_trace_data(trace_file: str) -> List[Dict[str, Any]]:
    """Load trace data from a JSONL file.
    
    Args:
        trace_file: Path to the trace file
        
    Returns:
        List of trace events
    """
    if not os.path.exists(trace_file):
        raise FileNotFoundError(f"Trace file not found: {trace_file}")
    
    events = []
    with open(trace_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse line: {line}")
    
    return events

def analyze_model_calls(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze model calls from trace events.
    
    Args:
        events: List of trace events
        
    Returns:
        Dictionary with analysis results
    """
    # Initialize analysis data
    analysis = {
        "request_count": 0,
        "response_count": 0,
        "error_count": 0,
        "total_tokens": 0,
        "response_times": [],
        "models_used": defaultdict(int),
        "average_response_time": 0,
        "max_response_time": 0,
        "min_response_time": 0,
        "requests_by_timestamp": [],
        "request_ids": set(),
        "matched_request_responses": [],
    }
    
    # Dictionary to store temporary request data
    requests = {}
    
    # Process events
    for event in events:
        event_type = event.get("type", "")
        
        if event_type == "llm_request":
            analysis["request_count"] += 1
            data = event.get("data", {})
            request_id = data.get("request_id")
            model = data.get("model", "unknown")
            analysis["models_used"][model] += 1
            
            if request_id:
                analysis["request_ids"].add(request_id)
                # Store request data
                requests[request_id] = {
                    "timestamp": event.get("timestamp"),
                    "model": model,
                    "messages": data.get("messages", []),
                }
                
                # Store timestamp for time-series analysis
                analysis["requests_by_timestamp"].append({
                    "timestamp": event.get("timestamp"),
                    "type": "request",
                    "model": model,
                    "request_id": request_id,
                })
                
        elif event_type == "llm_response":
            analysis["response_count"] += 1
            data = event.get("data", {})
            request_id = data.get("request_id")
            duration = data.get("duration_seconds", 0)
            
            if duration > 0:
                analysis["response_times"].append(duration)
                
                if request_id in requests:
                    # Match response with request
                    matched_pair = {
                        "request_id": request_id,
                        "model": requests[request_id].get("model", "unknown"),
                        "request_time": requests[request_id].get("timestamp"),
                        "response_time": event.get("timestamp"),
                        "duration": duration,
                        "output_length": len(data.get("output", "")),
                    }
                    analysis["matched_request_responses"].append(matched_pair)
                
                # Store timestamp for time-series analysis
                analysis["requests_by_timestamp"].append({
                    "timestamp": event.get("timestamp"),
                    "type": "response",
                    "duration": duration,
                    "request_id": request_id,
                })
            
        elif event_type == "llm_error":
            analysis["error_count"] += 1
    
    # Calculate statistics if we have response times
    if analysis["response_times"]:
        analysis["average_response_time"] = statistics.mean(analysis["response_times"])
        analysis["max_response_time"] = max(analysis["response_times"])
        analysis["min_response_time"] = min(analysis["response_times"])
        if len(analysis["response_times"]) > 1:
            analysis["std_dev_response_time"] = statistics.stdev(analysis["response_times"])
        else:
            analysis["std_dev_response_time"] = 0
    
    return analysis

def generate_visualizations(analysis: Dict[str, Any], output_dir: str, prefix: str = "trace_analysis"):
    """Generate visualizations from trace analysis.
    
    Args:
        analysis: Dictionary with analysis results
        output_dir: Directory to save visualizations
        prefix: Prefix for output files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a plot for response times
    if analysis["response_times"]:
        plt.figure(figsize=(10, 6))
        plt.hist(analysis["response_times"], bins=10, alpha=0.7, color='blue')
        plt.xlabel('Response Time (seconds)')
        plt.ylabel('Frequency')
        plt.title('Distribution of Model Response Times')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_dir, f"{prefix}_response_times.png"))
        plt.close()
    
    # Create a plot for models used
    if analysis["models_used"]:
        plt.figure(figsize=(10, 6))
        models = list(analysis["models_used"].keys())
        counts = list(analysis["models_used"].values())
        plt.bar(models, counts, color='green')
        plt.xlabel('Model')
        plt.ylabel('Number of Requests')
        plt.title('Models Used in Taxonomy Generation')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{prefix}_models_used.png"))
        plt.close()
    
    # Create a summary report
    report_path = os.path.join(output_dir, f"{prefix}_summary.txt")
    with open(report_path, 'w') as f:
        f.write("Trace Analysis Summary\n")
        f.write("=====================\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        f.write("Request Statistics\n")
        f.write("-----------------\n")
        f.write(f"Total Requests: {analysis['request_count']}\n")
        f.write(f"Successful Responses: {analysis['response_count']}\n")
        f.write(f"Errors: {analysis['error_count']}\n\n")
        
        f.write("Response Time Statistics\n")
        f.write("-----------------------\n")
        f.write(f"Average Response Time: {analysis['average_response_time']:.2f} seconds\n")
        f.write(f"Maximum Response Time: {analysis['max_response_time']:.2f} seconds\n")
        f.write(f"Minimum Response Time: {analysis['min_response_time']:.2f} seconds\n")
        if "std_dev_response_time" in analysis:
            f.write(f"Standard Deviation: {analysis['std_dev_response_time']:.2f} seconds\n\n")
        
        f.write("Models Used\n")
        f.write("-----------\n")
        for model, count in analysis["models_used"].items():
            f.write(f"{model}: {count} requests\n")
    
    return report_path

def main():
    """Parse arguments and run the trace analysis."""
    parser = argparse.ArgumentParser(description="Analyze taxonomy generation traces")
    
    parser.add_argument(
        "trace_file",
        help="Path to the trace file to analyze"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save analysis results (default: analysis)",
        default="analysis"
    )
    
    parser.add_argument(
        "--prefix",
        help="Prefix for output files (default: trace_analysis)",
        default="trace_analysis"
    )
    
    args = parser.parse_args()
    
    try:
        # Load trace data
        logger.info(f"Loading trace data from {args.trace_file}...")
        events = load_trace_data(args.trace_file)
        logger.info(f"Loaded {len(events)} events from trace file")
        
        # Analyze model calls
        logger.info("Analyzing model calls...")
        analysis = analyze_model_calls(events)
        
        # Generate visualizations
        logger.info(f"Generating visualizations in {args.output_dir}...")
        report_path = generate_visualizations(analysis, args.output_dir, args.prefix)
        
        logger.info(f"Analysis complete! Summary report saved to {report_path}")
        
    except Exception as e:
        logger.error(f"Error analyzing trace: {e}")
        raise

if __name__ == "__main__":
    main()