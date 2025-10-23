"""
Machine Learning Models for Predictive Analytics

Provides AutoML capabilities, time series forecasting,
anomaly detection, and optimization algorithms.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import joblib
from dataclasses import dataclass

# ML Libraries
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.svm import SVR, SVC
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

# Time Series
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

# Deep Learning (optional, requires tensorflow)
try:
    import tensorflow as tf
    from tensorflow import keras
    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False

# Optimization
from scipy.optimize import minimize, differential_evolution

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for ML models"""
    model_type: str  # regression, classification, time_series, clustering
    algorithm: str  # specific algorithm to use
    hyperparameters: Dict[str, Any]
    features: List[str]
    target: str
    validation_split: float = 0.2
    cross_validation_folds: int = 5
    auto_tune: bool = True


class MLEngine:
    """
    Machine Learning Engine for predictive analytics
    """
    
    def __init__(self):
        """Initialize ML Engine"""
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_metadata = {}
        self.performance_history = []
        
        logger.info(f"MLEngine initialized (Deep Learning: {DEEP_LEARNING_AVAILABLE})")
    
    async def prepare_data(
        self,
        data: Any,
        config: Optional[ModelConfig] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for ML models
        
        Args:
            data: Input data
            config: Model configuration
            
        Returns:
            Tuple of features DataFrame and target Series
        """
        # Convert to DataFrame
        if isinstance(data, dict) and "data" in data:
            df = pd.DataFrame(data["data"])
        elif isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Handle missing values
        df = await self._handle_missing_values(df)
        
        # Encode categorical variables
        df = await self._encode_categorical_variables(df)
        
        # Feature engineering
        df = await self._engineer_features(df)
        
        # Split features and target
        if config and config.target in df.columns:
            X = df.drop(columns=[config.target])
            y = df[config.target]
        else:
            # If no target specified, prepare for unsupervised learning
            X = df
            y = None
        
        # Scale features
        X = await self._scale_features(X)
        
        return X, y
    
    async def train_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        config: ModelConfig
    ) -> Dict[str, Any]:
        """
        Train a machine learning model
        
        Args:
            X: Features
            y: Target variable
            config: Model configuration
            
        Returns:
            Training results including model and metrics
        """
        logger.info(f"Training {config.algorithm} model")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=config.validation_split,
            random_state=42
        )
        
        # Select and configure model
        model = await self._get_model(config)
        
        # Auto-tune hyperparameters if requested
        if config.auto_tune:
            model = await self._tune_hyperparameters(
                model, X_train, y_train, config
            )
        
        # Train model
        model.fit(X_train, y_train)
        
        # Make predictions
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        # Calculate metrics
        metrics = await self._calculate_metrics(
            y_train, y_pred_train, y_test, y_pred_test, config.model_type
        )
        
        # Store model
        model_id = f"{config.algorithm}_{datetime.utcnow().timestamp()}"
        self.models[model_id] = model
        self.model_metadata[model_id] = {
            "config": config,
            "metrics": metrics,
            "trained_at": datetime.utcnow().isoformat(),
            "feature_importance": await self._get_feature_importance(model, X.columns)
        }
        
        return {
            "model_id": model_id,
            "metrics": metrics,
            "feature_importance": self.model_metadata[model_id]["feature_importance"]
        }
    
    async def predict(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate predictions using trained models
        
        Args:
            data: Input data for prediction
            context: Additional context (model_id, etc.)
            
        Returns:
            Predictions with confidence scores
        """
        # Prepare data
        X, _ = await self.prepare_data(data)
        
        # Get model
        model_id = context.get("model_id") if context else None
        if not model_id:
            # Use most recent model
            model_id = list(self.models.keys())[-1] if self.models else None
        
        if not model_id or model_id not in self.models:
            # Train a new model if none exists
            logger.info("No trained model found, training new model")
            # This would need proper configuration
            return {"error": "No trained model available"}
        
        model = self.models[model_id]
        config = self.model_metadata[model_id]["config"]
        
        # Generate predictions
        predictions = model.predict(X)
        
        # Get prediction probabilities if available
        probabilities = None
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)
        
        # Format results
        results = {
            "predictions": predictions.tolist(),
            "model_id": model_id,
            "model_type": config.model_type,
            "algorithm": config.algorithm,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if probabilities is not None:
            results["probabilities"] = probabilities.tolist()
            results["confidence_scores"] = np.max(probabilities, axis=1).tolist()
        
        return results
    
    async def forecast_time_series(
        self,
        data: pd.DataFrame,
        target_column: str,
        periods: int = 30,
        method: str = "auto"
    ) -> Dict[str, Any]:
        """
        Perform time series forecasting
        
        Args:
            data: Time series data
            target_column: Column to forecast
            periods: Number of periods to forecast
            method: Forecasting method (auto, arima, prophet, lstm)
            
        Returns:
            Forecast results with confidence intervals
        """
        logger.info(f"Forecasting {periods} periods using {method}")
        
        # Prepare time series data
        ts_data = data[target_column].values
        
        # Check stationarity
        is_stationary = await self._check_stationarity(ts_data)
        
        # Select forecasting method
        if method == "auto":
            method = "arima" if is_stationary else "arima"  # Would use more sophisticated selection
        
        # Perform forecasting
        if method == "arima":
            forecast = await self._arima_forecast(ts_data, periods)
        elif method == "lstm" and DEEP_LEARNING_AVAILABLE:
            forecast = await self._lstm_forecast(ts_data, periods)
        else:
            # Fallback to simple method
            forecast = await self._simple_forecast(ts_data, periods)
        
        # Calculate confidence intervals
        std_error = np.std(ts_data) * np.sqrt(np.arange(1, periods + 1))
        lower_bound = forecast - 1.96 * std_error
        upper_bound = forecast + 1.96 * std_error
        
        return {
            "forecast": forecast.tolist(),
            "lower_bound": lower_bound.tolist(),
            "upper_bound": upper_bound.tolist(),
            "method": method,
            "periods": periods,
            "is_stationary": is_stationary,
            "historical_mean": float(np.mean(ts_data)),
            "historical_std": float(np.std(ts_data))
        }
    
    async def detect_anomalies(
        self,
        data: pd.DataFrame,
        method: str = "isolation_forest",
        contamination: float = 0.1
    ) -> Dict[str, Any]:
        """
        Detect anomalies in data
        
        Args:
            data: Input data
            method: Anomaly detection method
            contamination: Expected proportion of anomalies
            
        Returns:
            Anomaly detection results
        """
        logger.info(f"Detecting anomalies using {method}")
        
        # Prepare data
        X, _ = await self.prepare_data(data)
        
        # Select anomaly detection method
        if method == "isolation_forest":
            detector = IsolationForest(contamination=contamination, random_state=42)
        elif method == "statistical":
            # Use statistical methods (z-score, IQR)
            return await self._statistical_anomaly_detection(X)
        else:
            detector = IsolationForest(contamination=contamination, random_state=42)
        
        # Fit and predict
        anomalies = detector.fit_predict(X)
        anomaly_scores = detector.score_samples(X)
        
        # Get anomaly indices
        anomaly_indices = np.where(anomalies == -1)[0]
        normal_indices = np.where(anomalies == 1)[0]
        
        return {
            "anomaly_indices": anomaly_indices.tolist(),
            "normal_indices": normal_indices.tolist(),
            "anomaly_scores": anomaly_scores.tolist(),
            "num_anomalies": len(anomaly_indices),
            "anomaly_rate": len(anomaly_indices) / len(X),
            "method": method,
            "threshold": float(np.percentile(anomaly_scores, contamination * 100))
        }
    
    async def optimize(
        self,
        data: pd.DataFrame,
        constraints: Dict[str, Any],
        objective: str = "maximize"
    ) -> Dict[str, Any]:
        """
        Perform optimization based on constraints
        
        Args:
            data: Input data
            constraints: Optimization constraints
            objective: Optimization objective (maximize/minimize)
            
        Returns:
            Optimization results
        """
        logger.info(f"Running optimization with objective: {objective}")
        
        # Define objective function
        def objective_function(x):
            # This would be customized based on the specific problem
            return -np.sum(x ** 2) if objective == "maximize" else np.sum(x ** 2)
        
        # Set up constraints
        bounds = constraints.get("bounds", [(0, 1)] * len(data.columns))
        
        # Run optimization
        result = differential_evolution(
            objective_function,
            bounds,
            seed=42,
            maxiter=100
        )
        
        return {
            "optimal_values": result.x.tolist(),
            "optimal_objective": float(result.fun),
            "success": result.success,
            "message": result.message,
            "iterations": result.nit,
            "objective": objective
        }
    
    async def calculate_confidence(
        self,
        predictions: Dict[str, Any]
    ) -> List[float]:
        """
        Calculate confidence scores for predictions
        
        Args:
            predictions: Prediction results
            
        Returns:
            List of confidence scores
        """
        if "probabilities" in predictions:
            # Use probability scores
            return np.max(predictions["probabilities"], axis=1).tolist()
        elif "predictions" in predictions:
            # Generate pseudo-confidence based on prediction variance
            preds = np.array(predictions["predictions"])
            # Simple confidence based on distance from mean
            mean = np.mean(preds)
            std = np.std(preds)
            if std > 0:
                confidence = 1 - np.abs(preds - mean) / (3 * std)
                confidence = np.clip(confidence, 0, 1)
            else:
                confidence = np.ones_like(preds)
            return confidence.tolist()
        else:
            return []
    
    async def explain_predictions(
        self,
        predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate explanations for predictions
        
        Args:
            predictions: Prediction results
            
        Returns:
            Explanations for the predictions
        """
        explanations = {
            "model_type": predictions.get("model_type", "unknown"),
            "algorithm": predictions.get("algorithm", "unknown"),
            "feature_contributions": {},
            "summary": ""
        }
        
        # Get model metadata
        model_id = predictions.get("model_id")
        if model_id and model_id in self.model_metadata:
            metadata = self.model_metadata[model_id]
            
            # Add feature importance
            if "feature_importance" in metadata:
                explanations["feature_contributions"] = metadata["feature_importance"]
            
            # Generate summary
            top_features = sorted(
                explanations["feature_contributions"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if top_features:
                feature_names = [f[0] for f in top_features]
                explanations["summary"] = f"Predictions primarily influenced by: {', '.join(feature_names)}"
        
        return explanations
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about trained models
        
        Returns:
            Dictionary with model information
        """
        model_info = {}
        
        for model_id, metadata in self.model_metadata.items():
            model_info[model_id] = {
                "algorithm": metadata["config"].algorithm,
                "model_type": metadata["config"].model_type,
                "trained_at": metadata["trained_at"],
                "metrics": metadata["metrics"],
                "features": metadata["config"].features
            }
        
        return model_info
    
    # Private helper methods
    
    async def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in DataFrame"""
        # Numeric columns: fill with median
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col].fillna(df[col].median(), inplace=True)
        
        # Categorical columns: fill with mode
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            mode_value = df[col].mode()
            if not mode_value.empty:
                df[col].fillna(mode_value[0], inplace=True)
            else:
                df[col].fillna("unknown", inplace=True)
        
        return df
    
    async def _encode_categorical_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables"""
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        for col in categorical_cols:
            # Use label encoding for simplicity
            # In production, would use one-hot encoding for non-ordinal variables
            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                df[col] = self.encoders[col].fit_transform(df[col].astype(str))
            else:
                # Handle unseen categories
                df[col] = df[col].apply(
                    lambda x: self.encoders[col].transform([str(x)])[0]
                    if str(x) in self.encoders[col].classes_ else -1
                )
        
        return df
    
    async def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform feature engineering"""
        # Add polynomial features for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        # Add interaction features (limited to avoid explosion)
        if len(numeric_cols) >= 2:
            for i, col1 in enumerate(numeric_cols[:3]):  # Limit to first 3
                for col2 in numeric_cols[i+1:4]:
                    df[f"{col1}_x_{col2}"] = df[col1] * df[col2]
        
        # Add ratio features
        if len(numeric_cols) >= 2:
            for i, col1 in enumerate(numeric_cols[:2]):
                for col2 in numeric_cols[i+1:3]:
                    if (df[col2] != 0).all():
                        df[f"{col1}_div_{col2}"] = df[col1] / df[col2]
        
        return df
    
    async def _scale_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Scale features using StandardScaler"""
        scaler_id = "default"
        
        if scaler_id not in self.scalers:
            self.scalers[scaler_id] = StandardScaler()
            X_scaled = self.scalers[scaler_id].fit_transform(X)
        else:
            X_scaled = self.scalers[scaler_id].transform(X)
        
        return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
    
    async def _get_model(self, config: ModelConfig):
        """Get configured ML model"""
        if config.model_type == "regression":
            models = {
                "linear_regression": LinearRegression(),
                "ridge": Ridge(),
                "lasso": Lasso(),
                "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
                "decision_tree": DecisionTreeRegressor(random_state=42),
                "svr": SVR()
            }
        elif config.model_type == "classification":
            models = {
                "logistic_regression": LogisticRegression(random_state=42),
                "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
                "decision_tree": DecisionTreeClassifier(random_state=42),
                "svc": SVC(probability=True, random_state=42)
            }
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
        
        model = models.get(config.algorithm)
        if not model:
            # Default to random forest
            if config.model_type == "regression":
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            else:
