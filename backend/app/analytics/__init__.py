"""
Advanced Analytics Module for Data Analytics SaaS

This module provides comprehensive analytics capabilities including:
- Multi-modal RAG for structured and unstructured data
- Real-time data processing
- ML/AI-powered predictions
- Statistical analysis
- Intelligent visualization recommendations
"""

from .engine import AnalyticsEngine
from .connectors import DataConnectorFactory
from .processors import DataProcessor, StreamProcessor
from .ml_models import MLEngine
from .agents import AnalyticsAgentOrchestrator

__all__ = [
    'AnalyticsEngine',
    'DataConnectorFactory',
    'DataProcessor',
    'StreamProcessor',
    'MLEngine',
    'AnalyticsAgentOrchestrator'
]

# Module version
__version__ = '1.0.0'
