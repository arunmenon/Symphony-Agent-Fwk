"""Example of a DAG-based workflow using the Symphony framework with orchestration.

This example demonstrates using the Symphony orchestration layer to create and execute
a DAG (Directed Acyclic Graph) workflow with different types of nodes and edges.
"""

import asyncio
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.persistence.file_repository import FileSystemRepository
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus
from symphony.orchestration import (
    WorkflowDefinition, 
    TaskStep, 
    ConditionalStep,
    ParallelStep,
    LoopStep,
    register_orchestration_components
)


async def setup_registry():
    """Set up service registry with repositories and services."""
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Create repositories
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    agent_config_repo = InMemoryRepository(AgentConfig)
    workflow_def_repo = InMemoryRepository(WorkflowDefinition)
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("workflow_definition", workflow_def_repo)
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Create agent configurations
    researcher_agent = AgentConfig(
        name="ResearcherAgent",
        role="Information Researcher",
        instruction_template="You are a researcher who excels at finding accurate information.",
        capabilities=AgentCapabilities(
            expertise=["research", "information_gathering", "fact_checking"]
        )
    )
    
    writer_agent = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at generating engaging content.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    advisor_agent = AgentConfig(
        name="AdvisorAgent",
        role="Decision Advisor",
        instruction_template="You are a decision advisor who excels at providing recommendations.",
        capabilities=AgentCapabilities(
            expertise=["decision_making", "recommendations", "analysis"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(researcher_agent)
    await agent_config_repo.save(writer_agent)
    await agent_config_repo.save(advisor_agent)
    
    return registry


async def create_travel_planning_dag():
    """Create a DAG workflow for travel planning."""
    # Set up registry
    registry = await setup_registry()
    
    # Get agent configurations
    agent_config_repo = registry.get_repository("agent_config")
    configs = await agent_config_repo.find_all()
    
    # Find agent IDs
    researcher_id = next((c.id for c in configs if c.name == "ResearcherAgent"), None)
    writer_id = next((c.id for c in configs if c.name == "WriterAgent"), None)
    advisor_id = next((c.id for c in configs if c.name == "AdvisorAgent"), None)
    
    # Create a workflow definition
    workflow_def = WorkflowDefinition(
        name="Travel Planning DAG",
        description="A DAG workflow for travel planning with multiple paths"
    )
    
    # Start with destination research
    destination_research = TaskStep(
        name="Destination Research",
        description="Research potential travel destinations",
        task_template={
            "name": "Destination Research",
            "description": "Research potential travel destinations",
            "input_data": {
                "query": "Research three potential travel destinations for a week-long vacation in June. Provide key information about each destination including weather, attractions, and costs."
            }
        },
        agent_id=researcher_id
    )
    
    # Destination classification step
    classify_destination = TaskStep(
        name="Classify Destinations",
        description="Classify destinations by type",
        task_template={
            "name": "Destination Classification",
            "description": "Classify the researched destinations by type",
            "input_data": {
                "query": f"""Based on the following destination research, classify each destination as either BEACH, CITY, or NATURE.
                
Research results:
{{{{step.{destination_research.id}.result}}}}

Return your answer in the format:
Destination 1: TYPE
Destination 2: TYPE
Destination 3: TYPE"""
            }
        },
        agent_id=researcher_id
    )
    
    # Beach destination path
    beach_planning = TaskStep(
        name="Beach Trip Planning",
        description="Create beach vacation itinerary",
        task_template={
            "name": "Beach Trip Planning",
            "description": "Create a beach vacation itinerary",
            "input_data": {
                "query": f"""Create a detailed 7-day itinerary for a beach vacation based on the beach destination from the research:

{{{{step.{destination_research.id}.result}}}}

Classification: {{{{step.{classify_destination.id}.result}}}}

Include:
- Day-by-day activities
- Recommended accommodations
- Beach-specific items to pack
- Estimated budget"""
            }
        },
        agent_id=writer_id
    )
    
    # City destination path
    city_planning = TaskStep(
        name="City Trip Planning",
        description="Create urban exploration itinerary",
        task_template={
            "name": "City Trip Planning",
            "description": "Create a city vacation itinerary",
            "input_data": {
                "query": f"""Create a detailed 7-day itinerary for a city vacation based on the city destination from the research:

{{{{step.{destination_research.id}.result}}}}

Classification: {{{{step.{classify_destination.id}.result}}}}

Include:
- Cultural attractions to visit each day
- Urban transportation options
- Recommended restaurants and nightlife
- Shopping districts
- Estimated budget"""
            }
        },
        agent_id=writer_id
    )
    
    # Nature destination path
    nature_planning = TaskStep(
        name="Nature Trip Planning",
        description="Create nature and outdoor activity itinerary",
        task_template={
            "name": "Nature Trip Planning",
            "description": "Create a nature vacation itinerary",
            "input_data": {
                "query": f"""Create a detailed 7-day itinerary for a nature vacation based on the nature destination from the research:

{{{{step.{destination_research.id}.result}}}}

Classification: {{{{step.{classify_destination.id}.result}}}}

Include:
- Hiking trails and outdoor activities
- Wildlife viewing opportunities
- Camping or lodge accommodations
- Essential outdoor gear to pack
- Estimated budget"""
            }
        },
        agent_id=writer_id
    )
    
    # Conditional step for destination type
    destination_type_condition = ConditionalStep(
        name="Destination Type Decision",
        description="Choose planning path based on destination type",
        condition=f"'BEACH' in step.{classify_destination.id}.result.upper()",
        if_branch=beach_planning,
        else_branch=ConditionalStep(
            name="City or Nature",
            description="Choose between city or nature planning",
            condition=f"'CITY' in step.{classify_destination.id}.result.upper()",
            if_branch=city_planning,
            else_branch=nature_planning
        )
    )
    
    # Final recommendations step
    recommendations = TaskStep(
        name="Travel Recommendations",
        description="Provide final travel recommendations",
        task_template={
            "name": "Travel Recommendations",
            "description": "Provide final travel recommendations",
            "input_data": {
                "query": f"""Based on the complete travel planning information, provide final recommendations for making this trip successful.

Destinations Researched:
{{{{step.{destination_research.id}.result}}}}

Destination Types:
{{{{step.{classify_destination.id}.result}}}}

Trip Planning:
{% if step.{beach_planning.id}.result is defined %}
{{{{step.{beach_planning.id}.result}}}}
{% elif step.{city_planning.id}.result is defined %}
{{{{step.{city_planning.id}.result}}}}
{% elif step.{nature_planning.id}.result is defined %}
{{{{step.{nature_planning.id}.result}}}}
{% else %}
No specific planning available.
{% endif %}

Provide:
1. Top 3 practical recommendations to make this trip successful
2. Potential challenges and how to address them
3. Final budget considerations
"""
            }
        },
        agent_id=advisor_id
    )
    
    # Add steps to workflow
    workflow_def = workflow_def.add_step(destination_research)
    workflow_def = workflow_def.add_step(classify_destination)
    workflow_def = workflow_def.add_step(destination_type_condition)
    workflow_def = workflow_def.add_step(recommendations)
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    print("Executing travel planning DAG workflow...")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"\nWorkflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nTravel Planning Workflow Completed Successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            # Display research results
            research_result = context.get(f"step.{destination_research.id}.result", "Not found")
            print("\n=== Destination Research ===")
            print("-" * 60)
            print(research_result)
            
            # Display classification
            classification = context.get(f"step.{classify_destination.id}.result", "Not found")
            print("\n=== Destination Classification ===")
            print("-" * 60)
            print(classification)
            
            # Determine which planning path was taken
            print("\n=== Trip Planning ===")
            print("-" * 60)
            if f"step.{beach_planning.id}.result" in context:
                planning = context.get(f"step.{beach_planning.id}.result", "Not found")
                print("Beach Vacation Planning:")
            elif f"step.{city_planning.id}.result" in context:
                planning = context.get(f"step.{city_planning.id}.result", "Not found")
                print("City Vacation Planning:")
            elif f"step.{nature_planning.id}.result" in context:
                planning = context.get(f"step.{nature_planning.id}.result", "Not found")
                print("Nature Vacation Planning:")
            else:
                planning = "No specific planning found."
                print("Planning:")
            print(planning)
            
            # Display recommendations
            recommendations_result = context.get(f"step.{recommendations.id}.result", "Not found")
            print("\n=== Travel Recommendations ===")
            print("-" * 60)
            print(recommendations_result)
            
            # Save output to a file
            os.makedirs("./data", exist_ok=True)
            with open("./data/travel_plan.md", "w") as f:
                f.write("# Travel Planning Results\n\n")
                f.write("## Destination Research\n\n")
                f.write(research_result)
                f.write("\n\n## Destination Classification\n\n")
                f.write(classification)
                f.write("\n\n## Trip Planning\n\n")
                f.write(planning)
                f.write("\n\n## Travel Recommendations\n\n")
                f.write(recommendations_result)
            print(f"\nComplete travel plan saved to ./data/travel_plan.md")
    else:
        print(f"Workflow failed: {workflow.error or 'Unknown error'}")
        
    return workflow


async def create_product_development_dag():
    """Create a DAG workflow for product development."""
    # Set up registry
    registry = await setup_registry()
    
    # Get agent configurations
    agent_config_repo = registry.get_repository("agent_config")
    configs = await agent_config_repo.find_all()
    
    # Find agent IDs
    researcher_id = next((c.id for c in configs if c.name == "ResearcherAgent"), None)
    writer_id = next((c.id for c in configs if c.name == "WriterAgent"), None)
    advisor_id = next((c.id for c in configs if c.name == "AdvisorAgent"), None)
    
    # Create a workflow definition
    workflow_def = WorkflowDefinition(
        name="Product Development DAG",
        description="A DAG workflow for product development with parallel processing"
    )
    
    # Market research step
    market_research = TaskStep(
        name="Market Research",
        description="Research the market for AI productivity tools",
        task_template={
            "name": "Market Research",
            "description": "Research the market for AI productivity tools",
            "input_data": {
                "query": "Conduct market research for AI productivity tools. Identify key competitors, market size, and trends in this space."
            }
        },
        agent_id=researcher_id
    )
    
    # Target audience analysis step
    audience_analysis = TaskStep(
        name="Target Audience Analysis",
        description="Analyze potential target audiences",
        task_template={
            "name": "Target Audience Analysis",
            "description": "Analyze potential target audiences",
            "input_data": {
                "query": "Analyze potential target audiences for an AI productivity tool. Identify 3-4 distinct user segments, their needs, and pain points."
            }
        },
        agent_id=researcher_id
    )
    
    # Run market research and audience analysis in parallel
    parallel_research = ParallelStep(
        name="Parallel Research",
        description="Conduct market and audience research in parallel",
        steps=[market_research, audience_analysis]
    )
    
    # Feature planning step
    feature_planning = TaskStep(
        name="Feature Planning",
        description="Plan features based on research",
        task_template={
            "name": "Feature Planning",
            "description": "Plan features based on research",
            "input_data": {
                "query": f"""Based on the market research and target audience analysis, plan key features for an AI productivity tool.

Market Research:
{{{{step.{parallel_research.id}.results.0.result}}}}

Target Audience Analysis:
{{{{step.{parallel_research.id}.results.1.result}}}}

Outline:
1. Core features (must-haves)
2. Secondary features (nice-to-haves)
3. Future potential features
4. Unique selling propositions
"""
            }
        },
        agent_id=advisor_id
    )
    
    # Technical feasibility assessment
    tech_assessment = TaskStep(
        name="Technical Feasibility",
        description="Assess technical feasibility of features",
        task_template={
            "name": "Technical Feasibility",
            "description": "Assess technical feasibility of features",
            "input_data": {
                "query": f"""Assess the technical feasibility of implementing the following features for an AI productivity tool.

Planned Features:
{{{{step.{feature_planning.id}.result}}}}

For each feature category, provide:
1. Feasibility rating (High/Medium/Low)
2. Technical requirements
3. Potential implementation challenges
4. Estimated development time
"""
            }
        },
        agent_id=researcher_id
    )
    
    # Marketing strategy
    marketing_strategy = TaskStep(
        name="Marketing Strategy",
        description="Develop a marketing strategy",
        task_template={
            "name": "Marketing Strategy",
            "description": "Develop a marketing strategy",
            "input_data": {
                "query": f"""Develop a marketing strategy for an AI productivity tool with the following features.

Market Research:
{{{{step.{parallel_research.id}.results.0.result}}}}

Target Audience:
{{{{step.{parallel_research.id}.results.1.result}}}}

Product Features:
{{{{step.{feature_planning.id}.result}}}}

Include:
1. Positioning strategy
2. Key messaging for different audience segments
3. Marketing channels and tactics
4. Content marketing ideas
5. Launch strategy
"""
            }
        },
        agent_id=writer_id
    )
    
    # Run technical assessment and marketing in parallel
    parallel_planning = ParallelStep(
        name="Parallel Planning",
        description="Conduct technical assessment and marketing planning in parallel",
        steps=[tech_assessment, marketing_strategy]
    )
    
    # Product roadmap
    product_roadmap = TaskStep(
        name="Product Roadmap",
        description="Create a product development roadmap",
        task_template={
            "name": "Product Roadmap",
            "description": "Create a product development roadmap",
            "input_data": {
                "query": f"""Create a comprehensive product roadmap for developing and launching an AI productivity tool.

Market Research:
{{{{step.{parallel_research.id}.results.0.result}}}}

Target Audience:
{{{{step.{parallel_research.id}.results.1.result}}}}

Product Features:
{{{{step.{feature_planning.id}.result}}}}

Technical Assessment:
{{{{step.{parallel_planning.id}.results.0.result}}}}

Marketing Strategy:
{{{{step.{parallel_planning.id}.results.1.result}}}}

Create a roadmap with:
1. Development phases (MVP, v1.0, v2.0, etc.)
2. Timeline with key milestones
3. Resource requirements
4. Success metrics for each phase
5. Risk assessment and mitigation strategies
"""
            }
        },
        agent_id=advisor_id
    )
    
    # Add steps to workflow
    workflow_def = workflow_def.add_step(parallel_research)
    workflow_def = workflow_def.add_step(feature_planning)
    workflow_def = workflow_def.add_step(parallel_planning)
    workflow_def = workflow_def.add_step(product_roadmap)
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    print("Executing product development DAG workflow...")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"\nWorkflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nProduct Development Workflow Completed Successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            # Display final roadmap
            roadmap = context.get(f"step.{product_roadmap.id}.result", "Not found")
            print("\n=== Product Roadmap ===")
            print("-" * 60)
            print(roadmap)
            
            # Save output to a file
            os.makedirs("./data", exist_ok=True)
            with open("./data/product_roadmap.md", "w") as f:
                f.write("# AI Productivity Tool Product Roadmap\n\n")
                f.write(roadmap)
            print(f"\nProduct roadmap saved to ./data/product_roadmap.md")
    else:
        print(f"Workflow failed: {workflow.error or 'Unknown error'}")
        
    return workflow


async def main():
    """Run DAG workflow examples."""
    print("Symphony DAG Workflow Examples")
    print("==============================")
    print("\nThis example demonstrates building DAG workflows using the Symphony")
    print("orchestration layer, including conditional branching and parallel processing.")
    
    # Allow selecting specific examples or run all
    examples = {
        "1": ("Travel Planning DAG", create_travel_planning_dag),
        "2": ("Product Development DAG", create_product_development_dag),
        "all": ("All Examples", None)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}: {name}")
    
    choice = input("\nEnter example number to run (or 'all' for all examples): ").strip()
    
    if choice in examples:
        if choice == "all":
            # Run all examples
            await create_travel_planning_dag()
            await create_product_development_dag()
        else:
            # Run selected example
            await examples[choice][1]()
    else:
        print(f"Invalid choice: {choice}")
        print("Running first example only...")
        await create_travel_planning_dag()


if __name__ == "__main__":
    asyncio.run(main())