# Symphony Implementation Plan

## Phase 1: Core Architecture Foundations

### Goal-Plan Bridge

#### 1. Create GoalPlanManager
- Implement a centralized manager to coordinate between goals and plans
- Add bidirectional linkages between goals and their associated plans
- Develop automatic plan generation from goals using LLM
- Create mechanisms to update goal progress as plans execute

```python
class GoalPlanManager:
    """Centralized manager for coordinating goals and plans."""
    
    def __init__(self, llm_client = None):
        self.goal_manager = GoalManager(llm_client)
        self.plans = {}  # goal_id -> Plan
        self.llm_client = llm_client
        
    async def create_goal_with_plan(self, description, success_criteria=None):
        """Create a goal and automatically generate a plan for it."""
        goal = self.goal_manager.create_goal(description, success_criteria)
        plan = await self.generate_plan_for_goal(goal.id)
        return goal, plan
        
    async def generate_plan_for_goal(self, goal_id):
        """Generate a plan for a specific goal."""
        goal = self.goal_manager.get_goal(goal_id)
        if not goal:
            return None
            
        # Generate plan using LLM
        prompt = self._create_planning_prompt(goal)
        plan = await self._generate_plan_from_prompt(prompt)
        
        # Store plan
        self.plans[goal_id] = plan
        return plan
        
    def update_goal_from_plan_progress(self, goal_id):
        """Update goal status based on plan progress."""
        # Implementation details...
```

#### 2. Enhance Plan with Goal Tracking
- Extend Plan class to maintain references to associated goals
- Add functionality to update goal criteria as plan steps complete
- Implement plan revision when goals change

```python
class EnhancedPlan(Plan):
    """Plan with goal tracking capabilities."""
    
    def __init__(self, goal_id=None):
        super().__init__()
        self.goal_id = goal_id
        self.goal_criteria_map = {}  # step_id -> criterion_index
        
    def map_step_to_criterion(self, step_id, criterion_index):
        """Map a plan step to a specific goal criterion."""
        self.goal_criteria_map[step_id] = criterion_index
        
    def complete_step_with_goal_update(self, step_id, result, goal_manager):
        """Complete a step and update associated goal criterion if applicable."""
        super().complete_step(step_id, result)
        
        # Update goal criterion if mapped
        if self.goal_id and step_id in self.goal_criteria_map:
            criterion_index = self.goal_criteria_map[step_id]
            goal_manager.mark_criterion_met(
                self.goal_id, 
                criterion_index,
                evidence=result
            )
```

#### 3. Implement Plan Monitoring
- Create plan execution monitoring system
- Add automatic detection of plan failures
- Implement plan revision strategies

### Unified Memory Architecture

#### 1. Create MemoryManager
- Implement a centralized memory access system
- Add interfaces for different memory types
- Develop query routing between memory systems

```python
class MemoryManager:
    """Central manager for all memory systems."""
    
    def __init__(self):
        self.memories = {}  # name -> memory instance
        self.policies = {}  # memory type -> access policy
        
    def register_memory(self, name, memory_instance, memory_type=None):
        """Register a memory system with the manager."""
        self.memories[name] = memory_instance
        
    async def store(self, key, value, memory_names=None):
        """Store a value in selected or all memories."""
        targets = self._get_target_memories(memory_names)
        for name, memory in targets.items():
            await memory.store(key, value)
            
    async def retrieve(self, key, memory_names=None):
        """Retrieve a value from selected memories."""
        targets = self._get_target_memories(memory_names)
        results = {}
        for name, memory in targets.items():
            results[name] = await memory.retrieve(key)
        return results
        
    async def search(self, query, memory_names=None, **kwargs):
        """Search across multiple memory systems."""
        targets = self._get_target_memories(memory_names)
        results = {}
        for name, memory in targets.items():
            results[name] = await memory.search(query, **kwargs)
        return results
        
    def _get_target_memories(self, memory_names):
        """Get target memories based on names or defaults."""
        if not memory_names:
            return self.memories
        return {name: mem for name, mem in self.memories.items() if name in memory_names}
```

#### 2. Develop Memory Policies
- Create policy framework for memory access patterns
- Implement automatic memory selection based on query type
- Add memory prioritization mechanisms

```python
class MemoryPolicy:
    """Policy for memory access patterns."""
    
    def __init__(self, name, memory_types=None, priority=0):
        self.name = name
        self.memory_types = memory_types or []
        self.priority = priority
        
    def should_apply(self, query_type, content):
        """Determine if this policy should apply to this query."""
        return query_type in self.supported_query_types
        
    def get_memory_priority(self, memory_name, memory_type, query_type):
        """Get priority score for a memory system for this query."""
        if not self.should_apply(query_type, None):
            return 0
        if memory_type not in self.memory_types:
            return 0
        return self.priority
```

## Phase 2: Advanced Memory Systems

### Episodic Memory

#### 1. EpisodicMemory Implementation
- Create representation for episodes and events
- Implement temporal indexing
- Add narrative structure support

```python
class Episode(BaseModel):
    """Representation of an episode in episodic memory."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    events: List[Event] = Field(default_factory=list)
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class Event(BaseModel):
    """An event within an episode."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    episode_id: str
    description: str
    event_type: str
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any] = Field(default_factory=dict)
    
class EpisodicMemory(BaseMemory):
    """Memory implementation for storing and retrieving episodes."""
    
    def __init__(self, vector_store=None):
        self.episodes = {}  # id -> Episode
        self.events = {}  # id -> Event
        self.vector_store = vector_store  # For semantic search
        
    async def store_episode(self, episode):
        """Store an episode in memory."""
        self.episodes[episode.id] = episode
        
        # Store each event
        for event in episode.events:
            self.events[event.id] = event
            
        # Create vector embeddings if available
        if self.vector_store:
            content = f"{episode.title}: " + " ".join([e.description for e in episode.events])
            await self.vector_store.store(f"episode:{episode.id}", content)
            
    async def retrieve_episode(self, episode_id):
        """Retrieve an episode by ID."""
        return self.episodes.get(episode_id)
        
    async def search_episodes(self, query, limit=10):
        """Search episodes semantically."""
        if not self.vector_store:
            return []
            
        results = await self.vector_store.search(query, limit=limit)
        episode_ids = [r.split(":", 1)[1] for r in results if r.startswith("episode:")]
        return [self.episodes[eid] for eid in episode_ids if eid in self.episodes]
```

#### 2. Experience Replay
- Implement capabilities to replay and learn from past episodes
- Add reflection on episodic memory for better decision making
- Create summarization of episodic clusters

```python
class ExperienceReplay:
    """Mechanism for replaying and learning from past episodes."""
    
    def __init__(self, episodic_memory, llm_client=None):
        self.episodic_memory = episodic_memory
        self.llm_client = llm_client
        
    async def replay_episode(self, episode_id):
        """Replay an episode event by event."""
        episode = await self.episodic_memory.retrieve_episode(episode_id)
        if not episode:
            return None
            
        # Sort events by timestamp
        events = sorted(episode.events, key=lambda e: e.timestamp)
        return events
        
    async def learn_from_episodes(self, query, limit=5):
        """Extract learnings from relevant episodes."""
        episodes = await self.episodic_memory.search_episodes(query, limit=limit)
        
        if not episodes or not self.llm_client:
            return []
            
        # Format episodes for analysis
        episodes_text = []
        for ep in episodes:
            events = sorted(ep.events, key=lambda e: e.timestamp)
            events_text = "\n".join([f"- {e.description}" for e in events])
            episodes_text.append(f"## {ep.title}\n{events_text}")
            
        # Generate insights using LLM
        prompt = f"""Review these past experiences and extract key lessons learned relevant to: {query}
        
        Past Experiences:
        
        {"\n\n".join(episodes_text)}
        
        Based only on these experiences, what are the key lessons, patterns, or insights that would be helpful for handling similar situations?
        """
        
        response = await self.llm_client.generate(prompt)
        return response
```

### Working Memory

#### 1. WorkingMemory Implementation
- Create a limited capacity working memory
- Implement attention mechanisms
- Add information prioritization

```python
class MemoryItem(BaseModel):
    """An item in working memory."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    importance: float = 0.5  # 0-1 scale
    recency: float = Field(default_factory=time.time)
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class WorkingMemory(BaseMemory):
    """Limited capacity working memory with attention mechanisms."""
    
    def __init__(self, capacity=7):
        self.items = []  # List of MemoryItem
        self.capacity = capacity
        
    async def store(self, key, value, importance=0.5):
        """Store an item in working memory."""
        # Create new item
        item = MemoryItem(
            id=key,
            content=str(value),
            importance=importance,
            recency=time.time()
        )
        
        # Check if item already exists
        for i, existing in enumerate(self.items):
            if existing.id == key:
                # Update existing item
                self.items[i] = item
                return
                
        # Add new item
        self.items.append(item)
        
        # Enforce capacity limit
        self._enforce_capacity()
        
    def _enforce_capacity(self):
        """Enforce capacity limit by removing least important items."""
        if len(self.items) <= self.capacity:
            return
            
        # Calculate item scores (combination of importance and recency)
        now = time.time()
        max_age = 3600  # 1 hour
        
        for item in self.items:
            age = now - item.recency
            recency_score = max(0, 1 - (age / max_age))
            item.metadata["_score"] = (item.importance * 0.7) + (recency_score * 0.3)
            
        # Sort by score and keep only top items
        self.items.sort(key=lambda x: x.metadata.get("_score", 0), reverse=True)
        self.items = self.items[:self.capacity]
        
    async def get_all(self, sort_by="recency"):
        """Get all items in working memory."""
        if sort_by == "importance":
            return sorted(self.items, key=lambda x: x.importance, reverse=True)
        elif sort_by == "recency":
            return sorted(self.items, key=lambda x: x.recency, reverse=True)
        return self.items
        
    async def get_context(self, format="text"):
        """Get formatted context from working memory."""
        items = await self.get_all("importance")
        
        if format == "text":
            return "\n".join([f"- {item.content}" for item in items])
        elif format == "dict":
            return [item.model_dump() for item in items]
        return items
```

#### 2. Attention Mechanism
- Implement focus and attention over working memory
- Create context-based memory retrieval
- Add chunking capabilities for organizing information

## Phase 3: Agent Capabilities

### Reflective Goal-Oriented Agent

```python
class ReflectiveGoalOrientedAgent(ReflectiveAgentMixin, GoalConditionedAgentMixin, AgentBase):
    """An agent that combines reflection capabilities with goal-oriented behavior."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize memory systems
        self.working_memory = WorkingMemory()
        self.episodic_memory = EpisodicMemory()
        self.memory_manager = MemoryManager()
        
        # Register memories
        self.memory_manager.register_memory("working", self.working_memory, "working")
        self.memory_manager.register_memory("episodic", self.episodic_memory, "episodic")
        
        # Initialize goal-plan manager
        self.goal_plan_manager = GoalPlanManager(llm_client=self.llm_client)
        
        # Current episode tracking
        self.current_episode = None
        
    async def set_goal_and_plan(self, goal_description, success_criteria=None):
        """Set a goal and generate a plan for it."""
        goal, plan = await self.goal_plan_manager.create_goal_with_plan(
            goal_description, 
            success_criteria
        )
        
        self.active_goal_id = goal.id
        
        # Store in working memory
        await self.working_memory.store(
            f"goal:{goal.id}", 
            goal.description,
            importance=0.9
        )
        
        await self.working_memory.store(
            f"plan:{goal.id}", 
            plan.to_string(),
            importance=0.8
        )
        
        # Start a new episode
        self._start_new_episode(f"Working on: {goal.description}")
        
        return goal, plan
        
    async def execute_next_step(self):
        """Execute the next step in the current plan."""
        if not self.active_goal_id:
            return None
            
        plan = self.goal_plan_manager.plans.get(self.active_goal_id)
        if not plan:
            return None
            
        # Get the current step
        step = plan.get_current_step()
        if not step:
            return None
            
        # Log event in episodic memory
        self._add_event_to_episode(f"Executing step: {step.description}")
        
        # Execute step with reflection
        thought = f"I need to complete this step: {step.description}"
        reflected_thought = await self.reflect(thought, {"task": step.description})
        
        # Use reflected thought to guide execution
        context = await self.working_memory.get_context()
        prompt = f"""
        Task: {step.description}
        
        Context:
        {context}
        
        My approach:
        {reflected_thought}
        
        Complete this step and provide the results.
        """
        
        # Execute using LLM
        response = await self.llm_client.generate(prompt)
        
        # Complete step and update goal
        plan.complete_step_with_goal_update(
            step.id, 
            response, 
            self.goal_manager
        )
        
        # Log result in episodic memory
        self._add_event_to_episode(f"Completed step with result: {response[:100]}...")
        
        # Store result in working memory
        await self.working_memory.store(
            f"result:step:{step.id}", 
            response,
            importance=0.7
        )
        
        return response
        
    def _start_new_episode(self, title):
        """Start a new episode in episodic memory."""
        self.current_episode = Episode(title=title)
        
    def _add_event_to_episode(self, description, event_type="agent_action"):
        """Add an event to the current episode."""
        if not self.current_episode:
            return
            
        event = Event(
            episode_id=self.current_episode.id,
            description=description,
            event_type=event_type
        )
        
        self.current_episode.events.append(event)
```

## Implementation Roadmap

### Month 1: Core Architecture
- Implement GoalPlanManager
- Develop enhanced Plan with goal tracking
- Create MemoryManager
- Build centralized memory policies

### Month 2: Advanced Memory Systems
- Implement EpisodicMemory
- Develop WorkingMemory
- Create experience replay mechanisms
- Build attention focus capabilities

### Month 3: Agent Integration & Testing
- Implement ReflectiveGoalOrientedAgent
- Create end-to-end workflows
- Build system tests
- Develop benchmarking framework