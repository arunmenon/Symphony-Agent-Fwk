"""Domain-specific importance evaluation strategies for memory management."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from symphony.memory.importance import ImportanceStrategy, RuleBasedStrategy


class CustomerSupportStrategy(RuleBasedStrategy):
    """Specialized importance strategy for customer support scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.4,
        user_bonus: float = 0.1,
        base_importance: float = 0.5
    ):
        """Initialize customer support strategy with domain-specific keywords."""
        # Define customer support-specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "order", "refund", "cancel", "return", "shipping",
                "delivery", "payment", "warranty", "broken", "damaged",
                "complaint", "urgent", "issue", "problem", "support",
                "replacement", "missing", "delayed", "account", "subscription"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with customer support-specific logic."""
        importance = await super().calculate_importance(content, context)
        
        # Increase importance for order-related queries with order IDs
        if "order" in content.lower() and re.search(r'(\b[A-Z0-9]+-\d+\b|\b#\d+\b)', content):
            importance += 0.2
            
        # Increase importance for urgent issues
        urgent_terms = ["urgent", "immediately", "asap", "emergency", "today", "right now"]
        if any(term in content.lower() for term in urgent_terms):
            importance += 0.2
            
        # Increase importance for reports of serious problems
        problem_terms = ["broken", "damaged", "not working", "defective", "error", "failed"]
        if any(term in content.lower() for term in problem_terms):
            importance += 0.15
            
        # Increase importance for refund/return requests
        refund_terms = ["refund", "return", "money back", "credit", "exchange"]
        if any(term in content.lower() for term in refund_terms):
            importance += 0.15
            
        # Increase importance for customer sentiment indicators
        negative_sentiment = ["frustrated", "disappointed", "angry", "upset", "unhappy", "terrible"]
        if any(term in content.lower() for term in negative_sentiment):
            importance += 0.2
            
        # Cap at 1.0
        return min(importance, 1.0)


class ProductResearchStrategy(RuleBasedStrategy):
    """Specialized importance strategy for product research and development."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        user_bonus: float = 0.1,
        base_importance: float = 0.5,
        product_categories: Optional[List[str]] = None,
        feature_terms: Optional[List[str]] = None
    ):
        """Initialize product research strategy with domain-specific parameters."""
        # Define research-specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "research", "develop", "test", "prototype", "experiment",
                "feature", "design", "requirement", "specification", "roadmap", 
                "priority", "deadline", "milestone", "launch", "release"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        # Domain-specific parameter lists
        self.product_categories = product_categories or []
        self.feature_terms = feature_terms or [
            "performance", "reliability", "usability", "efficiency", 
            "maintainability", "security", "compatibility", "scalability"
        ]
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with product research-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for metric/measurement mentions
        if re.search(r'\b\d+(\.\d+)?\s*(ms|seconds|minutes|fps|mb|gb|%|percent)\b', content_lower):
            importance += 0.15
            
        # Increase importance for feature discussions
        if any(term in content_lower for term in self.feature_terms):
            importance += 0.15
            
        # Increase importance for product category mentions
        if self.product_categories and any(category.lower() in content_lower for category in self.product_categories):
            importance += 0.1
            
        # Increase importance for competitive analysis mentions
        competitor_indicators = ["competitor", "competition", "market", "industry", "versus", "compared to"]
        if any(indicator in content_lower for indicator in competitor_indicators):
            importance += 0.15
            
        # Increase importance for user feedback mentions
        feedback_indicators = ["user feedback", "customer response", "user testing", "survey", "user experience", "ux"]
        if any(indicator in content_lower for indicator in feedback_indicators):
            importance += 0.2
            
        # Increase importance for decision-making content
        decision_indicators = ["decide", "conclusion", "determined", "finalized", "agreed", "consensus"]
        if any(indicator in content_lower for indicator in decision_indicators):
            importance += 0.3
        
        # Cap at 1.0
        return min(importance, 1.0)


class PersonalAssistantStrategy(RuleBasedStrategy):
    """Specialized importance strategy for personal assistant scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        user_bonus: float = 0.1,
        base_importance: float = 0.5,
        user_contacts: Optional[List[str]] = None,
        user_interests: Optional[List[str]] = None
    ):
        """Initialize personal assistant strategy with user-specific parameters."""
        # Define assistant-specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "schedule", "reminder", "appointment", "meeting", "call",
                "task", "priority", "deadline", "important", "remember",
                "don't forget", "must", "should", "need to", "birthday"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        # User-specific parameters
        self.user_contacts = user_contacts or []
        self.user_interests = user_interests or []
        
        # Date and time pattern for scheduling-related content
        self.datetime_pattern = re.compile(
            r'(\b\d{1,2}[:/\-]\d{1,2}([:/\-]\d{2,4})?\b)|'  # Dates like 04/15/2024
            r'(\b\d{1,2}(:\d{2})?\s*(am|pm|AM|PM)\b)|'      # Times like 3:30pm
            r'(\b(today|tomorrow|next week|next month)\b)|'  # Relative dates
            r'(\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b)'  # Days
        )
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with personal assistant-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for date/time mentions (scheduling)
        if self.datetime_pattern.search(content):
            importance += 0.25
            
        # Increase importance for contact mentions
        if self.user_contacts and any(contact.lower() in content_lower for contact in self.user_contacts):
            importance += 0.2
            
        # Increase importance for user interest mentions
        if self.user_interests and any(interest.lower() in content_lower for interest in self.user_interests):
            importance += 0.1
            
        # Increase importance for potential requests/commands
        request_indicators = ["can you", "please", "would you", "I need", "I want", "help me"]
        if any(indicator in content_lower for indicator in request_indicators):
            importance += 0.15
            
        # Increase importance for recurring items
        recurring_indicators = ["daily", "weekly", "monthly", "every day", "each week", "regularly"]
        if any(indicator in content_lower for indicator in recurring_indicators):
            importance += 0.2
            
        # Increase importance for personal information
        personal_indicators = ["password", "address", "phone", "email", "account", "contact", "preference"]
        if any(indicator in content_lower for indicator in personal_indicators):
            importance += 0.2
        
        # Cap at 1.0
        return min(importance, 1.0)


class EducationalStrategy(RuleBasedStrategy):
    """Specialized importance strategy for educational and learning scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.3,  # Higher question bonus for educational context
        action_bonus: float = 0.2,
        user_bonus: float = 0.1,
        base_importance: float = 0.5,
        subjects: Optional[List[str]] = None,
        learning_level: str = "general"  # general, beginner, intermediate, advanced
    ):
        """Initialize educational strategy with learning-specific parameters."""
        # Define education-specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "learn", "study", "understand", "concept", "principle",
                "remember", "explain", "definition", "example", "practice",
                "assignment", "exercise", "problem", "solution", "quiz", "test",
                "exam", "project", "deadline", "important", "key point"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        # Subject-specific parameters
        self.subjects = subjects or []
        self.learning_level = learning_level
        
        # Level-specific difficulty terms
        self.difficulty_terms = {
            "beginner": ["basic", "fundamentals", "introduction", "beginner", "starting", "easy"],
            "intermediate": ["intermediate", "moderately", "further", "deeper", "building on"],
            "advanced": ["advanced", "complex", "challenging", "difficult", "in-depth", "expert"]
        }
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with educational-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for subject mentions
        if self.subjects and any(subject.lower() in content_lower for subject in self.subjects):
            importance += 0.15
            
        # Increase importance for level-appropriate content
        if self.learning_level != "general" and self.learning_level in self.difficulty_terms:
            level_terms = self.difficulty_terms[self.learning_level]
            if any(term in content_lower for term in level_terms):
                importance += 0.2
            
        # Increase importance for definitional content
        definition_indicators = ["is defined as", "refers to", "is a", "means", "definition", "concept of"]
        if any(indicator in content_lower for indicator in definition_indicators):
            importance += 0.25
            
        # Increase importance for examples
        example_indicators = ["example", "instance", "case", "illustration", "demonstrate", "shown by"]
        if any(indicator in content_lower for indicator in example_indicators):
            importance += 0.2
            
        # Increase importance for key principles
        principle_indicators = ["principle", "rule", "law", "theorem", "formula", "equation", "key idea"]
        if any(indicator in content_lower for indicator in principle_indicators):
            importance += 0.3
            
        # Increase importance for assessment-related content
        assessment_indicators = ["test", "quiz", "exam", "assessment", "evaluation", "graded"]
        if any(indicator in content_lower for indicator in assessment_indicators):
            importance += 0.25
        
        # Cap at 1.0
        return min(importance, 1.0)


class MedicalAssistantStrategy(RuleBasedStrategy):
    """Specialized importance strategy for medical and healthcare scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.3,
        action_bonus: float = 0.4,
        user_bonus: float = 0.1,
        base_importance: float = 0.6,  # Higher base importance for medical context
        medical_terms: Optional[List[str]] = None,
        severity_terms: Optional[List[str]] = None
    ):
        """Initialize medical assistant strategy with healthcare-specific parameters."""
        # Define medical-specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "medication", "treatment", "symptoms", "diagnosis", "prescription",
                "dosage", "side effect", "appointment", "emergency", "urgent",
                "consult", "schedule", "follow up", "monitor", "allergic"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        # Medical-specific parameters
        self.medical_terms = medical_terms or []
        self.severity_terms = severity_terms or [
            "severe", "critical", "emergency", "acute", "chronic", 
            "painful", "debilitating", "unbearable", "intense"
        ]
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with medical-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for medical term mentions
        if self.medical_terms and any(term.lower() in content_lower for term in self.medical_terms):
            importance += 0.15
            
        # Increase importance for severity mentions
        if any(term in content_lower for term in self.severity_terms):
            importance += 0.3
            
        # Increase importance for medication-related content
        medication_indicators = ["dosage", "dose", "mg", "tablet", "capsule", "pill", "prescription"]
        if any(indicator in content_lower for indicator in medication_indicators):
            importance += 0.25
            
        # Increase importance for symptom descriptions
        symptom_indicators = ["symptom", "feeling", "pain", "discomfort", "experiencing"]
        if any(indicator in content_lower for indicator in symptom_indicators):
            importance += 0.2
            
        # Increase importance for timing-related medical content
        timing_indicators = ["since", "last", "hours", "days", "weeks", "onset", "duration", "frequency"]
        if any(indicator in content_lower for indicator in timing_indicators):
            importance += 0.15
            
        # Highest importance for potential emergencies
        emergency_indicators = ["emergency", "immediate", "hospital", "ambulance", "urgent care", "severe"]
        if any(indicator in content_lower for indicator in emergency_indicators):
            importance += 0.4
            
        # High importance for patient history information
        history_indicators = ["history", "previous", "diagnosed", "condition", "chronic", "allergic to"]
        if any(indicator in content_lower for indicator in history_indicators):
            importance += 0.25
        
        # Cap at 1.0 (most medical information is important)
        return min(importance, 1.0)