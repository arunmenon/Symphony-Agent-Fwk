"""Planning-based agent implementation."""

import json
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from symphony.agents.base import AgentBase
from symphony.utils.types import Message


class Step(BaseModel):
    """A step in a plan."""
    
    id: int
    description: str
    is_complete: bool = False
    result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "is_complete": self.is_complete,
            "result": self.result
        }


class Plan(BaseModel):
    """A plan composed of steps."""
    
    steps: List[Step] = Field(default_factory=list)
    current_step_id: Optional[int] = None
    
    def add_step(self, description: str) -> Step:
        """Add a step to the plan."""
        step_id = len(self.steps) + 1
        step = Step(id=step_id, description=description)
        self.steps.append(step)
        
        if self.current_step_id is None:
            self.current_step_id = step_id
            
        return step
    
    def complete_step(self, step_id: int, result: str) -> None:
        """Mark a step as complete with a result."""
        for step in self.steps:
            if step.id == step_id:
                step.is_complete = True
                step.result = result
                break
                
        # Move to next step
        if self.current_step_id == step_id:
            next_id = self.find_next_incomplete_step()
            if next_id:
                self.current_step_id = next_id
            
    def find_next_incomplete_step(self) -> Optional[int]:
        """Find the next incomplete step."""
        for step in self.steps:
            if not step.is_complete:
                return step.id
        return None
    
    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(step.is_complete for step in self.steps)
    
    def get_step(self, step_id: int) -> Optional[Step]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_current_step(self) -> Optional[Step]:
        """Get the current step."""
        if self.current_step_id is None:
            return None
            
        return self.get_step(self.current_step_id)
    
    def to_string(self) -> str:
        """Convert plan to string representation."""
        result = ["# Current Plan:"]
        
        for step in self.steps:
            status = "✅" if step.is_complete else "⏳" if step.id == self.current_step_id else "⏱️"
            result.append(f"{status} Step {step.id}: {step.description}")
            
            if step.is_complete and step.result:
                result.append(f"   Result: {step.result}")
                
        return "\n".join(result)


class PlannerAgent(AgentBase):
    """An agent that creates and follows a plan."""
    
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.plan: Optional[Plan] = None
    
    async def run(self, input_message: str) -> str:
        """Run the agent on an input message and return a response."""
        # Reset plan for new requests
        self.plan = None
        return await super().run(input_message)
    
    async def decide_action(self, messages: List[Message]) -> Message:
        """Decide what action to take given the current context."""
        # If we don't have a plan yet, create one
        if not self.plan:
            planning_messages = list(messages)  # Copy messages
            
            # Add planning instruction
            planning_messages.append(Message(
                role="user",
                content=(
                    "Based on the above context, create a step-by-step plan to complete the task. "
                    "Format your response as a JSON array of steps, where each step has a 'description' field. "
                    "For example: [{'description': 'Search for information about X'}, {'description': 'Summarize findings'}]"
                )
            ))
            
            # Generate plan
            plan_response = await self.llm_client.chat(planning_messages)
            self.plan = await self._parse_plan(plan_response.content)
            
            # Return the plan as a message
            return Message(
                role="assistant",
                content=f"I'll help you with that. Here's my plan:\n\n{self.plan.to_string()}\n\nLet me start working on this."
            )
        
        # If we have a plan, execute the current step
        current_step = self.plan.get_current_step()
        
        if not current_step:
            # Plan is complete or invalid
            if self.plan.is_complete():
                return Message(
                    role="assistant",
                    content=f"I've completed all steps in the plan.\n\n{self.plan.to_string()}"
                )
            else:
                # Something went wrong
                return Message(
                    role="assistant",
                    content="I'm having trouble with the current plan. Let me reconsider the approach."
                )
        
        # Execute the current step
        step_messages = list(messages)
        step_messages.append(Message(
            role="user",
            content=f"Current step to execute: {current_step.description}\n\nComplete this step and provide your results."
        ))
        
        step_response = await self.llm_client.chat(step_messages)
        
        # Mark step as complete
        self.plan.complete_step(current_step.id, step_response.content)
        
        # If this was the last step, return a completion message
        if self.plan.is_complete():
            return Message(
                role="assistant",
                content=f"I've completed the plan.\n\n{self.plan.to_string()}\n\n{step_response.content}"
            )
        
        # Otherwise, return the step result and the next step
        next_step = self.plan.get_current_step()
        return Message(
            role="assistant",
            content=f"{step_response.content}\n\n{self.plan.to_string()}\n\nNow I'll work on the next step: {next_step.description}"
        )
    
    async def _parse_plan(self, plan_text: str) -> Plan:
        """Parse a plan from text, which might be JSON or natural language."""
        plan = Plan()
        
        try:
            # Try to extract JSON from the text
            start_idx = plan_text.find('[')
            end_idx = plan_text.rfind(']')
            
            if start_idx >= 0 and end_idx > start_idx:
                json_text = plan_text[start_idx:end_idx+1]
                steps_data = json.loads(json_text)
                
                for step_data in steps_data:
                    if isinstance(step_data, dict) and 'description' in step_data:
                        plan.add_step(step_data['description'])
            else:
                # If no JSON, try to parse as numbered list
                lines = plan_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Look for numbered steps like "1. Do something" or "Step 1: Do something"
                    if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                            line.lower().startswith(('step 1', 'step 2', 'step 3', 'step 4', 'step 5'))):
                        # Extract the description after the number
                        parts = line.split(':', 1) if ':' in line else line.split('.', 1)
                        if len(parts) > 1:
                            description = parts[1].strip()
                            plan.add_step(description)
        except Exception as e:
            # If parsing fails, create a single-step plan
            plan.add_step(f"Complete the task based on: {plan_text[:100]}...")
            
        # If we couldn't parse any steps, create a default step
        if not plan.steps:
            plan.add_step("Analyze the request and provide a response")
            
        return plan