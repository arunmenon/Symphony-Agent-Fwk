"""Example demonstrating the Symphony orchestration layer.

This example demonstrates how to use the Symphony orchestration layer to create
and execute complex workflows with different patterns of agent interaction.
"""

import os
import asyncio
import json
from typing import Dict, Any

from symphony.core.registry import ServiceRegistry
from symphony.core.config import SymphonyConfig, ConfigLoader
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
    WorkflowTemplates,
    register_orchestration_components
)


async def setup_registry(config: SymphonyConfig = None):
    """Set up service registry with repositories and services."""
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Use default config if none provided
    if config is None:
        config = ConfigLoader.load() if hasattr(ConfigLoader, 'load') else SymphonyConfig()
    
    # Determine storage path from config
    storage_path = getattr(config, 'base_dir', './data')
    if not os.path.isabs(storage_path):
        storage_path = os.path.join(os.getcwd(), storage_path)
    storage_path = os.path.join(storage_path, "data")
    os.makedirs(storage_path, exist_ok=True)
    
    # Create repositories
    persistence_type = getattr(config, 'persistence_type', 'memory')
    
    if persistence_type == "memory":
        # Use in-memory repositories for demo
        task_repo = InMemoryRepository(Task)
        workflow_repo = InMemoryRepository(Workflow)
        agent_config_repo = InMemoryRepository(AgentConfig)
        workflow_def_repo = InMemoryRepository(WorkflowDefinition)
    else:
        # Use file system repositories
        task_repo = FileSystemRepository(Task, storage_path)
        workflow_repo = FileSystemRepository(Workflow, storage_path)
        agent_config_repo = FileSystemRepository(AgentConfig, storage_path)
        workflow_def_repo = FileSystemRepository(WorkflowDefinition, storage_path)
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("workflow_definition", workflow_def_repo)
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Create some agent configs for demo
    writer_agent = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at generating engaging content.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    critic_agent = AgentConfig(
        name="CriticAgent",
        role="Content Critic",
        instruction_template="You are a critical reviewer who identifies issues and suggests improvements.",
        capabilities=AgentCapabilities(
            expertise=["critique", "review", "analysis"]
        )
    )
    
    math_agent = AgentConfig(
        name="MathAgent",
        role="Mathematics Expert",
        instruction_template="You are a mathematics expert who solves complex math problems.",
        capabilities=AgentCapabilities(
            expertise=["mathematics", "algebra", "calculations"]
        )
    )
    
    data_agent = AgentConfig(
        name="DataAnalystAgent",
        role="Data Analyst",
        instruction_template="You are a data analyst who excels at interpreting and analyzing data.",
        capabilities=AgentCapabilities(
            expertise=["analysis", "data", "statistics"]
        )
    )
    
    # Save agent configs
    await agent_config_repo.save(writer_agent)
    await agent_config_repo.save(critic_agent)
    await agent_config_repo.save(math_agent)
    await agent_config_repo.save(data_agent)
    
    return registry


async def critic_revise_example():
    """Demonstrate the critic-revise workflow pattern."""
    print("\n=== Critic-Revise Workflow Example ===")
    
    # Set up registry
    registry = await setup_registry()
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create critic-revise workflow
    workflow_def = templates.critic_revise(
        name="Blog Post Creation",
        main_prompt="Write a short blog post about the benefits of AI assistants in daily life.",
        critique_prompt="Review the blog post critically. Identify areas for improvement in terms of clarity, engagement, and factual accuracy.",
        revision_prompt="Revise the blog post based on the critique to create an improved version."
    )
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow completed successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            print("\nInitial Blog Post:")
            print("-" * 40)
            initial_result = next(
                (v.get("result") for k, v in context.items() 
                 if k.startswith("step.") and ".result" in k and "Initial" in k),
                "Not found"
            )
            print(initial_result)
            
            print("\nCritique:")
            print("-" * 40)
            critique_result = next(
                (v.get("result") for k, v in context.items() 
                 if k.startswith("step.") and ".result" in k and "Critique" in k),
                "Not found"
            )
            print(critique_result)
            
            print("\nFinal Revised Blog Post:")
            print("-" * 40)
            revision_result = next(
                (v.get("result") for k, v in context.items() 
                 if k.startswith("step.") and ".result" in k and "Revision" in k),
                "Not found"
            )
            print(revision_result)
    else:
        print(f"Workflow failed: {workflow.error}")


async def parallel_experts_example():
    """Demonstrate the parallel experts workflow pattern."""
    print("\n=== Parallel Experts Workflow Example ===")
    
    # Set up registry
    registry = await setup_registry()
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create parallel experts workflow
    workflow_def = templates.parallel_experts(
        name="Smart Home Analysis",
        prompt="What are the key considerations when setting up a smart home system?",
        expert_roles=["Technology", "Security", "Home Design"],
        summary_prompt="Synthesize the expert opinions into a comprehensive guide for setting up a smart home system."
    )
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow completed successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            # Get expert responses
            parallel_results = next(
                (v.get("results") for k, v in context.items() 
                 if k.startswith("step.") and ".results" in k),
                []
            )
            
            if parallel_results:
                for i, role in enumerate(["Technology", "Security", "Home Design"]):
                    if i < len(parallel_results):
                        print(f"\n{role} Expert Response:")
                        print("-" * 40)
                        print(parallel_results[i].get("result", "Not found"))
            
            # Get final synthesis
            synthesis_result = next(
                (v.get("result") for k, v in context.items() 
                 if k.startswith("step.") and ".result" in k and "Synthesis" in k),
                "Not found"
            )
            print("\nFinal Synthesis:")
            print("-" * 40)
            print(synthesis_result)
    else:
        print(f"Workflow failed: {workflow.error}")


async def custom_workflow_example():
    """Demonstrate a custom workflow with conditional logic."""
    print("\n=== Custom Workflow with Conditional Logic Example ===")
    
    # Set up registry
    registry = await setup_registry()
    
    # Create a custom workflow definition
    workflow_def = WorkflowDefinition(
        name="Math Problem Solver",
        description="Workflow that solves math problems with different approaches based on complexity"
    )
    
    # Initial classification step
    classify_step = TaskStep(
        name="Classify Problem",
        description="Classify the math problem as simple or complex",
        task_template={
            "name": "Problem Classification",
            "description": "Determine if the problem is simple or complex",
            "input_data": {
                "query": "Classify the following math problem as SIMPLE or COMPLEX. Only respond with the single word 'SIMPLE' or 'COMPLEX'.\n\nProblem: Find the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Simple solution step
    simple_step = TaskStep(
        name="Simple Solution",
        description="Solve a simple math problem",
        task_template={
            "name": "Simple Math Solution",
            "description": "Provide a straightforward solution",
            "input_data": {
                "query": "Solve this simple math problem step by step:\n\nFind the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Complex solution step
    complex_step = TaskStep(
        name="Complex Solution",
        description="Solve a complex math problem with detailed explanation",
        task_template={
            "name": "Complex Math Solution",
            "description": "Provide a detailed solution with explanation",
            "input_data": {
                "query": "Solve this complex math problem with detailed explanation and show all steps:\n\nFind the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Conditional step to choose simple or complex path
    conditional_step = ConditionalStep(
        name="Solution Path",
        description="Choose solution approach based on problem classification",
        condition=f"step.{classify_step.id}.result.strip().upper() == 'COMPLEX'",
        if_branch=complex_step,
        else_branch=simple_step
    )
    
    # Add steps to workflow
    workflow_def = workflow_def.add_step(classify_step)
    workflow_def = workflow_def.add_step(conditional_step)
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow completed successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            classification = context.get(f"step.{classify_step.id}.result", "").strip()
            print(f"\nProblem Classification: {classification}")
            
            # Determine which branch was taken
            branch_taken = context.get(f"step.{conditional_step.id}.branch_taken", "unknown")
            print(f"Branch Taken: {branch_taken}")
            
            # Get solution
            if branch_taken == "if":
                solution = context.get(f"step.{complex_step.id}.result", "Not found")
                print("\nComplex Solution:")
            else:
                solution = context.get(f"step.{simple_step.id}.result", "Not found")
                print("\nSimple Solution:")
                
            print("-" * 40)
            print(solution)
    else:
        print(f"Workflow failed: {workflow.error}")


async def iterative_refinement_example():
    """Demonstrate the iterative refinement workflow pattern."""
    print("\n=== Iterative Refinement Workflow Example ===")
    
    # Set up registry
    registry = await setup_registry()
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create an iterative refinement workflow
    workflow_def = templates.iterative_refinement(
        name="Business Proposal Refinement",
        initial_prompt="Draft a short business proposal for a new AI-powered productivity app.",
        feedback_prompt="Review the current draft and suggest specific improvements to make it more compelling and clear.",
        max_iterations=3,
        convergence_condition="'excellent' in step.result.lower() or 'complete' in step.result.lower()"
    )
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow completed successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            # Find the loop step information
            loop_step_id = next(
                (k.split('.')[1] for k in context.keys() 
                 if k.startswith("step.") and "total_iterations" in k),
                None
            )
            
            if loop_step_id:
                total_iterations = context.get(f"step.{loop_step_id}.total_iterations", 0)
                print(f"\nCompleted {total_iterations} refinement iterations")
                
                # Find initial step
                initial_step_id = next(
                    (k.split('.')[1] for k in context.keys() 
                     if k.startswith("step.") and "Initial" in context.get(f"step.{k.split('.')[1]}.name", "")),
                    None
                )
                
                if initial_step_id:
                    print("\nInitial Draft:")
                    print("-" * 40)
                    print(context.get(f"step.{initial_step_id}.result", "Not found"))
                
                # Print each iteration result
                for i in range(total_iterations):
                    iteration_result = context.get(f"step.{loop_step_id}.iterations.{i}", {})
                    print(f"\nIteration {i+1}:")
                    print("-" * 40)
                    print(iteration_result.get("result", "Not found"))
    else:
        print(f"Workflow failed: {workflow.error}")


async def data_report_example():
    """Demonstrate a data report workflow with parallel reviews."""
    print("\n=== Data Report Generation Workflow Example ===")
    
    # Set up registry
    registry = await setup_registry()
    
    # Get agent configurations
    agent_config_repo = registry.get_repository("agent_config")
    configs = await agent_config_repo.find_all()
    
    # Find agent IDs
    data_agent_id = next((c.id for c in configs if c.name == "DataAnalystAgent"), None)
    writer_agent_id = next((c.id for c in configs if c.name == "WriterAgent"), None)
    critic_agent_id = next((c.id for c in configs if c.name == "CriticAgent"), None)
    
    # Create a report generation workflow
    workflow_def = WorkflowDefinition(
        name="Sales Report Generation",
        description="Multi-stage workflow for creating and refining a data report"
    )
    
    # 1. Data analysis step
    analysis_step = TaskStep(
        name="Data Analysis",
        description="Analyze the provided data",
        task_template={
            "name": "Data Analysis",
            "description": "Analyze the given dataset and identify key insights",
            "input_data": {
                "query": """You are a data analyst analyzing quarterly sales data.
                
Here's the raw data:
Region,Q1,Q2,Q3,Q4
North,120000,145000,160000,190000
South,95000,110000,102000,130000
East,150000,175000,190000,205000
West,135000,140000,155000,180000

Analyze this data and provide 5 key insights about trends, patterns, and notable findings.
Organize your insights in a clear, structured format."""
            }
        },
        agent_id=data_agent_id
    )
    
    # 2. Report drafting step
    draft_step = TaskStep(
        name="Report Draft",
        description="Write the report draft based on analysis",
        task_template={
            "name": "Report Draft",
            "description": "Write report draft based on analysis",
            "input_data": {
                "query": f"""Write a well-structured quarterly sales report based on the following analysis:

{{{{step.{analysis_step.id}.result}}}}

The report should include:
1. An executive summary
2. Regional performance analysis
3. Quarter-over-quarter trends
4. Recommendations based on the data
5. A brief outlook for next quarter

Use professional business language appropriate for stakeholders."""
            }
        },
        agent_id=writer_agent_id
    )
    
    # 3. Review steps (clarity and technical accuracy)
    clarity_review = TaskStep(
        name="Clarity Review",
        description="Review for clarity and readability",
        task_template={
            "name": "Clarity Review",
            "description": "Review for clarity and readability",
            "input_data": {
                "query": f"""Review this report for clarity and readability. Identify specific areas where the text could be clearer or better structured:

{{{{step.{draft_step.id}.result}}}}

Focus on:
- Structure and flow
- Language clarity
- Accessibility to non-technical readers
- Overall readability

Provide specific recommendations for improvements."""
            }
        },
        agent_id=critic_agent_id
    )
    
    technical_review = TaskStep(
        name="Technical Review",
        description="Review for data accuracy",
        task_template={
            "name": "Technical Review",
            "description": "Review for analytical accuracy",
            "input_data": {
                "query": f"""Review this report for analytical accuracy and completeness. Ensure the data analysis is sound and the conclusions are supported by the data:

{{{{step.{draft_step.id}.result}}}}

Focus on:
- Analytical rigor
- Correctness of interpretations
- Appropriateness of recommendations
- Missing analyses or perspectives

Provide specific technical suggestions for improvement."""
            }
        },
        agent_id=data_agent_id
    )
    
    # Combine reviews in parallel
    parallel_review = ParallelStep(
        name="Parallel Reviews",
        description="Conduct multiple reviews in parallel",
        steps=[clarity_review, technical_review]
    )
    
    # 4. Final revision step
    final_step = TaskStep(
        name="Final Revision",
        description="Revise report based on reviews",
        task_template={
            "name": "Final Revision",
            "description": "Revise the report based on reviews",
            "input_data": {
                "query": f"""Revise this report based on the following reviews:

Original Draft:
{{{{step.{draft_step.id}.result}}}}

Clarity Review:
{{{{step.{parallel_review.id}.results.0.result}}}}

Technical Review:
{{{{step.{parallel_review.id}.results.1.result}}}}

Create an improved version that addresses both the clarity and technical feedback while maintaining professional business language."""
            }
        },
        agent_id=writer_agent_id
    )
    
    # Add all steps to workflow
    workflow_def = workflow_def.add_step(analysis_step)
    workflow_def = workflow_def.add_step(draft_step)
    workflow_def = workflow_def.add_step(parallel_review)
    workflow_def = workflow_def.add_step(final_step)
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow completed successfully!")
        
        # Access results from workflow metadata
        if "context" in workflow.metadata:
            context = workflow.metadata["context"]
            
            # Get final result
            final_result = context.get(f"step.{final_step.id}.result", "Not found")
            
            print("\nFinal Sales Report:")
            print("-" * 60)
            print(final_result)
            
            # Save output to a file
            os.makedirs("./data", exist_ok=True)
            with open("./data/sales_report.md", "w") as f:
                f.write(final_result)
            print(f"\nOutput saved to ./data/sales_report.md")
    else:
        print(f"Workflow failed: {workflow.error}")


async def main():
    """Run orchestration examples."""
    print("Symphony Orchestration Layer Examples")
    print("=====================================")
    print("\nThis example demonstrates various workflow patterns provided by the")
    print("Symphony orchestration layer, including critic-revise, parallel-experts,")
    print("conditional branching, iterative refinement, and custom workflows.")
    
    # Allow selecting specific examples or run all
    examples = {
        "1": ("Critic-Revise Pattern", critic_revise_example),
        "2": ("Parallel Experts Pattern", parallel_experts_example),
        "3": ("Conditional Workflow", custom_workflow_example),
        "4": ("Iterative Refinement Pattern", iterative_refinement_example),
        "5": ("Data Report Generation", data_report_example),
        "all": ("All Examples", None)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}: {name}")
    
    choice = input("\nEnter example number to run (or 'all' for all examples): ").strip()
    
    if choice in examples:
        if choice == "all":
            # Run all examples
            await critic_revise_example()
            await parallel_experts_example()
            await custom_workflow_example()
            await iterative_refinement_example()
            await data_report_example()
        else:
            # Run selected example
            await examples[choice][1]()
    else:
        print(f"Invalid choice: {choice}")
        print("Running all examples...")
        await critic_revise_example()
        await parallel_experts_example()
        await custom_workflow_example()
        await iterative_refinement_example()
        await data_report_example()


if __name__ == "__main__":
    asyncio.run(main())