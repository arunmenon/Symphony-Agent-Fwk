"""Factory for creating importance evaluation strategies."""

from typing import Any, Dict, List, Optional, Union

from symphony.memory.importance import (
    ImportanceStrategy, 
    RuleBasedStrategy, 
    LLMBasedStrategy, 
    HybridStrategy
)
from symphony.memory.domain_strategies import (
    CustomerSupportStrategy,
    ProductResearchStrategy,
    PersonalAssistantStrategy,
    EducationalStrategy,
    MedicalAssistantStrategy
)


class ImportanceStrategyFactory:
    """Factory for creating appropriate importance strategies."""
    
    @staticmethod
    def create_strategy(
        strategy_type: str,
        **kwargs
    ) -> ImportanceStrategy:
        """Create an importance evaluation strategy based on specified type.
        
        Args:
            strategy_type: Type of strategy to create
                Basic types: "rule", "llm", "hybrid"
                Domain-specific: "customer_support", "product_research", 
                "personal_assistant", "educational", "medical"
            **kwargs: Strategy-specific configuration parameters
            
        Returns:
            The configured importance strategy
            
        Raises:
            ValueError: If strategy_type is not recognized
        """
        # Basic strategies
        if strategy_type == "rule":
            return RuleBasedStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.2),
                action_bonus=kwargs.get("action_bonus", 0.3),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.5)
            )
            
        elif strategy_type == "llm":
            if "llm_client" not in kwargs:
                raise ValueError("LLM strategy requires llm_client parameter")
                
            return LLMBasedStrategy(
                llm_client=kwargs["llm_client"],
                prompt_registry=kwargs.get("prompt_registry"),
                prompt_key=kwargs.get("prompt_key", "memory.importance_assessment"),
                default_prompt=kwargs.get("default_prompt")
            )
            
        elif strategy_type == "hybrid":
            if "strategies" not in kwargs:
                # Create default hybrid with rule-based and optional LLM
                strategies = []
                
                # Add rule-based strategy
                rule_strategy = RuleBasedStrategy()
                strategies.append((rule_strategy, kwargs.get("rule_weight", 0.5)))
                
                # Add LLM strategy if client provided
                if "llm_client" in kwargs:
                    llm_strategy = LLMBasedStrategy(llm_client=kwargs["llm_client"])
                    strategies.append((llm_strategy, kwargs.get("llm_weight", 0.5)))
                    
                return HybridStrategy(strategies)
            else:
                # Use provided strategies
                return HybridStrategy(kwargs["strategies"])
                
        # Domain-specific strategies
        elif strategy_type == "customer_support":
            return CustomerSupportStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.2),
                action_bonus=kwargs.get("action_bonus", 0.4),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.5)
            )
            
        elif strategy_type == "product_research":
            return ProductResearchStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.2),
                action_bonus=kwargs.get("action_bonus", 0.3),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.5),
                product_categories=kwargs.get("product_categories"),
                feature_terms=kwargs.get("feature_terms")
            )
            
        elif strategy_type == "personal_assistant":
            return PersonalAssistantStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.2),
                action_bonus=kwargs.get("action_bonus", 0.3),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.5),
                user_contacts=kwargs.get("user_contacts"),
                user_interests=kwargs.get("user_interests")
            )
            
        elif strategy_type == "educational":
            return EducationalStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.3),
                action_bonus=kwargs.get("action_bonus", 0.2),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.5),
                subjects=kwargs.get("subjects"),
                learning_level=kwargs.get("learning_level", "general")
            )
            
        elif strategy_type == "medical":
            return MedicalAssistantStrategy(
                action_keywords=kwargs.get("action_keywords"),
                question_bonus=kwargs.get("question_bonus", 0.3),
                action_bonus=kwargs.get("action_bonus", 0.4),
                user_bonus=kwargs.get("user_bonus", 0.1),
                base_importance=kwargs.get("base_importance", 0.6),
                medical_terms=kwargs.get("medical_terms"),
                severity_terms=kwargs.get("severity_terms")
            )
            
        # Domain-specific hybrid strategies
        elif strategy_type.startswith("hybrid_"):
            domain = strategy_type[7:]  # Extract domain part after "hybrid_"
            
            if "llm_client" not in kwargs:
                raise ValueError("Hybrid domain strategy requires llm_client parameter")
                
            # Create domain strategy
            domain_strategy = ImportanceStrategyFactory.create_strategy(domain, **kwargs)
            
            # Create LLM strategy
            llm_strategy = LLMBasedStrategy(
                llm_client=kwargs["llm_client"],
                prompt_registry=kwargs.get("prompt_registry"),
                prompt_key=kwargs.get("prompt_key", f"memory.{domain}.importance_assessment"),
                default_prompt=kwargs.get("default_prompt")
            )
            
            # Create hybrid with domain and LLM strategies
            return HybridStrategy([
                (domain_strategy, kwargs.get("domain_weight", 0.7)),
                (llm_strategy, kwargs.get("llm_weight", 0.3))
            ])
            
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
            
    @staticmethod
    def create_domain_hybrid(
        domain_strategy: ImportanceStrategy,
        llm_client,
        domain_weight: float = 0.7,
        llm_weight: float = 0.3,
        prompt_registry = None,
        prompt_key: Optional[str] = None,
        default_prompt: Optional[str] = None
    ) -> HybridStrategy:
        """Create a hybrid strategy combining a domain-specific strategy with LLM assessment.
        
        Args:
            domain_strategy: Domain-specific strategy instance
            llm_client: LLM client for semantic importance assessment
            domain_weight: Weight for domain strategy (0.0-1.0)
            llm_weight: Weight for LLM strategy (0.0-1.0)
            prompt_registry: Optional registry for prompt templates
            prompt_key: Key to retrieve prompt from registry
            default_prompt: Default prompt if registry is unavailable
            
        Returns:
            Hybrid strategy combining domain rules with LLM assessment
        """
        llm_strategy = LLMBasedStrategy(
            llm_client=llm_client,
            prompt_registry=prompt_registry,
            prompt_key=prompt_key,
            default_prompt=default_prompt
        )
        
        return HybridStrategy([
            (domain_strategy, domain_weight),
            (llm_strategy, llm_weight)
        ])