"""Goal management system for Symphony agents."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from symphony.utils.types import Message


class GoalStatus(str, Enum):
    """Status of a goal."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class SuccessCriterion(BaseModel):
    """A criterion for determining if a goal has been completed successfully."""
    
    description: str
    validation_function: Optional[str] = None
    is_met: bool = False
    evidence: Optional[str] = None


class Goal(BaseModel):
    """Representation of a goal in the system."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    success_criteria: List[SuccessCriterion] = Field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_success_criterion(self, description: str) -> SuccessCriterion:
        """Add a success criterion to the goal."""
        criterion = SuccessCriterion(description=description)
        self.success_criteria.append(criterion)
        return criterion
    
    def update_status(self, status: GoalStatus) -> None:
        """Update the status of the goal."""
        self.status = status
        self.updated_at = datetime.now()
        
        if status == GoalStatus.COMPLETED:
            self.completed_at = datetime.now()
    
    def is_completed(self) -> bool:
        """Check if the goal is completed."""
        # A goal is completed if all success criteria are met or status is COMPLETED
        if self.status == GoalStatus.COMPLETED:
            return True
            
        if not self.success_criteria:
            return False
            
        return all(criterion.is_met for criterion in self.success_criteria)
    
    def set_criterion_met(self, index: int, is_met: bool, evidence: Optional[str] = None) -> None:
        """Set a success criterion as met or not met."""
        if 0 <= index < len(self.success_criteria):
            self.success_criteria[index].is_met = is_met
            if evidence:
                self.success_criteria[index].evidence = evidence
            
            # Update status if all criteria are met
            if all(criterion.is_met for criterion in self.success_criteria):
                self.update_status(GoalStatus.COMPLETED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary format."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "parent_id": self.parent_id,
            "success_criteria": [
                {"description": sc.description, "is_met": sc.is_met}
                for sc in self.success_criteria
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class GoalManager:
    """Manager for goal tracking and decomposition."""
    
    def __init__(self, llm_client = None):
        self.goals: Dict[str, Goal] = {}
        self.goal_hierarchy: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self.llm_client = llm_client
    
    def create_goal(
        self, 
        description: str, 
        success_criteria: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Goal:
        """Create a new goal."""
        # Create success criteria
        criteria_models = []
        if success_criteria:
            criteria_models = [
                SuccessCriterion(description=criterion)
                for criterion in success_criteria
            ]
        
        # Create goal
        goal = Goal(
            description=description,
            success_criteria=criteria_models,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        # Store goal
        self.goals[goal.id] = goal
        
        # Update hierarchy
        if parent_id:
            if parent_id not in self.goal_hierarchy:
                self.goal_hierarchy[parent_id] = []
            self.goal_hierarchy[parent_id].append(goal.id)
        
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self.goals.get(goal_id)
    
    def get_subgoals(self, parent_id: str) -> List[Goal]:
        """Get all subgoals of a goal."""
        child_ids = self.goal_hierarchy.get(parent_id, [])
        return [self.goals[child_id] for child_id in child_ids if child_id in self.goals]
    
    def update_goal_status(self, goal_id: str, status: GoalStatus) -> Optional[Goal]:
        """Update the status of a goal."""
        goal = self.get_goal(goal_id)
        if goal:
            goal.update_status(status)
            
            # Check if this completes the parent goal
            if status == GoalStatus.COMPLETED and goal.parent_id:
                self._check_parent_completion(goal.parent_id)
                
        return goal
    
    def _check_parent_completion(self, parent_id: str) -> None:
        """Check if a parent goal is completed based on subgoals."""
        parent = self.get_goal(parent_id)
        if not parent:
            return
            
        # Get subgoals
        subgoals = self.get_subgoals(parent_id)
        
        # Check if all subgoals are completed
        if all(subgoal.status == GoalStatus.COMPLETED for subgoal in subgoals):
            parent.update_status(GoalStatus.COMPLETED)
            
            # Recursively check parent's parent
            if parent.parent_id:
                self._check_parent_completion(parent.parent_id)
    
    async def decompose_goal(
        self, 
        goal_id: str, 
        max_subgoals: int = 5
    ) -> List[Goal]:
        """Decompose a goal into subgoals using LLM."""
        goal = self.get_goal(goal_id)
        if not goal or not self.llm_client:
            return []
            
        # Prepare prompt for decomposition
        prompt = f"""Task: Decompose the following goal into {max_subgoals} or fewer clear, specific subgoals.

GOAL: {goal.description}

For each subgoal, provide:
1. A clear description of the subgoal
2. 1-3 specific success criteria for the subgoal

Format your response as a JSON array like this:
```json
[
  {{
    "description": "Subgoal 1 description",
    "success_criteria": ["Criterion 1", "Criterion 2"]
  }},
  {{
    "description": "Subgoal 2 description",
    "success_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"]
  }}
]
```

Ensure each subgoal:
- Is specific and actionable
- Has measurable success criteria
- Together with other subgoals, fully addresses the main goal
"""
        
        try:
            # Get decomposition from LLM
            response = await self.llm_client.generate(prompt)
            
            # Extract JSON
            # Look for JSON between code fences, or just take the whole response
            json_str = response
            if "```json" in response and "```" in response.split("```json", 1)[1]:
                json_str = response.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in response and "```" in response.split("```", 1)[1]:
                json_str = response.split("```", 1)[1].split("```", 1)[0].strip()
            
            # Parse subgoals
            import json
            subgoal_data = json.loads(json_str)
            
            # Create subgoals
            created_subgoals = []
            for item in subgoal_data:
                if isinstance(item, dict) and "description" in item:
                    subgoal = self.create_goal(
                        description=item["description"],
                        success_criteria=item.get("success_criteria", []),
                        parent_id=goal_id
                    )
                    created_subgoals.append(subgoal)
            
            return created_subgoals
            
        except Exception as e:
            print(f"Error decomposing goal: {str(e)}")
            return []
    
    def get_goal_tree(self, root_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the goal tree starting from a root goal."""
        if root_id and root_id not in self.goals:
            return {}
            
        # If no root specified, find top-level goals
        if not root_id:
            top_goals = {
                goal_id: goal for goal_id, goal in self.goals.items()
                if not goal.parent_id
            }
            
            if not top_goals:
                return {}
                
            if len(top_goals) == 1:
                # If only one top goal, return its tree
                root_id = next(iter(top_goals.keys()))
            else:
                # Return all top-level goals
                return {
                    "goals": [self.get_goal_tree(goal_id) for goal_id in top_goals.keys()]
                }
        
        # Get the root goal
        root_goal = self.goals[root_id]
        
        # Get children
        children = []
        for child_id in self.goal_hierarchy.get(root_id, []):
            if child_id in self.goals:
                children.append(self.get_goal_tree(child_id))
        
        # Build tree
        return {
            "goal": root_goal.to_dict(),
            "children": children
        }
    
    def mark_criterion_met(
        self, 
        goal_id: str, 
        criterion_index: int, 
        evidence: Optional[str] = None
    ) -> bool:
        """Mark a success criterion as met."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False
            
        if criterion_index < 0 or criterion_index >= len(goal.success_criteria):
            return False
            
        goal.set_criterion_met(criterion_index, True, evidence)
        return True


class GoalConditionedAgentMixin:
    """Mixin that adds goal-conditioned capabilities to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize goal manager
        self.goal_manager = GoalManager(
            llm_client=getattr(self, "llm_client", None)
        )
        
        # Current active goal
        self.active_goal_id: Optional[str] = None
    
    def set_goal(
        self, 
        description: str, 
        success_criteria: Optional[List[str]] = None
    ) -> Goal:
        """Set the current goal for the agent."""
        goal = self.goal_manager.create_goal(
            description=description,
            success_criteria=success_criteria
        )
        
        self.active_goal_id = goal.id
        goal.update_status(GoalStatus.IN_PROGRESS)
        
        return goal
    
    async def decompose_active_goal(self) -> List[Goal]:
        """Decompose the active goal into subgoals."""
        if not self.active_goal_id:
            return []
            
        return await self.goal_manager.decompose_goal(self.active_goal_id)
    
    def get_active_goal(self) -> Optional[Goal]:
        """Get the active goal."""
        if not self.active_goal_id:
            return None
            
        return self.goal_manager.get_goal(self.active_goal_id)
    
    def get_active_goal_context(self) -> Dict[str, Any]:
        """Get context information about the active goal."""
        if not self.active_goal_id:
            return {"has_goal": False}
            
        goal = self.get_active_goal()
        if not goal:
            return {"has_goal": False}
            
        subgoals = self.goal_manager.get_subgoals(self.active_goal_id)
        
        # Create context
        context = {
            "has_goal": True,
            "goal": {
                "description": goal.description,
                "status": goal.status,
                "progress": sum(1 for c in goal.success_criteria if c.is_met) / 
                            max(1, len(goal.success_criteria))
            },
            "success_criteria": [
                {"description": c.description, "is_met": c.is_met}
                for c in goal.success_criteria
            ],
            "has_subgoals": len(subgoals) > 0,
            "subgoals_count": len(subgoals),
            "completed_subgoals": sum(1 for sg in subgoals if sg.status == GoalStatus.COMPLETED)
        }
        
        return context
    
    def format_goal_for_prompt(self) -> str:
        """Format the active goal for inclusion in prompts."""
        if not self.active_goal_id:
            return "No active goal."
            
        goal = self.get_active_goal()
        if not goal:
            return "No active goal."
            
        subgoals = self.goal_manager.get_subgoals(self.active_goal_id)
        
        # Format goal and criteria
        result = [f"Goal: {goal.description}"]
        
        if goal.success_criteria:
            result.append("\nSuccess Criteria:")
            for i, criterion in enumerate(goal.success_criteria):
                status = "✅" if criterion.is_met else "⬜"
                result.append(f"{status} {i+1}. {criterion.description}")
        
        # Format subgoals if any
        if subgoals:
            result.append("\nSubgoals:")
            for i, subgoal in enumerate(subgoals):
                status = "✅" if subgoal.status == GoalStatus.COMPLETED else "⬜"
                result.append(f"{status} {i+1}. {subgoal.description}")
        
        return "\n".join(result)