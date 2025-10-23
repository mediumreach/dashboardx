"""
LangChain Adapter

Adapter for pure LangChain agents (without LangGraph).
Supports LangChain's agent executors and tools.
"""

import logging
from typing import Dict, Any, AsyncIterator, List, Optional
from datetime import datetime
import time

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.schema import HumanMessage, AIMessage

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

logger = logging.getLogger(__name__)


class LangChainAdapter(BaseAgent):
    """
    Adapter for LangChain agents
    
    This adapter provides a pure LangChain implementation that can be used
    as an alternative to LangGraph. It supports LangChain's agent executors,
    tools, and memory.
    
    Example:
        ```python
        adapter = LangChainAdapter({
            "agent_id": "langchain-simple",
            "name": "LangChain Agent",
            "type": "langchain",
            "model": "gpt-3.5-turbo",
            "tools": ["search", "calculator"]
        })
        
        response = await adapter.execute("What is 2+2?", context)
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LangChain adapter
        
        Args:
            config: Configuration dictionary
        """
        # Set type before calling super().__init__
        if "type" not in config:
            config["type"] = "langchain"
        
        super().__init__(config)
        
        # LangChain-specific configuration
        self.model_name = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.tool_names = config.get("tools", [])
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Initialize tools
        self.tools = self._load_tools(self.tool_names)
        
        # Create agent
        self.agent_executor = self._create_agent()
        
        logger.info(f"Initialized LangChain adapter: {self.agent_id}")
    
    def _load_tools(self, tool_names: List[str]) -> List[Tool]:
        """
        Load tools by name
        
        Args:
            tool_names: List of tool names to load
            
        Returns:
            List of Tool objects
        """
        tools = []
        
        for tool_name in tool_names:
            if tool_name == "search":
                # Placeholder for search tool
                tools.append(Tool(
                    name="search",
                    description="Search for information on the internet",
                    func=lambda q: f"Search results for: {q}"
                ))
            
            elif tool_name == "calculator":
                # Placeholder for calculator tool
                tools.append(Tool(
                    name="calculator",
                    description="Perform mathematical calculations",
                    func=lambda expr: str(eval(expr))
                ))
            
            # Add more tools as needed
        
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create LangChain agent executor
        
        Returns:
            AgentExecutor instance
        """
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant. Use the available tools to answer questions accurately."),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        if self.tools:
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                return_intermediate_steps=True,
                max_iterations=10
            )
        else:
            # No tools, create simple executor
            agent_executor = None
        
        return agent_executor
    
    async def execute(
        self,
        query: str,
        context: AgentContext
    ) -> AgentResponse:
        """
        Execute LangChain agent with a query
        
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
                f"Executing LangChain agent for query: '{query}' "
                f"(tenant: {context.tenant_id})"
            )
            
            # Prepare chat history
            chat_history = self._prepare_chat_history(
                context.conversation_history
            )
            
            # Execute agent
            if self.agent_executor:
                result = await self.agent_executor.ainvoke({
                    "input": query,
                    "chat_history": chat_history
                })
                
                answer = result.get("output", "No response generated")
                intermediate_steps = result.get("intermediate_steps", [])
                
                # Extract thoughts from intermediate steps
                thoughts = self._extract_thoughts(intermediate_steps)
                tools_used = self._extract_tools_used(intermediate_steps)
            else:
                # No agent executor, use LLM directly
                messages = chat_history + [HumanMessage(content=query)]
                response = await self.llm.ainvoke(messages)
                answer = response.content
                thoughts = []
                tools_used = []
            
            execution_time = time.time() - start_time
            
            # Create response
            return AgentResponse(
                answer=answer,
                citations=[],  # LangChain doesn't provide citations by default
                thoughts=thoughts,
                agent_id=self.agent_id,
                agent_type=AgentType.LANGCHAIN,
                status=AgentStatus.COMPLETED,
                execution_time=execution_time,
                tools_used=tools_used,
                metadata={
                    "model": self.model_name,
                    "temperature": self.temperature
                },
                started_at=started_at,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in LangChain execution: {e}", exc_info=True)
            
            return AgentResponse(
                answer=f"I apologize, but I encountered an error: {str(e)}",
                agent_id=self.agent_id,
                agent_type=AgentType.LANGCHAIN,
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
        Execute LangChain agent with streaming
        
        Args:
            query: User's question
            context: Execution context
            
        Yields:
            AgentStreamChunk objects with incremental updates
        """
        try:
            logger.info(
                f"Executing LangChain agent with streaming for: '{query}'"
            )
            
            # Prepare chat history
            chat_history = self._prepare_chat_history(
                context.conversation_history
            )
            
            # Stream from LLM
            messages = chat_history + [HumanMessage(content=query)]
            
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield AgentStreamChunk(
                        chunk_type="text",
                        content=chunk.content,
                        metadata={}
                    )
            
            # Send completion chunk
            yield AgentStreamChunk(
                chunk_type="completion",
                content="",
                metadata={"status": "completed"}
            )
            
        except Exception as e:
            logger.error(f"Error in streaming execution: {e}", exc_info=True)
            
            yield AgentStreamChunk(
                chunk_type="error",
                content=str(e),
                metadata={"status": "failed"}
            )
    
    def get_capabilities(self) -> AgentCapabilities:
        """
        Get LangChain agent capabilities
        
        Returns:
            AgentCapabilities describing what this agent can do
        """
        return AgentCapabilities(
            supports_streaming=True,
            supports_tools=len(self.tools) > 0,
            supports_memory=True,
            supports_multimodal=False,
            supports_rag=False,  # Basic LangChain agent doesn't have RAG
            supports_code_execution=False,
            max_context_length=4096,
            supported_languages=["en"],
            supported_file_types=[]
        )
    
    async def health_check(self) -> HealthStatus:
        """
        Check if LangChain agent is healthy
        
        Returns:
            HealthStatus with health information
        """
        try:
            # Try a simple LLM call
            test_message = [HumanMessage(content="Hello")]
            response = await self.llm.ainvoke(test_message)
            
            if response and response.content:
                return HealthStatus(
                    healthy=True,
                    message="LangChain agent is healthy",
                    details={
                        "agent_id": self.agent_id,
                        "model": self.model_name,
                        "tools_count": len(self.tools)
                    }
                )
            else:
                return HealthStatus(
                    healthy=False,
                    message="LLM returned empty response"
                )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def _prepare_chat_history(
        self,
        conversation_history: List[Dict[str, Any]]
    ) -> List:
        """
        Convert conversation history to LangChain message format
        
        Args:
            conversation_history: List of message dictionaries
            
        Returns:
            List of LangChain message objects
        """
        messages = []
        
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        
        return messages
    
    def _extract_thoughts(
        self,
        intermediate_steps: List[tuple]
    ) -> List[AgentThought]:
        """
        Extract agent thoughts from intermediate steps
        
        Args:
            intermediate_steps: List of (action, observation) tuples
            
        Returns:
            List of AgentThought objects
        """
        thoughts = []
        
        for i, (action, observation) in enumerate(intermediate_steps):
            thoughts.append(AgentThought(
                step=f"step_{i+1}",
                thought=f"Tool: {action.tool}, Input: {action.tool_input}, Result: {observation}"
            ))
        
        return thoughts
    
    def _extract_tools_used(
        self,
        intermediate_steps: List[tuple]
    ) -> List[str]:
        """
        Extract list of tools used
        
        Args:
            intermediate_steps: List of (action, observation) tuples
            
        Returns:
            List of tool names
        """
        tools_used = []
        
        for action, _ in intermediate_steps:
            if action.tool not in tools_used:
                tools_used.append(action.tool)
        
        return tools_used
