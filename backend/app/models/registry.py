"""
Model Registry

Central registry for all available models and their capabilities.
Provides model discovery, capability querying, and health monitoring.
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from app.models.base import (
    BaseModelProvider,
    ModelProvider,
    ModelCapabilities,
    ModelConfig,
    ModelProviderFactory,
)

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a registered model"""
    provider: ModelProvider
    model_name: str
    display_name: str
    capabilities: ModelCapabilities
    is_available: bool = True
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, any] = field(default_factory=dict)


class ModelRegistry:
    """
    Central registry for all available models
    
    Manages model registration, discovery, and health monitoring.
    """
    
    def __init__(self):
        """Initialize model registry"""
        self._models: Dict[str, ModelInfo] = {}
        self._providers: Dict[ModelProvider, BaseModelProvider] = {}
        self._health_check_interval = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info("Model registry initialized")
    
    def register_model(
        self,
        provider: ModelProvider,
        model_name: str,
        display_name: str,
        capabilities: ModelCapabilities,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, any]] = None
    ):
        """
        Register a model in the registry
        
        Args:
            provider: Model provider
            model_name: Model identifier
            display_name: Human-readable name
            capabilities: Model capabilities
            tags: Optional tags for categorization
            metadata: Optional additional metadata
        """
        model_id = f"{provider.value}:{model_name}"
        
        self._models[model_id] = ModelInfo(
            provider=provider,
            model_name=model_name,
            display_name=display_name,
            capabilities=capabilities,
            tags=tags or set(),
            metadata=metadata or {}
        )
        
        logger.info(f"Registered model: {model_id}")
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get model information
        
        Args:
            model_id: Model identifier (provider:model_name)
            
        Returns:
            ModelInfo if found, None otherwise
        """
        return self._models.get(model_id)
    
    def list_models(
        self,
        provider: Optional[ModelProvider] = None,
        tags: Optional[Set[str]] = None,
        available_only: bool = True
    ) -> List[ModelInfo]:
        """
        List registered models
        
        Args:
            provider: Filter by provider
            tags: Filter by tags (any match)
            available_only: Only return available models
            
        Returns:
            List of ModelInfo objects
        """
        models = list(self._models.values())
        
        # Filter by provider
        if provider:
            models = [m for m in models if m.provider == provider]
        
        # Filter by tags
        if tags:
            models = [m for m in models if m.tags & tags]
        
        # Filter by availability
        if available_only:
            models = [m for m in models if m.is_available]
        
        return models
    
    def list_providers(self) -> List[ModelProvider]:
        """
        List all registered providers
        
        Returns:
            List of ModelProvider enums
        """
        providers = set(m.provider for m in self._models.values())
        return sorted(providers, key=lambda p: p.value)
    
    def find_models_by_capability(
        self,
        capability: str,
        min_context_length: Optional[int] = None,
        max_cost: Optional[float] = None
    ) -> List[ModelInfo]:
        """
        Find models by capability requirements
        
        Args:
            capability: Required capability (e.g., 'function_calling')
            min_context_length: Minimum context length required
            max_cost: Maximum cost per 1k tokens
            
        Returns:
            List of matching ModelInfo objects
        """
        matching_models = []
        
        for model in self._models.values():
            if not model.is_available:
                continue
            
            caps = model.capabilities
            
            # Check capability
            if capability == 'function_calling' and not caps.supports_function_calling:
                continue
            if capability == 'vision' and not caps.supports_vision:
                continue
            if capability == 'streaming' and not caps.supports_streaming:
                continue
            if capability == 'json_mode' and not caps.supports_json_mode:
                continue
            
            # Check context length
            if min_context_length and caps.max_context_length < min_context_length:
                continue
            
            # Check cost
            if max_cost:
                avg_cost = (caps.cost_per_1k_input_tokens + caps.cost_per_1k_output_tokens) / 2
                if avg_cost > max_cost:
                    continue
            
            matching_models.append(model)
        
        # Sort by cost (cheapest first)
        matching_models.sort(
            key=lambda m: (
                m.capabilities.cost_per_1k_input_tokens +
                m.capabilities.cost_per_1k_output_tokens
            )
        )
        
        return matching_models
    
    def get_cheapest_model(
        self,
        min_context_length: Optional[int] = None,
        required_capabilities: Optional[List[str]] = None
    ) -> Optional[ModelInfo]:
        """
        Get the cheapest available model
        
        Args:
            min_context_length: Minimum context length
            required_capabilities: List of required capabilities
            
        Returns:
            Cheapest ModelInfo or None
        """
        models = list(self._models.values())
        
        # Filter available models
        models = [m for m in models if m.is_available]
        
        # Filter by context length
        if min_context_length:
            models = [
                m for m in models
                if m.capabilities.max_context_length >= min_context_length
            ]
        
        # Filter by capabilities
        if required_capabilities:
            for capability in required_capabilities:
                models = self.find_models_by_capability(capability)
        
        if not models:
            return None
        
        # Sort by cost
        models.sort(
            key=lambda m: (
                m.capabilities.cost_per_1k_input_tokens +
                m.capabilities.cost_per_1k_output_tokens
            )
        )
        
        return models[0]
    
    def get_fastest_model(
        self,
        required_capabilities: Optional[List[str]] = None
    ) -> Optional[ModelInfo]:
        """
        Get the fastest available model
        
        Note: This is a heuristic based on model size/type.
        Actual performance may vary.
        
        Args:
            required_capabilities: List of required capabilities
            
        Returns:
            Fastest ModelInfo or None
        """
        models = list(self._models.values())
        
        # Filter available models
        models = [m for m in models if m.is_available]
        
        # Filter by capabilities
        if required_capabilities:
            for capability in required_capabilities:
                filtered = self.find_models_by_capability(capability)
                models = [m for m in models if m in filtered]
        
        if not models:
            return None
        
        # Heuristic: smaller models are generally faster
        # Priority: haiku > small > medium > large
        speed_priority = {
            'haiku': 0,
            'small': 1,
            'mini': 1,
            'turbo': 2,
            'medium': 3,
            'large': 4,
            'opus': 5,
            'ultra': 6,
        }
        
        def get_speed_score(model: ModelInfo) -> int:
            name_lower = model.model_name.lower()
            for key, score in speed_priority.items():
                if key in name_lower:
                    return score
            return 3  # Default to medium
        
        models.sort(key=get_speed_score)
        return models[0]
    
    async def health_check(self, model_id: str) -> bool:
        """
        Perform health check on a model
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if healthy, False otherwise
        """
        model = self._models.get(model_id)
        if not model:
            return False
        
        try:
            # Get or create provider instance
            provider = self._providers.get(model.provider)
            if not provider:
                # Create temporary config for health check
                # In production, this should use stored credentials
                logger.warning(
                    f"No provider instance for {model.provider}, "
                    "skipping health check"
                )
                return True
            
            # Perform health check
            is_healthy = await provider.validate_config()
            
            # Update model status
            model.is_available = is_healthy
            model.last_health_check = datetime.utcnow()
            
            if is_healthy:
                model.health_check_failures = 0
            else:
                model.health_check_failures += 1
                
                # Mark as unavailable after 3 consecutive failures
                if model.health_check_failures >= 3:
                    model.is_available = False
                    logger.warning(
                        f"Model {model_id} marked as unavailable after "
                        f"{model.health_check_failures} failures"
                    )
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {model_id}: {e}")
            model.health_check_failures += 1
            return False
    
    async def health_check_all(self):
        """Perform health check on all models"""
        logger.info("Starting health check for all models")
        
        tasks = [
            self.health_check(model_id)
            for model_id in self._models.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        healthy_count = sum(1 for r in results if r is True)
        total_count = len(results)
        
        logger.info(
            f"Health check complete: {healthy_count}/{total_count} models healthy"
        )
    
    async def start_health_monitoring(self):
        """Start periodic health monitoring"""
        if self._health_check_task:
            logger.warning("Health monitoring already running")
            return
        
        async def monitor():
            while True:
                try:
                    await self.health_check_all()
                    await asyncio.sleep(self._health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in health monitoring: {e}")
                    await asyncio.sleep(60)  # Wait before retry
        
        self._health_check_task = asyncio.create_task(monitor())
        logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self):
        """Stop periodic health monitoring"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Health monitoring stopped")
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get registry statistics
        
        Returns:
            Dictionary with statistics
        """
        total_models = len(self._models)
        available_models = sum(1 for m in self._models.values() if m.is_available)
        
        providers = {}
        for model in self._models.values():
            provider_name = model.provider.value
            if provider_name not in providers:
                providers[provider_name] = {'total': 0, 'available': 0}
            providers[provider_name]['total'] += 1
            if model.is_available:
                providers[provider_name]['available'] += 1
        
        return {
            'total_models': total_models,
            'available_models': available_models,
            'unavailable_models': total_models - available_models,
            'providers': providers,
            'health_check_interval': self._health_check_interval,
            'monitoring_active': self._health_check_task is not None
        }


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """
    Get global model registry instance
    
    Returns:
        ModelRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _initialize_default_models()
    return _registry


def _initialize_default_models():
    """Initialize registry with default models"""
    registry = get_registry()
    
    # OpenAI Models
    registry.register_model(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4-turbo-preview",
        display_name="GPT-4 Turbo",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=False,
            supports_json_mode=True,
            max_context_length=128000,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.01,
            cost_per_1k_output_tokens=0.03,
        ),
        tags={'openai', 'gpt4', 'large', 'premium'}
    )
    
    registry.register_model(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4",
        display_name="GPT-4",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=False,
            supports_json_mode=False,
            max_context_length=8192,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.03,
            cost_per_1k_output_tokens=0.06,
        ),
        tags={'openai', 'gpt4', 'large', 'premium'}
    )
    
    registry.register_model(
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        display_name="GPT-3.5 Turbo",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=False,
            supports_json_mode=True,
            max_context_length=16385,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.0005,
            cost_per_1k_output_tokens=0.0015,
        ),
        tags={'openai', 'gpt35', 'fast', 'affordable'}
    )
    
    # Anthropic Models
    registry.register_model(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_json_mode=False,
            max_context_length=200000,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.015,
            cost_per_1k_output_tokens=0.075,
        ),
        tags={'anthropic', 'claude3', 'large', 'premium', 'vision'}
    )
    
    registry.register_model(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        display_name="Claude 3 Sonnet",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_json_mode=False,
            max_context_length=200000,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.003,
            cost_per_1k_output_tokens=0.015,
        ),
        tags={'anthropic', 'claude3', 'medium', 'balanced', 'vision'}
    )
    
    registry.register_model(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_json_mode=False,
            max_context_length=200000,
            max_output_tokens=4096,
            cost_per_1k_input_tokens=0.00025,
            cost_per_1k_output_tokens=0.00125,
        ),
        tags={'anthropic', 'claude3', 'small', 'fast', 'affordable', 'vision'}
    )
    
    logger.info("Default models initialized in registry")


# Export
__all__ = ["ModelRegistry", "ModelInfo", "get_registry"]
