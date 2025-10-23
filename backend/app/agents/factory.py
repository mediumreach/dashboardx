"""
Agent Factory

Creates and manages agent instances based on configuration.
Handles dependency injection, validation, and lifecycle management.
"""

import logging
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from app.agents.base import BaseAgent, AgentContext, HealthStatus
from app.agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating agent instances
    
    Handles:
    - Agent instantiation from configuration
    - Configuration validation
    - Health checks
    - Connection pooling
    - Error handling
    
    Example:
        ```python
        factory = AgentFactory()
        
        # Create agent from config
        agent = await factory.create_agent(
            agent_id="langgraph-default",
            config={"model": "gpt-4"}
        )
        
        # Use agent
        response = await agent.execute(query, context)
        
        # Clean up
        await factory.destroy_agent(agent)
        ```
    """
    
    def __init__(self):
        """Initialize the factory"""
        self._agent_pool: Dict[str, BaseAgent] = {}
        self._creation_times: Dict[str, datetime] = {}
        self._health_status: Dict[str, HealthStatus] = {}
    
    async def create_agent(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        initialize: bool = True
    ) -> BaseAgent:
        """
        Create an agent instance
        
        Args:
            agent_id: ID of agent to create
            config: Agent configuration (merged with defaults)
            validate: Whether to validate configuration
            initialize: Whether to call agent.initialize()
            
        Returns:
            Initialized agent instance
            
        Raises:
            ValueError: If agent not found or configuration invalid
            RuntimeError: If agent fails health check
        """
        try:
            # Get agent class from registry
            agent_class = AgentRegistry.get(agent_id)
            
            if not agent_class:
                raise ValueError(
                    f"Agent '{agent_id}' not found in registry. "
                    f"Available agents: {AgentRegistry.list_agents()}"
                )
            
            # Prepare configuration
            agent_config = self._prepare_config(agent_id, config)
            
            # Validate configuration if requested
            if validate:
                self._validate_config(agent_id, agent_config)
            
            # Create agent instance
            logger.info(f"Creating agent: {agent_id}")
            agent = agent_class(agent_config)
            
            # Initialize agent if requested
            if initialize:
                await agent.initialize()
            
            # Perform health check
            health = await agent.health_check()
            
            if not health.healthy:
                raise RuntimeError(
                    f"Agent {agent_id} failed health check: {health.message}"
                )
            
            # Store in pool
            pool_key = f"{agent_id}_{id(agent)}"
            self._agent_pool[pool_key] = agent
            self._creation_times[pool_key] = datetime.utcnow()
            self._health_status[pool_key] = health
            
            logger.info(f"Successfully created agent: {agent_id}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent {agent_id}: {e}", exc_info=True)
            raise
    
    async def get_or_create_agent(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAgent:
        """
        Get existing agent from pool or create new one
        
        Args:
            agent_id: ID of agent
            config: Configuration (only used if creating new agent)
            
        Returns:
            Agent instance
        """
        # Check if agent exists in pool
        for pool_key, agent in self._agent_pool.items():
            if pool_key.startswith(f"{agent_id}_"):
                # Verify agent is still healthy
                try:
                    health = await agent.health_check()
                    if health.healthy:
                        logger.debug(f"Reusing existing agent: {agent_id}")
                        return agent
                    else:
                        logger.warning(
                            f"Agent {agent_id} unhealthy, creating new instance"
                        )
                        await self.destroy_agent(agent)
                except Exception as e:
                    logger.error(f"Health check failed for {agent_id}: {e}")
                    await self.destroy_agent(agent)
        
        # Create new agent
        return await self.create_agent(agent_id, config)
    
    async def destroy_agent(self, agent: BaseAgent) -> None:
        """
        Destroy an agent instance and clean up resources
        
        Args:
            agent: Agent instance to destroy
        """
        try:
            # Find agent in pool
            pool_key = None
            for key, pooled_agent in self._agent_pool.items():
                if pooled_agent is agent:
                    pool_key = key
                    break
            
            if pool_key:
                # Clean up agent
                await agent.cleanup()
                
                # Remove from pool
                del self._agent_pool[pool_key]
                if pool_key in self._creation_times:
                    del self._creation_times[pool_key]
                if pool_key in self._health_status:
                    del self._health_status[pool_key]
                
                logger.info(f"Destroyed agent: {agent.agent_id}")
            
        except Exception as e:
            logger.error(f"Error destroying agent: {e}", exc_info=True)
    
    async def destroy_all_agents(self) -> None:
        """Destroy all agents in the pool"""
        agents = list(self._agent_pool.values())
        
        for agent in agents:
            await self.destroy_agent(agent)
        
        logger.info(f"Destroyed {len(agents)} agents")
    
    def _prepare_config(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Prepare agent configuration by merging with defaults
        
        Args:
            agent_id: Agent ID
            config: User-provided configuration
            
        Returns:
            Merged configuration
        """
        # Start with default config
        agent_config = {
            "agent_id": agent_id,
            "name": agent_id,
            "enabled": True,
            "priority": 999
        }
        
        # Merge with registry metadata
        metadata = AgentRegistry.get_metadata(agent_id)
        if metadata:
            agent_config.update(metadata)
        
        # Merge with user config
        if config:
            agent_config.update(config)
        
        return agent_config
    
    def _validate_config(
        self,
        agent_id: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Validate agent configuration
        
        Args:
            agent_id: Agent ID
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Check required fields
        required_fields = ["agent_id", "name"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(
                    f"Missing required field '{field}' in configuration for {agent_id}"
                )
        
        # Validate agent_id matches
        if config["agent_id"] != agent_id:
            raise ValueError(
                f"Configuration agent_id '{config['agent_id']}' "
                f"doesn't match requested agent_id '{agent_id}'"
            )
        
        logger.debug(f"Configuration validated for agent: {agent_id}")
    
    async def health_check_all(self) -> Dict[str, HealthStatus]:
        """
        Perform health check on all agents in pool
        
        Returns:
            Dictionary mapping pool_key to health status
        """
        results = {}
        
        for pool_key, agent in self._agent_pool.items():
            try:
                health = await agent.health_check()
                results[pool_key] = health
                self._health_status[pool_key] = health
            except Exception as e:
                logger.error(f"Health check failed for {pool_key}: {e}")
                results[pool_key] = HealthStatus(
                    healthy=False,
                    message=f"Health check error: {str(e)}"
                )
        
        return results
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the agent pool
        
        Returns:
            Dictionary with pool statistics
        """
        now = datetime.utcnow()
        
        agent_ages = {}
        for pool_key, creation_time in self._creation_times.items():
            age = (now - creation_time).total_seconds()
            agent_ages[pool_key] = age
        
        healthy_count = sum(
            1 for health in self._health_status.values()
            if health.healthy
        )
        
        return {
            "total_agents": len(self._agent_pool),
            "healthy_agents": healthy_count,
            "unhealthy_agents": len(self._agent_pool) - healthy_count,
            "average_age_seconds": (
                sum(agent_ages.values()) / len(agent_ages)
                if agent_ages else 0
            ),
            "oldest_agent_age_seconds": max(agent_ages.values()) if agent_ages else 0,
            "agents": list(self._agent_pool.keys())
        }
    
    async def cleanup_unhealthy_agents(self) -> int:
        """
        Remove unhealthy agents from pool
        
        Returns:
            Number of agents cleaned up
        """
        unhealthy_agents = []
        
        for pool_key, agent in self._agent_pool.items():
            try:
                health = await agent.health_check()
                if not health.healthy:
                    unhealthy_agents.append(agent)
            except Exception:
                unhealthy_agents.append(agent)
        
        for agent in unhealthy_agents:
            await self.destroy_agent(agent)
        
        logger.info(f"Cleaned up {len(unhealthy_agents)} unhealthy agents")
        
        return len(unhealthy_agents)


# ==================== Global Factory Instance ====================

_global_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """
    Get the global agent factory instance
    
    Returns:
        Global AgentFactory instance
    """
    global _global_factory
    
    if _global_factory is None:
        _global_factory = AgentFactory()
    
    return _global_factory


async def create_agent_from_config(
    agent_id: str,
    config: Optional[Dict[str, Any]] = None
) -> BaseAgent:
    """
    Convenience function to create an agent
    
    Args:
        agent_id: ID of agent to create
        config: Optional configuration
        
    Returns:
        Agent instance
    """
    factory = get_agent_factory()
    return await factory.create_agent(agent_id, config)


# ==================== Agent Pool Manager ====================

class AgentPoolManager:
    """
    Manages a pool of pre-initialized agents for better performance
    
    Useful for high-traffic scenarios where agent initialization is expensive.
    """
    
    def __init__(
        self,
        pool_size: int = 5,
        max_age_seconds: int = 3600
    ):
        """
        Initialize pool manager
        
        Args:
            pool_size: Number of agents to keep in pool per type
            max_age_seconds: Maximum age of agents before recreation
        """
        self.pool_size = pool_size
        self.max_age_seconds = max_age_seconds
        self.factory = AgentFactory()
        self._pools: Dict[str, list[BaseAgent]] = {}
        self._lock = asyncio.Lock()
    
    async def get_agent(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAgent:
        """
        Get an agent from the pool
        
        Args:
            agent_id: ID of agent type
            config: Optional configuration
            
        Returns:
            Agent instance
        """
        async with self._lock:
            # Initialize pool for this agent type if needed
            if agent_id not in self._pools:
                self._pools[agent_id] = []
            
            pool = self._pools[agent_id]
            
            # Try to get agent from pool
            if pool:
                agent = pool.pop(0)
                
                # Check if agent is still healthy and not too old
                try:
                    health = await agent.health_check()
                    if health.healthy:
                        return agent
                    else:
                        await self.factory.destroy_agent(agent)
                except Exception:
                    await self.factory.destroy_agent(agent)
            
            # Create new agent if pool is empty or agent was unhealthy
            return await self.factory.create_agent(agent_id, config)
    
    async def return_agent(self, agent: BaseAgent) -> None:
        """
        Return an agent to the pool
        
        Args:
            agent: Agent to return
        """
        async with self._lock:
            agent_id = agent.agent_id
            
            if agent_id not in self._pools:
                self._pools[agent_id] = []
            
            pool = self._pools[agent_id]
            
            # Only return to pool if under size limit
            if len(pool) < self.pool_size:
                pool.append(agent)
            else:
                # Pool is full, destroy agent
                await self.factory.destroy_agent(agent)
    
    async def warm_up(self, agent_id: str, count: Optional[int] = None) -> None:
        """
        Pre-create agents to warm up the pool
        
        Args:
            agent_id: Agent type to warm up
            count: Number of agents to create (defaults to pool_size)
        """
        count = count or self.pool_size
        
        logger.info(f"Warming up pool for {agent_id} with {count} agents")
        
        for _ in range(count):
            try:
                agent = await self.factory.create_agent(agent_id)
                await self.return_agent(agent)
            except Exception as e:
                logger.error(f"Error warming up agent {agent_id}: {e}")
    
    async def cleanup(self) -> None:
        """Clean up all pools"""
        async with self._lock:
            for agent_id, pool in self._pools.items():
                for agent in pool:
                    await self.factory.destroy_agent(agent)
                pool.clear()
            
            self._pools.clear()
            
        logger.info("Cleaned up all agent pools")
