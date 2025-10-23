"""
LangGraph Adapter

Wraps the existing LangGraph implementation to conform to the BaseAgent interface.
This allows the existing LangGraph agent to work with the new plugin architecture.
"""

import logging
from typing import Dict, Any, AsyncIterator
from datetime import datetime
import time

from app.agents.base import (
    BaseAgent,
    AgentResponse,
    AgentContext,
    AgentCapabilities,
    AgentType,
    AgentStatus,
    AgentStreamChunk,
    HealthStatus,
    Citation,
    AgentThought
)
from app.agents.graph import run_agent, run_agent_streaming
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class LangGraphAdapter(BaseAgent):
    """
    Adapter for the existing LangGraph agent implementation
    
    This adapter wraps the existing LangGraph workflow to make it compatible
    with the new plugin-based architecture. It translates between the new
    BaseAgent interface and the existing LangGraph implementation.
    
    Example:
        ```python
        adapter = LangGraphAdapter({
            "agent_id": "langgraph-default",
            "name": "LangGraph RAG Agent",
            "type": "langgraph"
        })
        
        context = AgentContext(
            tenant_id="tenant1",
            user_id="user1",
            session_id="session1"
        )
        
        response = await adapter.execute("What is AI?", context)
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LangGraph adapter
        
        Args:
            config: Configuration dictionary
        """
        # Set type before calling super().__init__
        if "type" not in config:
            config["type"] = "langgraph"
        
        super().__init__(config)
        
        # LangGraph-specific configuration
        self.model = config.get("model", "gpt-4-turbo-preview")
        self.temperature = config.get("temperature", 0.7)
        self.max_iterations = config.get("max_iterations", 10)
        
        logger.info(f"Initialized LangGraph adapter: {self.agent_id}")
    
    async def execute(
        self,
        query: str,
        context: AgentContext
    ) -> AgentResponse:
        """
        Execute LangGraph agent with a query
        
        Args:
            query: User's question
            context: Execution context
            
        Returns:
            AgentResponse with answer and metadata
        """
        start_time = time.time()
        started_at = datetime.utcnow()
        
        try:
            logger.info(
                f"Executing LangGraph agent for query: '{query}' "
                f"(tenant: {context.tenant_id})"
            )
            
            # Call existing LangGraph implementation
            final_state = await run_agent(
                user_query=query,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                session_id=context.session_id
            )
            
            # Convert LangGraph state to AgentResponse
            response = self._convert_state_to_response(
                final_state,
                started_at,
                time.time() - start_time
            )
            
            logger.info(
                f"LangGraph execution completed in {response.execution_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in LangGraph execution: {e}", exc_info=True)
            
            # Return error response
            return AgentResponse(
                answer=f"I apologize, but I encountered an error: {str(e)}",
                agent_id=self.agent_id,
                agent_type=AgentType.LANGGRAPH,
                status=AgentStatus.FAILED,
                execution_time=time.time() - start_time,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow()
            )
    
    async def execute_streaming(
        self,
        query: str,
        context: AgentContext
    ) -> AsyncIterator[AgentStreamChunk]:
        """
        Execute LangGraph agent with streaming
        
        Args:
            query: User's question
            context: Execution context
            
        Yields:
            AgentStreamChunk objects with incremental updates
        """
        try:
            logger.info(
                f"Executing LangGraph agent with streaming for: '{query}'"
            )
            
            # Stream from existing LangGraph implementation
            async for state in run_agent_streaming(
                user_query=query,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                session_id=context.session_id
            ):
                # Convert state updates to stream chunks
                chunk = self._convert_state_to_chunk(state)
                if chunk:
                    yield chunk
            
            # Send completion chunk
            yield AgentStreamChunk(
                chunk_type="completion",
                content="",
                metadata={"status": "completed"}
            )
            
        except Exception as e:
            logger.error(f"Error in streaming execution: {e}", exc_info=True)
            
            # Send error chunk
            yield AgentStreamChunk(
                chunk_type="error",
                content=str(e),
                metadata={"status": "failed"}
            )
    
    def get_capabilities(self) -> AgentCapabilities:
        """
        Get LangGraph agent capabilities
        
        Returns:
            AgentCapabilities describing what this agent can do
        """
        return AgentCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_memory=True,
            supports_multimodal=False,
            supports_rag=True,
            supports_code_execution=False,
            max_context_length=8000,
            supported_languages=["en"],
            supported_file_types=["pdf", "docx", "txt", "md"]
        )
    
    async def health_check(self) -> HealthStatus:
        """
        Check if LangGraph agent is healthy
        
        Returns:
            HealthStatus with health information
        """
        try:
            # Check if we can import required modules
            from app.agents.graph import agent_graph
            
            # Check if graph is initialized
            if agent_graph is None:
                return HealthStatus(
                    healthy=False,
                    message="LangGraph agent graph not initialized"
                )
            
            # All checks passed
            return HealthStatus(
                healthy=True,
                message="LangGraph agent is healthy",
                details={
                    "agent_id": self.agent_id,
                    "model": self.model,
                    "graph_initialized": True
                }
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def _convert_state_to_response(
        self,
        state: AgentState,
        started_at: datetime,
        execution_time: float
    ) -> AgentResponse:
        """
        Convert LangGraph state to AgentResponse
        
        Args:
            state: Final LangGraph state
            started_at: When execution started
            execution_time: Execution time in seconds
            
        Returns:
            AgentResponse
        """
        # Extract answer
        answer = state.get("final_response", "No response generated")
        
        # Convert citations
        citations = []
        for citation_data in state.get("citations", []):
            citations.append(Citation(
                source=citation_data.get("source", "unknown"),
                content=citation_data.get("content", ""),
                relevance_score=citation_data.get("relevance_score"),
                metadata=citation_data.get("metadata", {})
            ))
        
        # Convert thoughts
        thoughts = []
        for thought_text in state.get("agent_thoughts", []):
            thoughts.append(AgentThought(
                step="reasoning",
                thought=thought_text
            ))
        
        # Determine status
        status = AgentStatus.COMPLETED
        if state.get("error"):
            status = AgentStatus.FAILED
        elif state.get("current_step") == "timeout":
            status = AgentStatus.TIMEOUT
        
        # Extract tools used
        tools_used = state.get("tools_used", [])
        
        # Create response
        return AgentResponse(
            answer=answer,
            citations=citations,
            thoughts=thoughts,
            agent_id=self.agent_id,
            agent_type=AgentType.LANGGRAPH,
            status=status,
            execution_time=execution_time,
            visualization_data=state.get("visualization_data"),
            tools_used=tools_used,
            metadata={
                "query_intent": state.get("query_intent"),
                "documents_retrieved": len(state.get("retrieved_documents", [])),
                "reranked": state.get("reranked_documents") is not None,
                "retry_count": state.get("retry_count", 0),
                "current_step": state.get("current_step")
            },
            error=state.get("error"),
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
    
    def _convert_state_to_chunk(
        self,
        state: Dict[str, Any]
    ) -> AgentStreamChunk:
        """
        Convert LangGraph state update to stream chunk
        
        Args:
            state: State update from LangGraph
            
        Returns:
            AgentStreamChunk or None if no meaningful update
        """
        # Determine chunk type and content based on state
        current_step = state.get("current_step", "")
        
        if current_step == "analyze":
            return AgentStreamChunk(
                chunk_type="thought",
                content="Analyzing query intent...",
                metadata={"step": current_step}
            )
        
        elif current_step == "retrieve":
            return AgentStreamChunk(
                chunk_type="thought",
                content="Retrieving relevant documents...",
                metadata={"step": current_step}
            )
        
        elif current_step == "rerank":
            return AgentStreamChunk(
                chunk_type="thought",
                content="Reranking documents for relevance...",
                metadata={"step": current_step}
            )
        
        elif current_step == "respond":
            # Check for partial response
            draft = state.get("draft_response")
            final = state.get("final_response")
            
            if draft or final:
                return AgentStreamChunk(
                    chunk_type="text",
                    content=final or draft or "",
                    metadata={"step": current_step}
                )
        
        elif state.get("error"):
            return AgentStreamChunk(
                chunk_type="error",
                content=state.get("error", "Unknown error"),
                metadata={"step": current_step}
            )
        
        # Return generic update for other steps
        if current_step:
            return AgentStreamChunk(
                chunk_type="status",
                content=f"Processing: {current_step}",
                metadata={"step": current_step}
            )
        
        return None
