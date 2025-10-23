"""
n8n Adapter

Adapter for integrating n8n workflows as agents.
Allows calling n8n workflows via webhooks and treating them as agents.
"""

import logging
from typing import Dict, Any, AsyncIterator, Optional
from datetime import datetime
import time
import httpx

from app.agents.base import (
    BaseAgent,
    AgentResponse,
    AgentContext,
    AgentCapabilities,
    AgentType,
    AgentStatus,
    AgentStreamChunk,
    HealthStatus,
    Citation
)

logger = logging.getLogger(__name__)


class N8NAdapter(BaseAgent):
    """
    Adapter for n8n workflow integration
    
    This adapter allows you to use n8n workflows as agents by calling them
    via webhooks. The workflow should accept a query and context, and return
    a response in the expected format.
    
    Example:
        ```python
        adapter = N8NAdapter({
            "agent_id": "n8n-workflow",
            "name": "n8n Custom Workflow",
            "type": "n8n",
            "webhook_url": "https://your-n8n.com/webhook/abc123",
            "api_key": "your-api-key"
        })
        
        response = await adapter.execute("Process this data", context)
        ```
    
    n8n Workflow Requirements:
        - Accept POST request with JSON body containing:
          - query: string
          - context: object with tenant_id, user_id, session_id
        - Return JSON response with:
          - answer: string (required)
          - citations: array (optional)
          - metadata: object (optional)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize n8n adapter
        
        Args:
            config: Configuration dictionary
        """
        # Set type before calling super().__init__
        if "type" not in config:
            config["type"] = "n8n"
        
        super().__init__(config)
        
        # n8n-specific configuration
        self.webhook_url = config.get("webhook_url")
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout", 120)
        self.retry_count = config.get("retry_count", 3)
        
        # Validate configuration
        if not self.webhook_url:
            raise ValueError("webhook_url is required for n8n adapter")
        
        logger.info(f"Initialized n8n adapter: {self.agent_id}")
    
    async def execute(
        self,
        query: str,
        context: AgentContext
    ) -> AgentResponse:
        """
        Execute n8n workflow with a query
        
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
                f"Executing n8n workflow for query: '{query}' "
                f"(tenant: {context.tenant_id})"
            )
            
            # Prepare request payload
            payload = {
                "query": query,
                "context": {
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                    "session_id": context.session_id,
                    "conversation_history": context.conversation_history,
                    "metadata": context.metadata
                }
            }
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Call n8n webhook with retry logic
            response_data = await self._call_webhook_with_retry(
                payload,
                headers
            )
            
            # Parse response
            answer = response_data.get("answer", "No response from workflow")
            citations_data = response_data.get("citations", [])
            metadata = response_data.get("metadata", {})
            
            # Convert citations
            citations = []
            for citation_data in citations_data:
                citations.append(Citation(
                    source=citation_data.get("source", "n8n workflow"),
                    content=citation_data.get("content", ""),
                    relevance_score=citation_data.get("relevance_score"),
                    metadata=citation_data.get("metadata", {})
                ))
            
            execution_time = time.time() - start_time
            
            # Create response
            return AgentResponse(
                answer=answer,
                citations=citations,
                thoughts=[],
                agent_id=self.agent_id,
                agent_type=AgentType.N8N,
                status=AgentStatus.COMPLETED,
                execution_time=execution_time,
                tools_used=metadata.get("tools_used", []),
                metadata={
                    **metadata,
                    "webhook_url": self.webhook_url,
                    "workflow_execution_id": response_data.get("execution_id")
                },
                started_at=started_at,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in n8n execution: {e}", exc_info=True)
            
            return AgentResponse(
                answer=f"I apologize, but the workflow encountered an error: {str(e)}",
                agent_id=self.agent_id,
                agent_type=AgentType.N8N,
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
        Execute n8n workflow with streaming
        
        Note: n8n doesn't natively support streaming, so this implementation
        calls the workflow and yields the complete response as chunks.
        
        Args:
            query: User's question
            context: Execution context
            
        Yields:
            AgentStreamChunk objects with incremental updates
        """
        try:
            logger.info(
                f"Executing n8n workflow with streaming for: '{query}'"
            )
            
            # Yield processing status
            yield AgentStreamChunk(
                chunk_type="status",
                content="Calling n8n workflow...",
                metadata={"status": "processing"}
            )
            
            # Execute workflow (non-streaming)
            response = await self.execute(query, context)
            
            # Yield the answer as text chunks
            # Split into sentences for better streaming effect
            sentences = response.answer.split('. ')
            
            for sentence in sentences:
                if sentence.strip():
                    yield AgentStreamChunk(
                        chunk_type="text",
                        content=sentence + '. ',
                        metadata={}
                    )
            
            # Yield citations if any
            if response.citations:
                yield AgentStreamChunk(
                    chunk_type="citations",
                    content="",
                    metadata={"citations": [c.dict() for c in response.citations]}
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
        Get n8n workflow capabilities
        
        Note: Capabilities depend on the specific workflow implementation.
        These are generic defaults.
        
        Returns:
            AgentCapabilities describing what this workflow can do
        """
        return AgentCapabilities(
            supports_streaming=False,  # n8n doesn't natively support streaming
            supports_tools=True,  # n8n can integrate with many tools
            supports_memory=False,  # Depends on workflow implementation
            supports_multimodal=False,  # Depends on workflow
            supports_rag=False,  # Depends on workflow
            supports_code_execution=True,  # n8n can execute code
            max_context_length=8000,  # Depends on workflow
            supported_languages=["en"],  # Depends on workflow
            supported_file_types=[]  # Depends on workflow
        )
    
    async def health_check(self) -> HealthStatus:
        """
        Check if n8n workflow is healthy
        
        Returns:
            HealthStatus with health information
        """
        try:
            # Try a simple ping to the webhook
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Some n8n webhooks support GET for health checks
                try:
                    response = await client.get(self.webhook_url)
                    
                    if response.status_code in [200, 405]:  # 405 = Method Not Allowed (POST only)
                        return HealthStatus(
                            healthy=True,
                            message="n8n workflow is reachable",
                            details={
                                "agent_id": self.agent_id,
                                "webhook_url": self.webhook_url,
                                "status_code": response.status_code
                            }
                        )
                except httpx.HTTPStatusError:
                    # If GET fails, try a minimal POST
                    pass
                
                # Try minimal POST request
                test_payload = {"query": "health_check", "context": {}}
                headers = {"Content-Type": "application/json"}
                
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.post(
                    self.webhook_url,
                    json=test_payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return HealthStatus(
                        healthy=True,
                        message="n8n workflow is healthy",
                        details={
                            "agent_id": self.agent_id,
                            "webhook_url": self.webhook_url
                        }
                    )
                else:
                    return HealthStatus(
                        healthy=False,
                        message=f"n8n returned status {response.status_code}"
                    )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                healthy=False,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _call_webhook_with_retry(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Call n8n webhook with retry logic
        
        Args:
            payload: Request payload
            headers: HTTP headers
            
        Returns:
            Response data from n8n
            
        Raises:
            Exception: If all retries fail
        """
        import asyncio
        
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                logger.debug(
                    f"n8n request attempt {attempt + 1}/{self.retry_count}"
                )
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        headers=headers
                    )
                    
                    response.raise_for_status()
                    
                    return response.json()
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    f"n8n request attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self.retry_count - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        raise last_error

