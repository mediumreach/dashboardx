"""
Base Agent Interface

Defines the abstract base class and core models that all agent implementations must follow.
This enables a plugin-based architecture where any agent framework can be integrated.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


# ==================== Enums ====================

class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentType(str, Enum):
    """Types of agents"""
    LANGGRAPH = "langgraph"
    LANGCHAIN = "langchain"
    N8N = "n8n"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    LLAMAINDEX = "llamaindex"
    CUSTOM = "custom"


# ==================== Models ====================

class AgentCapabilities(BaseModel):
    """
    Defines what an agent can do
    
    This helps the orchestrator route requests to appropriate agents
    and inform users about agent features.
    """
    supports_streaming: bool = Field(
        default=False,
        description="Can the agent stream responses?"
    )
    supports_tools: bool = Field(
        default=False,
        description="Can the agent use external tools?"
    )
    supports_memory: bool = Field(
        default=False,
        description="Does the agent maintain conversation memory?"
    )
    supports_multimodal: bool = Field(
        default=False,
        description="Can the agent handle images, audio, etc.?"
    )
    supports_rag: bool = Field(
        default=False,
        description="Does the agent support RAG?"
    )
    supports_code_execution: bool = Field(
        default=False,
        description="Can the agent execute code?"
    )
    max_context_length: int = Field(
        default=4096,
        description="Maximum context length in tokens"
    )
    supported_languages: List[str] = Field(
        default=["en"],
        description="Supported natural languages"
    )
    supported_file_types: List[str] = Field(
        default=[],
        description="Supported file types for processing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "supports_streaming": True,
                "supports_tools": True,
                "supports_memory": True,
                "supports_multimodal": False,
                "supports_rag": True,
                "supports_code_execution": False,
                "max_context_length": 8000,
                "supported_languages": ["en", "es", "fr"],
                "supported_file_types": ["pdf", "docx", "txt"]
            }
        }


class AgentContext(BaseModel):
    """
    Context passed to agent for execution
    
    Contains all necessary information for the agent to process a request.
    """
    tenant_id: str = Field(..., description="Tenant ID for multi-tenancy")
    user_id: str = Field(..., description="User ID making the request")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    
    # Optional context
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Previous messages in conversation"
    )
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences and settings"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # RAG context
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific documents to search"
    )
    
    # Execution constraints
    max_execution_time: Optional[int] = Field(
        default=120,
        description="Maximum execution time in seconds"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens in response"
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Temperature for LLM generation"
    )


class Citation(BaseModel):
    """Source citation for agent response"""
    source: str = Field(..., description="Source identifier")
    content: str = Field(..., description="Cited content")
    relevance_score: Optional[float] = Field(
        default=None,
        description="Relevance score (0-1)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class AgentThought(BaseModel):
    """Agent's reasoning step"""
    step: str = Field(..., description="Step name")
    thought: str = Field(..., description="Agent's thought process")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this thought occurred"
    )


class AgentResponse(BaseModel):
    """
    Standardized response from any agent
    
    All agents must return this format for consistency.
    """
    # Core response
    answer: str = Field(..., description="Agent's answer to the query")
    
    # Supporting information
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source citations"
    )
    thoughts: List[AgentThought] = Field(
        default_factory=list,
        description="Agent's reasoning steps"
    )
    
    # Metadata
    agent_id: str = Field(..., description="ID of agent that generated response")
    agent_type: AgentType = Field(..., description="Type of agent")
    status: AgentStatus = Field(
        default=AgentStatus.COMPLETED,
        description="Execution status"
    )
    
    # Performance metrics
    execution_time: float = Field(..., description="Execution time in seconds")
    tokens_used: Optional[int] = Field(
        default=None,
        description="Total tokens used"
    )
    
    # Additional data
    visualization_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data for visualizations"
    )
    tools_used: List[str] = Field(
        default_factory=list,
        description="Tools used during execution"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # Error information
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
    
    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When execution started"
    )
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When execution completed"
    )
    
    @validator('execution_time', pre=True, always=True)
    def calculate_execution_time(cls, v, values):
        """Calculate execution time if not provided"""
        if v is None and 'started_at' in values and 'completed_at' in values:
            delta = values['completed_at'] - values['started_at']
            return delta.total_seconds()
        return v


class AgentStreamChunk(BaseModel):
    """
    Chunk of streamed response
    
    Used for streaming responses from agents.
    """
    chunk_type: str = Field(..., description="Type of chunk (text, thought, citation, etc.)")
    content: str = Field(..., description="Chunk content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When chunk was generated"
    )


class HealthStatus(BaseModel):
    """Agent health check status"""
    healthy: bool = Field(..., description="Is agent healthy?")
    message: Optional[str] = Field(
        default=None,
        description="Health status message"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health details"
    )
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When health was checked"
    )


# ==================== Base Agent Class ====================

class BaseAgent(ABC):
    """
    Abstract base class for all agent implementations
    
    All agent adapters (LangGraph, LangChain, n8n, etc.) must inherit from this class
    and implement the required methods.
    
    Example:
        ```python
        class MyCustomAgent(BaseAgent):
            def __init__(self, config: Dict[str, Any]):
                super().__init__(config)
                # Initialize your agent
            
            async def execute(self, query: str, context: AgentContext) -> AgentResponse:
                # Implement execution logic
                return AgentResponse(...)
            
            def get_capabilities(self) -> AgentCapabilities:
                return AgentCapabilities(...)
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent with configuration
        
        Args:
            config: Agent configuration dictionary
        """
        self.config = config
        self.agent_id = config.get("agent_id", "unknown")
        self.name = config.get("name", self.__class__.__name__)
        self.agent_type = AgentType(config.get("type", "custom"))
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 999)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """
        Validate agent configuration
        
        Override this method to add custom validation logic.
        Raise ValueError if configuration is invalid.
        """
        if not self.agent_id:
            raise ValueError("agent_id is required in configuration")
        
        if not self.name:
            raise ValueError("name is required in configuration")
    
    # ==================== Required Methods ====================
    
    @abstractmethod
    async def execute(
        self,
        query: str,
        context: AgentContext
    ) -> AgentResponse:
        """
        Execute agent with a query
        
        This is the main method that processes user queries and returns responses.
        
        Args:
            query: User's question or command
            context: Execution context with tenant, user, session info
            
        Returns:
            AgentResponse with answer, citations, and metadata
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    @abstractmethod
    async def execute_streaming(
        self,
        query: str,
        context: AgentContext
    ) -> AsyncIterator[AgentStreamChunk]:
        """
        Execute agent with streaming response
        
        Yields chunks of the response as they're generated.
        
        Args:
            query: User's question or command
            context: Execution context
            
        Yields:
            AgentStreamChunk objects with incremental response data
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """
        Get agent capabilities
        
        Returns:
            AgentCapabilities describing what this agent can do
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check if agent is healthy and ready to process requests
        
        Returns:
            HealthStatus with health information
        """
        pass
    
    # ==================== Optional Methods ====================
    
    async def initialize(self) -> None:
        """
        Initialize agent resources
        
        Called once when agent is first created.
        Override to set up connections, load models, etc.
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up agent resources
        
        Called when agent is being destroyed.
        Override to close connections, release resources, etc.
        """
        pass
    
    def validate_query(self, query: str) -> bool:
        """
        Validate if query is appropriate for this agent
        
        Args:
            query: User query to validate
            
        Returns:
            True if query is valid, False otherwise
        """
        if not query or not query.strip():
            return False
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get agent metadata
        
        Returns:
            Dictionary with agent information
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "capabilities": self.get_capabilities().dict()
        }
    
    def __repr__(self) -> str:
        """String representation of agent"""
        return f"{self.__class__.__name__}(id={self.agent_id}, name={self.name})"


# ==================== Utility Functions ====================

def create_error_response(
    agent_id: str,
    agent_type: AgentType,
    error: str,
    query: str = ""
) -> AgentResponse:
    """
    Create a standardized error response
    
    Args:
        agent_id: ID of the agent
        agent_type: Type of agent
        error: Error message
        query: Original query (optional)
        
    Returns:
        AgentResponse with error information
    """
    return AgentResponse(
        answer=f"I apologize, but I encountered an error: {error}",
        agent_id=agent_id,
        agent_type=agent_type,
        status=AgentStatus.FAILED,
        execution_time=0.0,
        error=error,
        metadata={"query": query}
    )


def merge_agent_responses(
    responses: List[AgentResponse],
    strategy: str = "best"
) -> AgentResponse:
    """
    Merge multiple agent responses into one
    
    Useful for multi-agent scenarios where multiple agents process the same query.
    
    Args:
        responses: List of agent responses to merge
        strategy: Merge strategy ("best", "consensus", "concatenate")
        
    Returns:
        Merged AgentResponse
    """
    if not responses:
        raise ValueError("No responses to merge")
    
    if len(responses) == 1:
        return responses[0]
    
    if strategy == "best":
        # Return response with highest confidence or shortest execution time
        return min(responses, key=lambda r: r.execution_time)
    
    elif strategy == "consensus":
        # Combine answers (simplified - in production, use more sophisticated logic)
        combined_answer = "\n\n".join([r.answer for r in responses])
        combined_citations = []
        for r in responses:
            combined_citations.extend(r.citations)
        
        return AgentResponse(
            answer=combined_answer,
            citations=combined_citations,
            agent_id="merged",
            agent_type=AgentType.CUSTOM,
            execution_time=sum(r.execution_time for r in responses),
            metadata={"merged_from": [r.agent_id for r in responses]}
        )
    
    elif strategy == "concatenate":
        # Concatenate all answers
        combined_answer = "\n\n---\n\n".join([
            f"**{r.agent_id}**: {r.answer}" for r in responses
        ])
        
        return AgentResponse(
            answer=combined_answer,
            agent_id="merged",
            agent_type=AgentType.CUSTOM,
            execution_time=max(r.execution_time for r in responses),
            metadata={"strategy": "concatenate"}
        )
    
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")
