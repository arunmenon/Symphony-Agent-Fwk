## 4. API Layer

The API Layer provides a clean, user-friendly interface for working with Symphony components. It implements both the Facade and Builder patterns to hide implementation details and provide intuitive interfaces.

### Key Components

- `Symphony`: Main entry point and API facade
- `Facade Classes`: Domain-specific interfaces that hide implementation details
  - `AgentFacade`: Interface for agent operations
  - `TaskFacade`: Interface for task operations
  - `WorkflowFacade`: Interface for workflow operations
- `Builder Classes`: Fluent interfaces for creating complex objects
  - `AgentBuilder`: Builder for agent configurations
  - `TaskBuilder`: Builder for tasks
  - `WorkflowBuilder`: Builder for workflow definitions

### Using the Facade Pattern

The Facade Pattern provides a simplified interface for common operations:

```python
import asyncio
from symphony import Symphony

async def facade_api_example():
    """Demonstrate the Symphony API using facades."""
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
    if task.status.value == "completed":
        print("\nTask Result:")
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
            print(f"\n{step_name}:")
            print("-" * 40)
            print(result)

asyncio.run(facade_api_example())
```

### Using the Builder Pattern

The Builder Pattern provides a fluent interface for creating complex objects:

```python
import asyncio
from symphony import Symphony, TaskPriority

async def builder_pattern_example():
    """Demonstrate the Symphony API using the builder pattern."""
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
    
    # Execute the task directly from the builder
    print("Executing task...")
    executed_task = await (symphony.build_task()
                          .create("Analyze Data", "Analyze the data")
                          .with_query("Analyze the quarterly sales data for key trends")
                          .for_agent(agent_id)
                          .build()
                          .execute())
    
    # Check task result
    print(f"Task status: {executed_task.status}")
    if executed_task.status.value == "completed":
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
                           "query": """Based on the data analysis, suggest 3 different visualization types that would best represent the insights. For each one, explain why it's appropriate and what it would reveal."""
                       }
                   },
                   agent_id
               )
               .with_context({"data_source": "quarterly_sales_report"})
               .build())
    
    # Execute the workflow directly from the builder
    print("Executing workflow...")
    executed_workflow = await (symphony.build_workflow()
                              .create("Multi-step Analysis", "Analysis with visualization")
                              .add_task("Data Analysis", "Analyze data", {
                                  "name": "Analysis",
                                  "description": "Analyze sales data",
                                  "input_data": {"query": "Analyze the quarterly sales trends"}
                              }, agent_id)
                              .build()
                              .execute())
    
    # Get workflow results
    results = await symphony.workflows.get_workflow_results(executed_workflow.id)
    print("\nWorkflow status:", results["status"])
    
    if "steps" in results:
        for step_name, result in results["steps"].items():
            print(f"\n{step_name}:")
            print("-" * 40)
            print(result)

asyncio.run(builder_pattern_example())
```

### Creating a Complete Application Using the API

Let's put it all together in a complete application example:

```python
import asyncio
import os
from symphony import Symphony, TaskPriority
from symphony.execution.workflow_tracker import WorkflowStatus

async def complete_api_example():
    """Complete example using the Symphony API."""
    print("\n=== Symphony API Complete Example ===\n")
    
    # Set up directory for storage
    os.makedirs("./data", exist_ok=True)
    
    # Initialize Symphony with file storage
    symphony = Symphony()
    await symphony.setup(persistence_type="file", base_dir="./data")
    
    # Create writer agent
    writer_agent = (symphony.build_agent()
                   .create("WriterAgent", "Content Writer",
                         "You are a creative content writer who excels at generating engaging content.")
                   .with_capabilities(["writing", "content", "creativity"])
                   .build())
    
    # Create editor agent
    editor_agent = (symphony.build_agent()
                   .create("EditorAgent", "Content Editor",
                         "You are a meticulous editor who excels at improving content clarity, flow, and correctness.")
                   .with_capabilities(["editing", "review", "clarity"])
                   .build())
    
    # Save agents
    writer_id = await symphony.agents.save_agent(writer_agent)
    editor_id = await symphony.agents.save_agent(editor_agent)
    print(f"Created agents: WriterAgent and EditorAgent")
    
    # Create a multi-stage content creation workflow
    workflow = (symphony.build_workflow()
               .create("Content Creation Pipeline", "Multi-stage pipeline for creating and refining content")
               
               # 1. Research step
               .add_task(
                   "Research",
                   "Research the topic",
                   {
                       "name": "Research",
                       "description": "Research the given topic and gather key points",
                       "input_data": {
                           "query": "Research the topic of 'artificial intelligence in healthcare' and provide 5 key points that should be covered in an article."
                       }
                   },
                   writer_id
               )
               
               # 2. First draft step
               .add_task(
                   "First Draft",
                   "Write the first draft based on research",
                   {
                       "name": "First Draft",
                       "description": "Write first draft based on research",
                       "input_data": {
                           "query": "Write a well-structured 500-word article about 'artificial intelligence in healthcare' covering the key points identified in the research phase."
                       }
                   },
                   writer_id
               )
               
               # 3. Review step
               .add_task(
                   "Editorial Review",
                   "Review the draft for clarity and accuracy",
                   {
                       "name": "Editorial Review",
                       "description": "Review for clarity, accuracy, and style",
                       "input_data": {
                           "query": "Review this article for clarity, factual accuracy, and style. Provide specific suggestions for improvement."
                       }
                   },
                   editor_id
               )
               
               # 4. Final revision step
               .add_task(
                   "Final Revision",
                   "Revise the draft based on review",
                   {
                       "name": "Final Revision",
                       "description": "Revise based on editorial review",
                       "input_data": {
                           "query": "Revise this article based on the editorial review. Create a polished final version."
                       }
                   },
                   writer_id
               )
               .build())
    
    # Save and execute workflow
    await symphony.workflows.save_workflow(workflow)
    print("Created and saved content creation workflow")
    
    print("Executing workflow...")
    executed_workflow = await symphony.workflows.execute_workflow(workflow)
    
    # Display results
    print(f"\nWorkflow completed with status: {executed_workflow.status}")
    
    if executed_workflow.status == WorkflowStatus.COMPLETED:
        # Get results using the facade
        results = await symphony.workflows.get_workflow_results(executed_workflow.id)
        
        # Find the final revision step
        final_result = next((result for step, result in results["steps"].items() 
                         if "Final Revision" in step), "Not found")
        
        print("\n=== Final Article ===")
        print("-" * 60)
        print(final_result)
        print("-" * 60)
        
        # Save output to a file
        with open("./data/final_article.md", "w") as f:
            f.write(final_result)
        print(f"\nOutput saved to ./data/final_article.md")

asyncio.run(complete_api_example())
```

## 5. Complete Application Example

Let's put it all together in a complete application example using the legacy approach:

```python
import asyncio
import os
import json
from typing import Dict, Any

from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep
from symphony.persistence.file_repository import FileSystemRepository
from symphony.orchestration import register_orchestration_components

async def complete_application_example():
    """Complete example demonstrating all Symphony layers working together."""
    print("\n=== Symphony Complete Application Example ===\n")
    
    # Set up directory for storage
    os.makedirs("./data", exist_ok=True)
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Create repositories
    task_repo = FileSystemRepository(Task, "./data")
    workflow_repo = FileSystemRepository(Workflow, "./data")
    agent_config_repo = FileSystemRepository(AgentConfig, "./data")
    workflow_def_repo = FileSystemRepository(WorkflowDefinition, "./data")
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("workflow_definition", workflow_def_repo)
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Create agent configurations
    writer_agent = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at generating engaging content.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    editor_agent = AgentConfig(
        name="EditorAgent",
        role="Content Editor",
        instruction_template="You are a meticulous editor who excels at improving content clarity, flow, and correctness.",
        capabilities=AgentCapabilities(
            expertise=["editing", "review", "clarity"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(writer_agent)
    await agent_config_repo.save(editor_agent)
    print(f"Created agent configurations for {writer_agent.name} and {editor_agent.name}")
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create a multi-stage content creation workflow
    workflow_def = WorkflowDefinition(
        name="Content Creation Pipeline",
        description="A multi-stage pipeline for creating and refining content"
    )
    
    # 1. Research step
    research_step = TaskStep(
        name="Research",
        description="Research the topic",
        task_template={
            "name": "Research",
            "description": "Research the given topic and gather key points",
            "input_data": {
                "query": "Research the topic of 'artificial intelligence in healthcare' and provide 5 key points that should be covered in an article."
            }
        },
        agent_id=writer_agent.id
    )
    
    # 2. First draft step
    draft_step = TaskStep(
        name="First Draft",
        description="Write the first draft based on research",
        task_template={
            "name": "First Draft",
            "description": "Write first draft based on research",
            "input_data": {
                "query": f"Write a well-structured 500-word article about 'artificial intelligence in healthcare' covering these key points:\n\n{{{{step.{research_step.id}.result}}}}"
            }
        },
        agent_id=writer_agent.id
    )
    
    # 3. Review step (parallel reviews from different perspectives)
    clarity_review_step = TaskStep(
        name="Clarity Review",
        description="Review for clarity and readability",
        task_template={
            "name": "Clarity Review",
            "description": "Review for clarity and readability",
            "input_data": {
                "query": f"Review this article for clarity and readability. Identify specific areas where the text could be clearer or more engaging:\n\n{{{{step.{draft_step.id}.result}}}}"
            }
        },
        agent_id=editor_agent.id
    )
    
    accuracy_review_step = TaskStep(
        name="Accuracy Review",
        description="Review for factual accuracy",
        task_template={
            "name": "Accuracy Review",
            "description": "Review for factual accuracy",
            "input_data": {
                "query": f"Review this article for factual accuracy. Identify any statements that might be incorrect or need verification:\n\n{{{{step.{draft_step.id}.result}}}}"
            }
        },
        agent_id=editor_agent.id
    )
    
    # Combine reviews in parallel
    parallel_review_step = ParallelStep(
        name="Parallel Reviews",
        description="Conduct multiple reviews in parallel",
        steps=[clarity_review_step, accuracy_review_step]
    )
    
    # 4. Final revision step
    revision_step = TaskStep(
        name="Final Revision",
        description="Revise the draft based on reviews",
        task_template={
            "name": "Final Revision",
            "description": "Revise the draft based on reviews",
            "input_data": {
                "query": f"Revise this article based on the following reviews:\n\nOriginal Draft:\n{{{{step.{draft_step.id}.result}}}}\n\nClarity Review:\n{{{{step.{parallel_review_step.id}.results.0.result}}}}\n\nAccuracy Review:\n{{{{step.{parallel_review_step.id}.results.1.result}}}}"
            }
        },
        agent_id=writer_agent.id
    )
    
    # Add all steps to the workflow
    workflow_def = workflow_def.add_step(research_step)
    workflow_def = workflow_def.add_step(draft_step)
    workflow_def = workflow_def.add_step(parallel_review_step)
    workflow_def = workflow_def.add_step(revision_step)
    
    # Save workflow definition
    await workflow_def_repo.save(workflow_def)
    print(f"Created and saved workflow definition: {workflow_def.name}")
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    print("Executing workflow...")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"\nWorkflow completed with status: {workflow.status}")
    
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow output summary:")
        context = workflow.metadata.get("context", {})
        
        # Get task results
        final_result = context.get(f"step.{revision_step.id}.result", "Not found")
        
        print("\n=== Final Article ===")
        print("-" * 60)
        print(final_result)
        print("-" * 60)
        
        # Save output to a file
        with open("./data/final_article.md", "w") as f:
            f.write(final_result)
        print(f"\nOutput saved to ./data/final_article.md")

# Run the example
asyncio.run(complete_application_example())
```

## Extending the Framework

### Creating Custom Step Types

You can extend the workflow orchestration layer by creating custom step types:

```python
from symphony.orchestration.workflow_definition import WorkflowStep, WorkflowContext, StepResult

class SummarizationStep(WorkflowStep):
    """Step that summarizes the outputs of previous steps."""
    
    def __init__(self, name, source_step_ids, max_length=200, description=""):
        super().__init__(name, description)
        self.source_step_ids = source_step_ids
        self.max_length = max_length
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Summarize outputs from source steps."""
        try:
            # Gather all source contents
            contents = []
            for step_id in self.source_step_ids:
                result = context.get(f"step.{step_id}.result")
                if result:
                    contents.append(result)
            
            if not contents:
                return StepResult(
                    success=False,
                    output={},
                    error="No source content found to summarize"
                )
            
            # Get task manager to create a summary task
            task_manager = context.get_service("task_manager")
            
            # Combine all content with proper spacing
            combined = "\n\n---\n\n".join(contents)
            
            # Create a summarization task
            summary_task = await task_manager.create_task(
                name=f"Summarize {self.name}",
                description=f"Summarize multiple pieces of content",
                input_data={
                    "query": f"Summarize the following content in no more than {self.max_length} words:\n\n{combined}"
                }
            )
            
            # Execute the task
            router = context.get_service("task_router")
            agent_factory = context.get_service("agent_factory")
            executor = context.get_service("enhanced_executor")
            
            agent_id = await router.route_task(summary_task)
            agent = await agent_factory.create_agent_from_id(agent_id)
            
            result_task = await executor.execute_task(
                summary_task.id,
                agent,
                workflow_id=context.workflow_id
            )
            
            # Store in context
            summary = result_task.output_data.get("result", "")
            context.set(f"step.{self.id}.result", summary)
            
            return StepResult(
                success=result_task.status == "completed",
                output={"result": summary},
                task_id=summary_task.id,
                error=result_task.error
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Summarization error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            "source_step_ids": self.source_step_ids,
            "max_length": self.max_length
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SummarizationStep':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            source_step_ids=data["source_step_ids"],
            max_length=data.get("max_length", 200)
        )
```

### Extension Points in the API Layer

The API layer is designed to be extended as well:

```python
from symphony.api import Symphony

# Extend the Symphony class with custom functionality
class EnhancedSymphony(Symphony):
    """Extended Symphony API with additional functionality."""
    
    async def setup_development_environment(self):
        """Set up a development environment with predefined agents and templates."""
        await self.setup(persistence_type="memory")
        
        # Create standard agents
        writer = await self.agents.create_agent(
            name="Writer",
            role="Content Writer",
            instruction_template="You write concise, helpful content.",
            capabilities={"expertise": ["writing", "communication"]}
        )
        
        analyst = await self.agents.create_agent(
            name="Analyst",
            role="Data Analyst",
            instruction_template="You analyze data and provide insights.",
            capabilities={"expertise": ["analysis", "data", "math"]}
        )
        
        reviewer = await self.agents.create_agent(
            name="Reviewer",
            role="Content Reviewer",
            instruction_template="You review content for quality and accuracy.",
            capabilities={"expertise": ["review", "editing", "fact-checking"]}
        )
        
        # Save the agents
        writer_id = await self.agents.save_agent(writer)
        analyst_id = await self.agents.save_agent(analyst)
        reviewer_id = await self.agents.save_agent(reviewer)
        
        return {
            "writer_id": writer_id,
            "analyst_id": analyst_id,
            "reviewer_id": reviewer_id
        }
    
    async def generate_report(self, topic, data_source, agent_ids=None):
        """Generate a comprehensive report on a topic using a predefined workflow."""
        # Create a multi-stage workflow for report generation
        workflow = (self.build_workflow()
                   .create(f"Report: {topic}", f"Generate a report on {topic}")
                   .add_task("Data Analysis", "Analyze the data", {
                       "name": "Data Analysis",
                       "description": f"Analyze data from {data_source}",
                       "input_data": {
                           "query": f"Analyze the following data from {data_source} related to {topic}. What are the key insights?"
                       }
                   }, agent_ids.get("analyst_id") if agent_ids else None)
                   .add_task("Report Draft", "Write report draft", {
                       "name": "Report Draft",
                       "description": "Write initial report draft",
                       "input_data": {
                           "query": f"Write a comprehensive report on {topic} based on this analysis. Include introduction, methods, results, and conclusion sections."
                       }
                   }, agent_ids.get("writer_id") if agent_ids else None)
                   .add_task("Review", "Review the report", {
                       "name": "Report Review",
                       "description": "Review the report for quality",
                       "input_data": {
                           "query": "Review this report for accuracy, clarity, and completeness. Suggest specific improvements."
                       }
                   }, agent_ids.get("reviewer_id") if agent_ids else None)
                   .add_task("Final Report", "Create final report", {
                       "name": "Final Report",
                       "description": "Create the final report",
                       "input_data": {
                           "query": "Revise the report based on the review. This should be the final, polished version."
                       }
                   }, agent_ids.get("writer_id") if agent_ids else None)
                   .build())
        
        # Execute the workflow
        executed_workflow = await self.workflows.execute_workflow(workflow)
        
        # Get results
        results = await self.workflows.get_workflow_results(executed_workflow.id)
        
        # Find the final report result
        final_report = next((result for step, result in results["steps"].items() 
                           if "Final Report" in step), "No report generated")
        
        return final_report
```

## Conclusion

This guide demonstrates the powerful capabilities of the Symphony framework with its four layers:

1. **Persistence Layer**: For storing and retrieving entities
2. **Execution Layer**: For executing tasks with advanced capabilities
3. **Orchestration Layer**: For defining and running complex workflows
4. **API Layer**: For providing clean, user-friendly interfaces

The API Layer improves developer experience by:

1. **Hiding implementation details**: The Registry pattern is powerful but exposes too many details
2. **Providing domain-specific interfaces**: Facades for common operations in workflows, agents, and tasks
3. **Enabling fluent interfaces**: Builders for creating complex objects with method chaining
4. **Simplifying setup**: Convenient initialization and configuration

When developing with Symphony, we recommend using the API Layer for most use cases. The underlying layers are still accessible for advanced use cases or when you need more control over the implementation details.

The framework is designed to be modular and extensible, allowing you to:

- Add custom storage implementations to the Persistence Layer
- Extend the Execution Layer with new execution strategies
- Create custom step types and workflow templates in the Orchestration Layer
- Extend the API Layer with custom facades and builders

This modular design ensures that Symphony can grow and adapt to your specific needs while maintaining a consistent architecture and API.