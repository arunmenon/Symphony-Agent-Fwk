"""Example of how to use the PromptLoader utility.

This demonstrates how to load and format templates using the generic PromptLoader.
"""

import os
import logging
from prompt_utils import PromptLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate PromptLoader usage."""
    # Get path to task-prompts directory
    current_dir = os.path.dirname(os.path.dirname(__file__))
    task_prompts_dir = os.path.join(current_dir, "task-prompts")
    
    # Create loader with task-prompts directory
    loader = PromptLoader(template_dirs=[task_prompts_dir])
    logger.info(f"Created prompt loader with directory: {task_prompts_dir}")
    
    # Load the planning template
    planning_template = loader.load_template("planning")
    if planning_template:
        logger.info("Successfully loaded planning template")
        
        # Get required variables
        variables = loader.get_template_variables("planning")
        logger.info(f"Template requires variables: {variables}")
        
        # Format the template with variables
        formatted = loader.format_template(
            "planning", 
            root_category="Weapons",
            enhanced_fields="description, risk_level, enforcement_examples",
            jurisdictions="USA, EU, Canada"
        )
        
        print("\n--- Formatted Planning Template ---")
        print(formatted)
        print("----------------------------------\n")
        
    # Load and format exploration template
    exploration_template = loader.format_template(
        "exploration",
        category="Weapons",
        enhanced_fields="description, risk_level, enforcement_examples",
        jurisdictions="USA, EU, Canada",
        initial_categories="Firearms, Knives, Explosives",
        taxonomy_plan="Initial hierarchical taxonomy plan..."
    )
    
    if exploration_template:
        print("\n--- Formatted Exploration Template ---")
        print(exploration_template)
        print("-------------------------------------\n")
    
    # Validate template variables
    variables = {
        "category": "Weapons",
        "enhanced_fields": "description, risk_level",
        # Missing: jurisdictions
    }
    
    missing = loader.validate_variables("exploration", variables)
    if missing:
        logger.warning(f"Missing variables: {missing}")
        
    # Complete variables
    variables["jurisdictions"] = "USA, EU"
    variables["initial_categories"] = "Firearms, Knives"
    variables["taxonomy_plan"] = "Plan..."
    
    missing = loader.validate_variables("exploration", variables)
    if not missing:
        logger.info("All required variables are provided")

if __name__ == "__main__":
    main()