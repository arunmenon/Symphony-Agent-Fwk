"""Example demonstrating the Symphony API.

This example demonstrates how to use the Symphony API with both the
facade pattern and the builder pattern.
"""

import os
import asyncio
import json
from typing import Dict, List, Any, Optional

from symphony import Symphony, TaskStatus, TaskPriority


async def facade_api_example():
    """Demonstrate the Symphony API using facades."""
    print("\n=== Symphony API Facade Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup(persistence_type="memory")
    
    # Create and save an agent using the facade
    agent_config = await symphony.agents.create_agent(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at generating engaging content.",
        capabilities={"expertise": ["writing", "content", "creativity"]}
    )
    agent_id = await symphony.agents.save_agent(agent_config)
    print(f"Created agent with ID: {agent_id}")
    
    # Create and execute a task using the facade
    task = await symphony.tasks.create_task(
        name="Write Blog Post",
        description="Write a blog post about AI",
        input_data={"query": "Write a short blog post about the benefits of AI assistants in daily life."},
        agent_id=agent_id
    )
    task_id = await symphony.tasks.save_task(task)
    
    print("Executing task...")
    task = await symphony.tasks.execute_task(task)
    
    # Check task result
    print(f"Task status: {task.status}")
    if task.status == TaskStatus.COMPLETED:
        print("\nTask Result:")
        print("-" * 40)
        print(task.result)
    
    # Create and execute a workflow using the facade
    print("\nCreating and executing critic-revise workflow...")
    workflow_def = await symphony.workflows.create_critic_revise_workflow(
        name="Blog Post Improvement",
        main_prompt="Write a short blog post about the benefits of AI assistants in daily life.",
        critique_prompt="Review the blog post critically. Identify areas for improvement in terms of clarity, engagement, and factual accuracy.",
        revision_prompt="Revise the blog post based on the critique to create an improved version."
    )
    
    workflow_id = await symphony.workflows.save_workflow(workflow_def)
    workflow = await symphony.workflows.execute_workflow(workflow_def)
    
    # Get and display workflow results
    results = await symphony.workflows.get_workflow_results(workflow.id)
    print("\nWorkflow status:", results["status"])
    
    if "steps" in results:
        for step_name, result in results["steps"].items():
            if "Initial" in step_name:
                print("\nInitial Blog Post:")
                print("-" * 40)
                print(result)
            elif "Critique" in step_name:
                print("\nCritique:")
                print("-" * 40)
                print(result)
            elif "Revision" in step_name:
                print("\nRevised Blog Post:")
                print("-" * 40)
                print(result)


async def builder_pattern_example():
    """Demonstrate the Symphony API using the builder pattern."""
    print("\n=== Symphony API Builder Pattern Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup(persistence_type="memory")
    
    # Create an agent using the builder pattern
    print("Creating agent with builder pattern...")
    agent = (symphony.build_agent()
             .create("AnalystAgent", "Data Analyst", 
                   "You are a data analyst who excels at interpreting and analyzing data.")
             .with_capabilities(["analysis", "data", "statistics"])
             .with_model("gpt-4")
             .with_metadata("description", "Specialized in data analysis and visualization")
             .build())
    
    # Save the agent
    agent_id = await symphony.agents.save_agent(agent)
    print(f"Created agent with ID: {agent_id}")
    
    # Create a task using the builder pattern
    print("\nCreating task with builder pattern...")
    task = (symphony.build_task()
           .create("Analyze Data", "Analyze the given dataset")
           .with_query("""Analyze this quarterly sales data and provide 3 key insights:
           
Region,Q1,Q2,Q3,Q4
North,120000,145000,160000,190000
South,95000,110000,102000,130000
East,150000,175000,190000,205000
West,135000,140000,155000,180000""")
           .for_agent(agent_id)
           .with_priority(TaskPriority.HIGH)
           .with_metadata("data_type", "quarterly_sales")
           .build())
    
    # Execute the task
    print("Executing task...")
    executed_task = await symphony.build_task().create("Analyze Data", "Analyze the data").with_query("...").for_agent(agent_id).build().execute()
    
    # Check task result
    print(f"Task status: {executed_task.status}")
    if executed_task.status == TaskStatus.COMPLETED:
        print("\nTask Result:")
        print("-" * 40)
        print(executed_task.result)
    
    # Create a workflow using the builder pattern
    print("\nCreating workflow with builder pattern...")
    workflow = (symphony.build_workflow()
               .create("Multi-step Analysis", "Perform analysis and visualization")
               .add_task(
                   "Data Analysis", 
                   "Analyze the dataset", 
                   {
                       "name": "Data Analysis",
                       "description": "Analyze the quarterly sales data",
                       "input_data": {
                           "query": """Analyze this quarterly sales data and provide insights:
                           
Region,Q1,Q2,Q3,Q4
North,120000,145000,160000,190000
South,95000,110000,102000,130000
East,150000,175000,190000,205000
West,135000,140000,155000,180000"""
                       }
                   },
                   agent_id
               )
               .add_task(
                   "Visualization Suggestions", 
                   "Suggest visualizations", 
                   {
                       "name": "Visualization Ideas",
                       "description": "Suggest visualizations for the data",
                       "input_data": {
                           "query": """Based on the data analysis, suggest 3 different visualization types that would best represent the insights. For each one, explain why it's appropriate and what it would reveal.
                           
Previous analysis: {{step.<STEP_ID>.result}}"""
                       }
                   },
                   agent_id
               )
               .build())
    
    # Fix step reference in the second task's input
    steps = workflow.get_steps()
    steps[1].task_template["input_data"]["query"] = steps[1].task_template["input_data"]["query"].replace("<STEP_ID>", steps[0].id)
    
    # Execute workflow
    print("Executing workflow...")
    executed_workflow = await symphony.build_workflow().create("Multi-step Analysis", "Perform analysis and visualization").add_task("...", "...", {}).build().execute()
    
    # Get workflow results
    results = await symphony.workflows.get_workflow_results(executed_workflow.id)
    print("\nWorkflow status:", results["status"])
    
    if "steps" in results:
        for step_name, result in results["steps"].items():
            print(f"\n{step_name}:")
            print("-" * 40)
            print(result)


async def main():
    """Run Symphony API examples."""
    print("Symphony API Examples")
    print("=====================")
    print("\nThis example demonstrates the Symphony API using both facades")
    print("and the builder pattern for fluent interfaces.")
    
    # Allow selecting specific examples or run all
    examples = {
        "1": ("Facade API", facade_api_example),
        "2": ("Builder Pattern", builder_pattern_example),
        "all": ("All Examples", None)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}: {name}")
    
    choice = input("\nEnter example number to run (or 'all' for all examples): ").strip()
    
    if choice in examples:
        if choice == "all":
            # Run all examples
            await facade_api_example()
            await builder_pattern_example()
        else:
            # Run selected example
            await examples[choice][1]()
    else:
        print(f"Invalid choice: {choice}")
        print("Running all examples...")
        await facade_api_example()
        await builder_pattern_example()


if __name__ == "__main__":
    asyncio.run(main())