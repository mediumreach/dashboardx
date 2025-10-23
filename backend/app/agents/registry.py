"""
Agent Registry System

Central registry for discovering, registering, and managing agent providers.
Enables dynamic agent discovery and plugin-based architecture.
"""

import logging
from typing import Dict, Type, List, Optional, Set
from threading import Lock
import inspect

from app.agents.base import BaseAgent, AgentType, AgentCapabilities

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all agent implementations
    
    Provides thread-safe registration and discovery of agent adapters.
    Agents can be registered manually or auto-discovered.
    
    Example:
        ```python
        # Register an agent
        AgentRegistry.register("my-agent", MyAgentClass)
        
        # Get an agent class
        agent_class = AgentRegistry.get("my-agent")
        
        # List all agents
        agents = AgentRegistry.list_agents()
        ```
    """
    
    # Class-level storage
    _agents: Dict[str, Type[BaseAgent]] = {}
    _metadata: Dict[str, Dict] = {}
    _lock = Lock()
    _initialized = False
    
    @classmethod
    def register(
        cls,
        agent_id: str,
        agent_class: Type[BaseAgent],
        metadata: Optional[Dict] = None,
        override: bool = False
    ) -> None:
        """
        Register an agent adapter
        
        Args:
            agent_id: Unique identifier for the agent
            agent_class: Agent class (must inherit from BaseAgent)
            metadata: Optional metadata about the agent
            override: Whether to override existing registration
            
        Raises:
            ValueError: If agent_id already registered and override=False
            TypeError: If agent_class doesn't inherit from BaseAgent
        """
        with cls._lock:
            # Validate agent class
            if not inspect.isclass(agent_class):
                raise TypeError(f"agent_class must be a class, got {type(agent_class)}")
            
            if not issubclass(agent_class, BaseAgent):
                raise TypeError(
                    f"agent_class must inherit from BaseAgent, "
                    f"got {agent_class.__name__}"
                )
            
            # Check for existing registration
            if agent_id in cls._agents and not override:
                raise ValueError(
                    f"Agent '{agent_id}' is already registered. "
                    f"Use override=True to replace it."
                )
            
            # Register agent
            cls._agents[agent_id] = agent_class
            cls._metadata[agent_id] = metadata or {}
            
            logger.info(
                f"Registered agent: {agent_id} ({agent_class.__name__})"
            )
    
    @classmethod
    def unregister(cls, agent_id: str) -> bool:
        """
        Unregister an agent
        
        Args:
            agent_id: ID of agent to unregister
            
        Returns:
            True if agent was unregistered, False if not found
        """
        with cls._lock:
            if agent_id in cls._agents:
                del cls._agents[agent_id]
                if agent_id in cls._metadata:
                    del cls._metadata[agent_id]
                
                logger.info(f"Unregistered agent: {agent_id}")
                return True
            
            return False
    
    @classmethod
    def get(cls, agent_id: str) -> Optional[Type[BaseAgent]]:
        """
        Get agent class by ID
        
        Args:
            agent_id: ID of agent to retrieve
            
        Returns:
            Agent class or None if not found
        """
        return cls._agents.get(agent_id)
    
    @classmethod
    def get_metadata(cls, agent_id: str) -> Optional[Dict]:
        """
        Get agent metadata
        
        Args:
            agent_id: ID of agent
            
        Returns:
            Metadata dictionary or None if not found
        """
        return cls._metadata.get(agent_id)
    
    @classmethod
    def list_agents(cls, enabled_only: bool = False) -> List[str]:
        """
        List all registered agent IDs
        
        Args:
            enabled_only: If True, only return enabled agents
            
        Returns:
            List of agent IDs
        """
        if not enabled_only:
            return list(cls._agents.keys())
        
        # Filter by enabled status in metadata
        return [
            agent_id for agent_id in cls._agents.keys()
            if cls._metadata.get(agent_id, {}).get("enabled", True)
        ]
    
    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict]:
        """
        Get metadata for all registered agents
        
        Returns:
            Dictionary mapping agent_id to metadata
        """
        return cls._metadata.copy()
    
    @classmethod
    def exists(cls, agent_id: str) -> bool:
        """
        Check if agent is registered
        
        Args:
            agent_id: ID to check
            
        Returns:
            True if agent exists, False otherwise
        """
        return agent_id in cls._agents
    
    @classmethod
    def get_by_type(cls, agent_type: AgentType) -> List[str]:
        """
        Get all agents of a specific type
        
        Args:
            agent_type: Type of agents to find
            
        Returns:
            List of agent IDs matching the type
        """
        matching_agents = []
        
        for agent_id, metadata in cls._metadata.items():
            if metadata.get("type") == agent_type.value:
                matching_agents.append(agent_id)
        
        return matching_agents
    
    @classmethod
    def get_by_capability(cls, capability: str) -> List[str]:
        """
        Get all agents with a specific capability
        
        Args:
            capability: Capability to search for (e.g., "supports_streaming")
            
        Returns:
            List of agent IDs with the capability
        """
        matching_agents = []
        
        for agent_id, metadata in cls._metadata.items():
            capabilities = metadata.get("capabilities", {})
            if capabilities.get(capability, False):
                matching_agents.append(agent_id)
        
        return matching_agents
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered agents
        
        Warning: This will remove all agent registrations!
        Mainly useful for testing.
        """
        with cls._lock:
            cls._agents.clear()
            cls._metadata.clear()
            logger.warning("Cleared all agent registrations")
    
    @classmethod
    def count(cls) -> int:
        """
        Get count of registered agents
        
        Returns:
            Number of registered agents
        """
        return len(cls._agents)
    
    @classmethod
    def validate_all(cls) -> Dict[str, bool]:
        """
        Validate all registered agents
        
        Checks if each agent class is properly configured.
        
        Returns:
            Dictionary mapping agent_id to validation status
        """
        results = {}
        
        for agent_id, agent_class in cls._agents.items():
            try:
                # Check if class has required methods
                required_methods = [
                    'execute',
                    'execute_streaming',
                    'get_capabilities',
                    'health_check'
                ]
                
                for method in required_methods:
                    if not hasattr(agent_class, method):
                        results[agent_id] = False
                        logger.error(
                            f"Agent {agent_id} missing required method: {method}"
                        )
                        break
                else:
                    results[agent_id] = True
                    
            except Exception as e:
                logger.error(f"Error validating agent {agent_id}: {e}")
                results[agent_id] = False
        
        return results
    
    @classmethod
    def get_statistics(cls) -> Dict:
        """
        Get registry statistics
        
        Returns:
            Dictionary with registry statistics
        """
        agent_types = {}
        capabilities_count = {}
        
        for agent_id, metadata in cls._metadata.items():
            # Count by type
            agent_type = metadata.get("type", "unknown")
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
            
            # Count capabilities
            capabilities = metadata.get("capabilities", {})
            for cap, enabled in capabilities.items():
                if enabled:
                    capabilities_count[cap] = capabilities_count.get(cap, 0) + 1
        
        return {
            "total_agents": len(cls._agents),
            "enabled_agents": len(cls.list_agents(enabled_only=True)),
            "agent_types": agent_types,
            "capabilities": capabilities_count
        }
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize the registry
        
        Called once at application startup to discover and register agents.
        """
        if cls._initialized:
            logger.warning("Registry already initialized")
            return
        
        logger.info("Initializing Agent Registry...")
        
        # Auto-discover and register agents from adapters module
        try:
            cls._auto_discover_agents()
        except Exception as e:
            logger.error(f"Error during auto-discovery: {e}")
        
        cls._initialized = True
        
        # Log statistics
        stats = cls.get_statistics()
        logger.info(
            f"Agent Registry initialized: {stats['total_agents']} agents registered"
        )
    
    @classmethod
    def _auto_discover_agents(cls) -> None:
        """
        Auto-discover agents from the adapters module
        
        Scans the adapters module for classes that inherit from BaseAgent
        and automatically registers them.
        """
        try:
            import importlib
            import pkgutil
            from app.agents import adapters
            
            # Iterate through all modules in adapters package
            for importer, modname, ispkg in pkgutil.iter_modules(adapters.__path__):
                if modname.startswith('_'):
                    continue
                
                try:
                    # Import the module
                    module = importlib.import_module(f'app.agents.adapters.{modname}')
                    
                    # Find all BaseAgent subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, BaseAgent) and 
                            obj is not BaseAgent and
                            obj.__module__ == module.__name__):
                            
                            # Generate agent_id from class name
                            agent_id = modname.replace('_adapter', '')
                            
                            # Register if not already registered
                            if not cls.exists(agent_id):
                                cls.register(
                                    agent_id=agent_id,
                                    agent_class=obj,
                                    metadata={
                                        "auto_discovered": True,
                                        "module": modname
                                    }
                                )
                                logger.info(f"Auto-discovered agent: {agent_id}")
                
                except Exception as e:
                    logger.error(f"Error importing adapter module {modname}: {e}")
        
        except ImportError:
            logger.warning("Adapters module not found, skipping auto-discovery")


# ==================== Decorator for Easy Registration ====================

def register_agent(
    agent_id: str,
    metadata: Optional[Dict] = None
):
    """
    Decorator to register an agent class
    
    Example:
        ```python
        @register_agent("my-agent", metadata={"version": "1.0"})
        class MyAgent(BaseAgent):
            pass
        ```
    
    Args:
        agent_id: Unique identifier for the agent
        metadata: Optional metadata
        
    Returns:
        Decorator function
    """
    def decorator(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        AgentRegistry.register(agent_id, agent_class, metadata)
        return agent_class
    
    return decorator


# ==================== Helper Functions ====================

def get_available_agents() -> List[Dict]:
    """
    Get list of available agents with their metadata
    
    Returns:
        List of dictionaries with agent information
    """
    agents = []
    
    for agent_id in AgentRegistry.list_agents():
        agent_class = AgentRegistry.get(agent_id)
        metadata = AgentRegistry.get_metadata(agent_id)
        
        if agent_class:
            agents.append({
                "id": agent_id,
                "name": agent_class.__name__,
                "metadata": metadata
            })
    
    return agents


def find_best_agent(
    query: str,
    required_capabilities: Optional[List[str]] = None
) -> Optional[str]:
    """
    Find the best agent for a given query
    
    Args:
        query: User query
        required_capabilities: List of required capabilities
        
    Returns:
        Agent ID of best match, or None if no suitable agent found
    """
    if not required_capabilities:
        # Return first available agent
        agents = AgentRegistry.list_agents(enabled_only=True)
        return agents[0] if agents else None
    
    # Find agents with all required capabilities
    suitable_agents = set(AgentRegistry.list_agents(enabled_only=True))
    
    for capability in required_capabilities:
        agents_with_cap = set(AgentRegistry.get_by_capability(capability))
        suitable_agents &= agents_with_cap
    
    if not suitable_agents:
        return None
    
    # Return agent with highest priority
    best_agent = None
    best_priority = float('inf')
    
    for agent_id in suitable_agents:
        metadata = AgentRegistry.get_metadata(agent_id)
        priority = metadata.get("priority", 999)
        
        if priority < best_priority:
            best_priority = priority
            best_agent = agent_id
    
    return best_agent
