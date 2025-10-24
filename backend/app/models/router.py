a"""
Intelligent Model Router

Routes requests to the optimal model based on:
- Cost optimization
- Performance requirements
- Capability matching
- Load balancing
- Automatic failover
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from enum import Enum
from dataclasses import dataclass
import time

from app.models.base import (
    BaseModelProvider,
    ModelProvider,
    ModelConfig,
    ModelResponse,
    StreamChunk,
    ModelProviderFactory,
)
from app.models.registry import ModelRegistry, ModelInfo, get_registry

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Model routing strategies"""
    COST_OPTIMIZED = "cost_optimized"  # Choose cheapest model
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Choose fastest model
    QUALITY_OPTIMIZED = "quality_optimized"  # Choose best quality model
    BALANCED = "balanced"  # Balance cost and performance
    ROUND_ROBIN = "round_robin"  # Distribute load evenly
    MANUAL = "manual"  # User specifies model


@dataclass
class RoutingContext:
    """Context for routing decisions"""
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    required_capabilities: List[str] = None
    min_context_length: Optional[int] = None
    max_cost_per_1k_tokens: Optional[float] = None
    preferred_providers: Optional[List[ModelProvider]] = None
    excluded_providers: Optional[List[ModelProvider]] = None
    manual_model: Optional[str] = None  # For manual strategy
    
    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []


class ModelRouter:
    """
    Intelligent model router
    
    Selects the optimal model for each request based on routing strategy,
    requirements, and current model availability.
    """
    
    def __init__(self, registry: Optional[ModelRegistry] = None):
        """
        Initialize model router
        
        Args:
            registry: Model registry (uses global if not provided)
        """
        self.registry = registry or get_registry()
        self._round_robin_index = 0
        self._provider_cache: Dict[str, BaseModelProvider] = {}
        
        logger.info("Model router initialized")
    
    async def route(
        self,
        messages: List[Dict[str, str]],
        context: RoutingContext,
        **kwargs
    ) -> ModelResponse:
        """
        Route request to optimal model
        
        Args:
            messages: Messages to send to model
            context: Routing context
            **kwargs: Additional generation parameters
            
        Returns:
            ModelResponse from selected model
        """
        start_time = time.time()
        
        # Select model
        model_info = self._select_model(context)
        if not model_info:
            raise ValueError("No suitable model found for request")
        
        logger.info(
            f"Routed to {model_info.provider.value}:{model_info.model_name} "
            f"(strategy: {context.strategy})"
        )
        
        # Get or create provider
        provider = await self._get_provider(model_info, context)
        
        # Try primary model
        try:
            response = await provider.generate(messages, **kwargs)
            response.metadata['routing_strategy'] = context.strategy.value
            response.metadata['selection_time_ms'] = (time.time() - start_time) * 1000
            return response
            
        except Exception as e:
            logger.error(f"Primary model failed: {e}")
            
            # Try fallback if available
            if hasattr(provider.config, 'fallback_models') and provider.config.fallback_models:
                logger.info("Attempting fallback models")
                return await self._try_fallback(
                    messages,
                    provider.config.fallback_models,
                    context,
                    **kwargs
                )
            
            raise
    
    async def route_stream(
        self,
        messages: List[Dict[str, str]],
        context: RoutingContext,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Route streaming request to optimal model
        
        Args:
            messages: Messages to send to model
            context: Routing context
            **kwargs: Additional generation parameters
            
        Yields:
            StreamChunk objects from selected model
        """
        # Select model
        model_info = self._select_model(context)
        if not model_info:
            raise ValueError("No suitable model found for request")
        
        # Check streaming support
        if not model_info.capabilities.supports_streaming:
            raise ValueError(
                f"Model {model_info.model_name} does not support streaming"
            )
        
        logger.info(
            f"Streaming routed to {model_info.provider.value}:{model_info.model_name}"
        )
        
        # Get or create provider
        provider = await self._get_provider(model_info, context)
        
        # Stream from provider
        async for chunk in provider.generate_stream(messages, **kwargs):
            yield chunk
    
    def _select_model(self, context: RoutingContext) -> Optional[ModelInfo]:
        """
        Select optimal model based on routing context
        
        Args:
            context: Routing context
            
        Returns:
            Selected ModelInfo or None
        """
        if context.strategy == RoutingStrategy.MANUAL:
            return self._select_manual(context)
        elif context.strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._select_cost_optimized(context)
        elif context.strategy == RoutingStrategy.PERFORMANCE_OPTIMIZED:
            return self._select_performance_optimized(context)
        elif context.strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            return self._select_quality_optimized(context)
        elif context.strategy == RoutingStrategy.BALANCED:
            return self._select_balanced(context)
        elif context.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._select_round_robin(context)
        else:
            raise ValueError(f"Unknown routing strategy: {context.strategy}")
    
    def _select_manual(self, context: RoutingContext) -> Optional[ModelInfo]:
        """Select manually specified model"""
        if not context.manual_model:
            raise ValueError("Manual model not specified")
        
        return self.registry.get_model(context.manual_model)
    
    def _select_cost_optimized(self, context: RoutingContext) -> Optional[ModelInfo]:
        """Select cheapest model that meets requirements"""
        models = self._filter_models(context)
        
        if not models:
            return None
        
        # Sort by cost (cheapest first)
        models.sort(
            key=lambda m: (
                m.capabilities.cost_per_1k_input_tokens +
                m.capabilities.cost_per_1k_output_tokens
            )
        )
        
        return models[0]
    
    def _select_performance_optimized(
        self,
        context: RoutingContext
    ) -> Optional[ModelInfo]:
        """Select fastest model that meets requirements"""
        models = self._filter_models(context)
        
        if not models:
            return None
        
        # Use registry's fastest model selection
        return self.registry.get_fastest_model(context.required_capabilities)
    
    def _select_quality_optimized(
        self,
        context: RoutingContext
    ) -> Optional[ModelInfo]:
        """Select highest quality model that meets requirements"""
        models = self._filter_models(context)
        
        if not models:
            return None
        
        # Heuristic: more expensive models are generally higher quality
        # Priority: opus > large > medium > small
        quality_priority = {
            'opus': 0,
            'ultra': 0,
            'large': 1,
            'turbo': 2,
            'medium': 3,
            'small': 4,
            'mini': 5,
            'haiku': 5,
        }
        
        def get_quality_score(model: ModelInfo) -> int:
            name_lower = model.model_name.lower()
            for key, score in quality_priority.items():
                if key in name_lower:
                    return score
            return 3  # Default to medium
        
        models.sort(key=get_quality_score)
        return models[0]
    
    def _select_balanced(self, context: RoutingContext) -> Optional[ModelInfo]:
        """Select model with best cost/performance balance"""
        models = self._filter_models(context)
        
        if not models:
            return None
        
        # Calculate balance score (lower is better)
        def balance_score(model: ModelInfo) -> float:
            # Normalize cost (0-1 scale, assuming max $0.1 per 1k tokens)
            avg_cost = (
                model.capabilities.cost_per_1k_input_tokens +
                model.capabilities.cost_per_1k_output_tokens
            ) / 2
            cost_score = min(avg_cost / 0.1, 1.0)
            
            # Normalize quality (0-1 scale based on model tier)
            quality_map = {
                'opus': 1.0, 'ultra': 1.0, 'large': 0.8,
                'turbo': 0.7, 'medium': 0.6, 'small': 0.4,
                'mini': 0.3, 'haiku': 0.3
            }
            name_lower = model.model_name.lower()
            quality_score = 0.5  # Default
            for key, score in quality_map.items():
                if key in name_lower:
                    quality_score = score
                    break
            
            # Balance: 60% quality, 40% cost
            return (0.4 * cost_score) + (0.6 * (1 - quality_score))
        
        models.sort(key=balance_score)
        return models[0]
    
    def _select_round_robin(self, context: RoutingContext) -> Optional[ModelInfo]:
        """Select model using round-robin load balancing"""
        models = self._filter_models(context)
        
        if not models:
            return None
        
        # Select next model in rotation
        selected = models[self._round_robin_index % len(models)]
        self._round_robin_index += 1
        
        return selected
    
    def _filter_models(self, context: RoutingContext) -> List[ModelInfo]:
        """
        Filter models based on context requirements
        
        Args:
            context: Routing context
            
        Returns:
            List of suitable models
        """
        # Start with all available models
        models = self.registry.list_models(available_only=True)
        
        # Filter by preferred providers
        if context.preferred_providers:
            models = [
                m for m in models
                if m.provider in context.preferred_providers
            ]
        
        # Filter by excluded providers
        if context.excluded_providers:
            models = [
                m for m in models
                if m.provider not in context.excluded_providers
            ]
        
        # Filter by context length
        if context.min_context_length:
            models = [
                m for m in models
                if m.capabilities.max_context_length >= context.min_context_length
            ]
        
        # Filter by cost
        if context.max_cost_per_1k_tokens:
            models = [
                m for m in models
                if (
                    m.capabilities.cost_per_1k_input_tokens +
                    m.capabilities.cost_per_1k_output_tokens
                ) / 2 <= context.max_cost_per_1k_tokens
            ]
        
        # Filter by capabilities
        for capability in context.required_capabilities:
            if capability == 'function_calling':
                models = [
                    m for m in models
                    if m.capabilities.supports_function_calling
                ]
            elif capability == 'vision':
                models = [
                    m for m in models
                    if m.capabilities.supports_vision
                ]
            elif capability == 'streaming':
                models = [
                    m for m in models
                    if m.capabilities.supports_streaming
                ]
            elif capability == 'json_mode':
                models = [
                    m for m in models
                    if m.capabilities.supports_json_mode
                ]
        
        return models
    
    async def _get_provider(
        self,
        model_info: ModelInfo,
        context: RoutingContext
    ) -> BaseModelProvider:
        """
        Get or create provider instance
        
        Args:
            model_info: Model information
            context: Routing context
            
        Returns:
            Provider instance
        """
        cache_key = f"{model_info.provider.value}:{model_info.model_name}"
        
        # Return cached provider if available
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]
        
        # Create new provider
        # Note: In production, API keys should come from secure storage
        from app.config import settings
        
        # Build config based on provider
        if model_info.provider == ModelProvider.OPENAI:
            config = ModelConfig(
                provider=model_info.provider,
                model_name=model_info.model_name,
                api_key=settings.openai_api_key,
                organization_id=settings.openai_organization_id,
            )
        elif model_info.provider == ModelProvider.ANTHROPIC:
            config = ModelConfig(
                provider=model_info.provider,
                model_name=model_info.model_name,
                api_key=settings.anthropic_api_key,
            )
        else:
            raise ValueError(f"Provider {model_info.provider} not yet implemented")
        
        # Create provider using factory
        provider = ModelProviderFactory.create(config)
        
        # Cache provider
        self._provider_cache[cache_key] = provider
        
        return provider
    
    async def _try_fallback(
        self,
        messages: List[Dict[str, str]],
        fallback_models: List[str],
        context: RoutingContext,
        **kwargs
    ) -> ModelResponse:
        """
        Try fallback models
        
        Args:
            messages: Messages to send
            fallback_models: List of fallback model IDs
            context: Routing context
            **kwargs: Generation parameters
            
        Returns:
            ModelResponse from successful fallback
            
        Raises:
            Exception if all fallbacks fail
        """
        last_error = None
        
        for model_id in fallback_models:
            try:
                logger.info(f"Trying fallback model: {model_id}")
                
                model_info = self.registry.get_model(model_id)
                if not model_info or not model_info.is_available:
                    continue
                
                provider = await self._get_provider(model_info, context)
                response = await provider.generate(messages, **kwargs)
                
                response.metadata['is_fallback'] = True
                response.metadata['fallback_model'] = model_id
                
                logger.info(f"Fallback successful: {model_id}")
                return response
                
            except Exception as e:
                logger.warning(f"Fallback {model_id} failed: {e}")
                last_error = e
                continue
        
        # All fallbacks failed
        raise Exception(f"All fallback models failed. Last error: {last_error}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics
        
        Returns:
            Dictionary with routing stats
        """
        return {
            'cached_providers': len(self._provider_cache),
            'round_robin_index': self._round_robin_index,
            'registry_stats': self.registry.get_stats()
        }
    
    def clear_cache(self):
        """Clear provider cache"""
        self._provider_cache.clear()
        logger.info("Router cache cleared")


# Global router instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """
    Get global model router instance
    
    Returns:
        ModelRouter instance
    """
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


# Export
__all__ = [
    "RoutingStrategy",
    "RoutingContext",
    "ModelRouter",
    "get_router",
]
