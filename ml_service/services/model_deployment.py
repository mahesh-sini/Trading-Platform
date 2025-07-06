"""
Model Deployment and Versioning System
Implements production model deployment with A/B testing and monitoring
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd

from .ml_engine import ml_engine, ModelType, PredictionTimeframe, PredictionResult
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

class DeploymentEnvironment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class ModelStatus(Enum):
    """Model deployment status"""
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    TESTING = "testing"  # A/B testing
    DEPRECATED = "deprecated"
    FAILED = "failed"

@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    environment: DeploymentEnvironment
    status: ModelStatus
    deployed_at: datetime
    performance_metrics: Dict[str, float]
    champion_model: bool = False  # For A/B testing
    traffic_percentage: float = 100.0  # Percentage of traffic
    health_status: str = "unknown"
    prediction_count: int = 0
    error_count: int = 0
    avg_latency: float = 0.0
    last_prediction: Optional[datetime] = None

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_id: str
    champion_model: str
    challenger_model: str
    traffic_split: float  # Percentage for challenger (0-100)
    start_date: datetime
    end_date: datetime
    success_metric: str  # 'accuracy', 'precision', 'sharpe_ratio'
    min_sample_size: int = 1000
    confidence_level: float = 0.95

class ModelDeploymentService:
    """Production model deployment with versioning and A/B testing"""
    
    def __init__(self):
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
        # Model registry
        self.model_versions: Dict[str, ModelVersion] = {}
        self.ab_tests: Dict[str, ABTestConfig] = {}
        
        # Environment directories
        for env in DeploymentEnvironment:
            env_dir = self.models_dir / env.value
            env_dir.mkdir(exist_ok=True)
        
        # Registry files
        self.registry_file = self.models_dir / "model_registry.json"
        self.ab_test_file = self.models_dir / "ab_tests.json"
        
        # Monitoring task
        self._monitoring_task = None
        
        # Load existing data
        self._load_registry()
        self._load_ab_tests()
    
    async def initialize(self):
        """Initialize deployment service"""
        try:
            # Start health monitoring
            self._monitoring_task = asyncio.create_task(self._health_monitor())
            
            # Load production models
            await self._load_production_models()
            
            logger.info("Model deployment service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize deployment service: {e}")
            raise
    
    async def deploy_model(
        self,
        model_id: str,
        symbol: str,
        timeframe: PredictionTimeframe,
        model_type: ModelType,
        environment: DeploymentEnvironment,
        performance_threshold: float = 0.6
    ) -> bool:
        """Deploy model to specified environment"""
        try:
            # Generate version
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            deployment_id = f"{model_id}_{environment.value}_{version}"
            
            logger.info(f"Deploying model {model_id} to {environment.value}")
            
            # Validate model exists
            model_key = f"{symbol}_{timeframe.value}_{model_type.value}"
            if model_key not in ml_engine.models:
                raise ValueError(f"Model {model_key} not found or not trained")
            
            model = ml_engine.models[model_key]
            
            # Validate performance meets threshold
            accuracy = model.performance_metrics.get('directional_accuracy', 0)
            if accuracy < performance_threshold:
                raise ValueError(f"Model accuracy {accuracy} below threshold {performance_threshold}")
            
            # Create model version record
            model_version = ModelVersion(
                model_id=deployment_id,
                version=version,
                environment=environment,
                status=ModelStatus.DEPLOYED,
                deployed_at=datetime.now(),
                performance_metrics=model.performance_metrics.copy(),
                champion_model=True,  # New deployments start as champion
                traffic_percentage=100.0
            )
            
            # Copy model to environment directory
            env_dir = self.models_dir / environment.value
            model_path = env_dir / deployment_id
            model.save_model(str(model_path))
            
            # Register deployment
            self.model_versions[deployment_id] = model_version
            self._save_registry()
            
            logger.info(f"Model {model_id} deployed successfully to {environment.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy model {model_id}: {e}")
            return False
    
    async def start_ab_test(
        self,
        champion_model_id: str,
        challenger_model_id: str,
        traffic_split: float,
        duration_days: int = 7,
        success_metric: str = "directional_accuracy"
    ) -> str:
        """Start A/B test between two models"""
        try:
            # Validate models exist and are deployed
            if champion_model_id not in self.model_versions:
                raise ValueError(f"Champion model {champion_model_id} not found")
            
            if challenger_model_id not in self.model_versions:
                raise ValueError(f"Challenger model {challenger_model_id} not found")
            
            champion = self.model_versions[champion_model_id]
            challenger = self.model_versions[challenger_model_id]
            
            if champion.environment != challenger.environment:
                raise ValueError("Models must be in same environment for A/B testing")
            
            # Create A/B test configuration
            test_id = f"ab_test_{int(datetime.now().timestamp())}"
            
            ab_test = ABTestConfig(
                test_id=test_id,
                champion_model=champion_model_id,
                challenger_model=challenger_model_id,
                traffic_split=traffic_split,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=duration_days),
                success_metric=success_metric
            )
            
            # Update model traffic allocation
            champion.traffic_percentage = 100.0 - traffic_split
            champion.champion_model = True
            challenger.traffic_percentage = traffic_split
            challenger.champion_model = False
            challenger.status = ModelStatus.TESTING
            
            # Register A/B test
            self.ab_tests[test_id] = ab_test
            
            # Save state
            self._save_registry()
            self._save_ab_tests()
            
            logger.info(f"A/B test {test_id} started: {champion_model_id} vs {challenger_model_id}")
            return test_id
            
        except Exception as e:
            logger.error(f"Failed to start A/B test: {e}")
            raise
    
    async def predict_with_deployment(
        self,
        symbol: str,
        timeframe: PredictionTimeframe,
        features: Dict[str, Any],
        environment: DeploymentEnvironment = DeploymentEnvironment.PRODUCTION
    ) -> PredictionResult:
        """Make prediction using deployed models with A/B testing"""
        try:
            start_time = datetime.now()
            
            # Find deployed models for symbol/timeframe in environment
            deployed_models = [
                mv for mv in self.model_versions.values()
                if mv.environment == environment 
                and mv.status in [ModelStatus.DEPLOYED, ModelStatus.TESTING]
                and mv.model_id.startswith(f"{symbol}_{timeframe.value}")
            ]
            
            if not deployed_models:
                raise ValueError(f"No deployed models for {symbol} {timeframe.value} in {environment.value}")
            
            # Select model based on A/B test traffic allocation
            selected_model = await self._select_model_for_prediction(deployed_models)
            
            # Load model if not in memory
            model_key = f"{symbol}_{timeframe.value}_{selected_model.model_id.split('_')[-2]}"
            if model_key not in ml_engine.models:
                await self._load_model_to_memory(selected_model)
            
            # Make prediction using ML engine
            from .ml_engine import PredictionRequest
            request = PredictionRequest(
                symbol=symbol,
                timeframe=timeframe,
                horizon="1d",  # Default horizon
                features=features
            )
            
            result = await ml_engine.predict(request)
            
            # Update deployment metrics
            prediction_time = (datetime.now() - start_time).total_seconds()
            selected_model.prediction_count += 1
            selected_model.last_prediction = datetime.now()
            selected_model.avg_latency = (
                (selected_model.avg_latency * (selected_model.prediction_count - 1) + prediction_time)
                / selected_model.prediction_count
            )
            
            # Add deployment info to result
            result.model_version = selected_model.version
            
            self._save_registry()
            
            return result
            
        except Exception as e:
            if 'selected_model' in locals():
                selected_model.error_count += 1
            logger.error(f"Prediction failed: {e}")
            raise
    
    async def _select_model_for_prediction(self, deployed_models: List[ModelVersion]) -> ModelVersion:
        """Select model based on A/B test traffic allocation"""
        try:
            # Check if there's an active A/B test
            active_tests = [
                test for test in self.ab_tests.values()
                if test.start_date <= datetime.now() <= test.end_date
            ]
            
            if active_tests:
                # Use A/B test traffic allocation
                test = active_tests[0]  # Assume one test at a time
                
                champion = next((m for m in deployed_models if m.model_id == test.champion_model), None)
                challenger = next((m for m in deployed_models if m.model_id == test.challenger_model), None)
                
                if champion and challenger:
                    # Random selection based on traffic split
                    import random
                    if random.random() * 100 < test.traffic_split:
                        return challenger
                    else:
                        return champion
            
            # Default: return champion model (highest performance)
            champion_models = [m for m in deployed_models if m.champion_model]
            if champion_models:
                return champion_models[0]
            
            # Fallback: return most recent deployment
            return max(deployed_models, key=lambda x: x.deployed_at)
            
        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            # Return first available model as fallback
            return deployed_models[0]
    
    async def evaluate_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Evaluate A/B test results"""
        try:
            if test_id not in self.ab_tests:
                raise ValueError(f"A/B test {test_id} not found")
            
            test = self.ab_tests[test_id]
            champion = self.model_versions[test.champion_model]
            challenger = self.model_versions[test.challenger_model]
            
            # Calculate metrics
            champion_metric = champion.performance_metrics.get(test.success_metric, 0)
            challenger_metric = challenger.performance_metrics.get(test.success_metric, 0)
            
            # Simple statistical significance test (would use proper stats in production)
            improvement = (challenger_metric - champion_metric) / champion_metric * 100
            is_significant = abs(improvement) > 5.0  # 5% improvement threshold
            
            # Determine winner
            winner = "challenger" if challenger_metric > champion_metric else "champion"
            
            results = {
                'test_id': test_id,
                'champion_model': test.champion_model,
                'challenger_model': test.challenger_model,
                'champion_metric': champion_metric,
                'challenger_metric': challenger_metric,
                'improvement_percent': improvement,
                'is_significant': is_significant,
                'winner': winner,
                'champion_predictions': champion.prediction_count,
                'challenger_predictions': challenger.prediction_count,
                'test_duration_days': (datetime.now() - test.start_date).days
            }
            
            logger.info(f"A/B test {test_id} evaluation completed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to evaluate A/B test {test_id}: {e}")
            raise
    
    async def promote_challenger(self, test_id: str) -> bool:
        """Promote challenger to champion after successful A/B test"""
        try:
            if test_id not in self.ab_tests:
                raise ValueError(f"A/B test {test_id} not found")
            
            test = self.ab_tests[test_id]
            champion = self.model_versions[test.champion_model]
            challenger = self.model_versions[test.challenger_model]
            
            # Promote challenger
            challenger.champion_model = True
            challenger.traffic_percentage = 100.0
            challenger.status = ModelStatus.DEPLOYED
            
            # Demote champion
            champion.champion_model = False
            champion.traffic_percentage = 0.0
            champion.status = ModelStatus.DEPRECATED
            
            # Mark test as completed
            test.end_date = datetime.now()
            
            # Save state
            self._save_registry()
            self._save_ab_tests()
            
            logger.info(f"Challenger {test.challenger_model} promoted to champion")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote challenger: {e}")
            return False
    
    async def rollback_deployment(self, model_id: str) -> bool:
        """Rollback to previous model version"""
        try:
            if model_id not in self.model_versions:
                raise ValueError(f"Model {model_id} not found")
            
            current_model = self.model_versions[model_id]
            environment = current_model.environment
            
            # Find previous version in same environment
            same_env_models = [
                mv for mv in self.model_versions.values()
                if mv.environment == environment and mv.model_id != model_id
            ]
            
            if not same_env_models:
                raise ValueError("No previous version available for rollback")
            
            # Get most recent previous deployment
            previous_model = max(same_env_models, key=lambda x: x.deployed_at)
            
            # Rollback
            current_model.status = ModelStatus.DEPRECATED
            current_model.champion_model = False
            current_model.traffic_percentage = 0.0
            
            previous_model.status = ModelStatus.DEPLOYED
            previous_model.champion_model = True
            previous_model.traffic_percentage = 100.0
            previous_model.deployed_at = datetime.now()  # Update rollback time
            
            self._save_registry()
            
            logger.info(f"Rolled back {model_id} to {previous_model.model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback model {model_id}: {e}")
            return False
    
    async def _load_model_to_memory(self, model_version: ModelVersion):
        """Load model to ML engine memory"""
        try:
            env_dir = self.models_dir / model_version.environment.value
            model_path = env_dir / model_version.model_id
            
            if not model_path.exists():
                raise ValueError(f"Model files not found: {model_path}")
            
            # Create model instance and load
            from .ml_engine import MLModel
            model = MLModel(ModelType.RANDOM_FOREST, "", PredictionTimeframe.INTRADAY)
            model.load_model(str(model_path))
            
            # Add to ML engine
            model_key = f"{model.symbol}_{model.timeframe.value}_{model.model_type.value}"
            ml_engine.models[model_key] = model
            
            logger.info(f"Loaded model {model_version.model_id} to memory")
            
        except Exception as e:
            logger.error(f"Failed to load model to memory: {e}")
            raise
    
    async def _load_production_models(self):
        """Load all production models to memory"""
        try:
            production_models = [
                mv for mv in self.model_versions.values()
                if mv.environment == DeploymentEnvironment.PRODUCTION
                and mv.status == ModelStatus.DEPLOYED
            ]
            
            for model_version in production_models:
                try:
                    await self._load_model_to_memory(model_version)
                except Exception as e:
                    logger.error(f"Failed to load production model {model_version.model_id}: {e}")
                    model_version.health_status = "load_failed"
            
            logger.info(f"Loaded {len(production_models)} production models")
            
        except Exception as e:
            logger.error(f"Failed to load production models: {e}")
    
    async def _health_monitor(self):
        """Monitor health of deployed models"""
        while True:
            try:
                for model_version in self.model_versions.values():
                    if model_version.status in [ModelStatus.DEPLOYED, ModelStatus.TESTING]:
                        await self._check_model_health(model_version)
                
                # Check A/B tests
                await self._check_ab_tests()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_model_health(self, model_version: ModelVersion):
        """Check health of specific model version"""
        try:
            # Check prediction recency
            if model_version.last_prediction:
                age = datetime.now() - model_version.last_prediction
                if age > timedelta(hours=2):
                    model_version.health_status = "stale_predictions"
                    return
            
            # Check error rate
            if model_version.prediction_count > 0:
                error_rate = model_version.error_count / model_version.prediction_count
                if error_rate > 0.1:  # 10% error threshold
                    model_version.health_status = "high_error_rate"
                    return
            
            # Check latency
            if model_version.avg_latency > 1.0:  # 1 second threshold
                model_version.health_status = "slow_predictions"
                return
            
            model_version.health_status = "healthy"
            
        except Exception as e:
            model_version.health_status = f"health_check_error: {str(e)}"
    
    async def _check_ab_tests(self):
        """Check active A/B tests"""
        try:
            current_time = datetime.now()
            
            for test_id, test in self.ab_tests.items():
                if test.start_date <= current_time <= test.end_date:
                    # Check if test has enough samples
                    champion = self.model_versions[test.champion_model]
                    challenger = self.model_versions[test.challenger_model]
                    
                    total_predictions = champion.prediction_count + challenger.prediction_count
                    
                    if total_predictions >= test.min_sample_size:
                        # Evaluate test
                        results = await self.evaluate_ab_test(test_id)
                        logger.info(f"A/B test {test_id} interim results: {results}")
                
                elif current_time > test.end_date:
                    # Auto-evaluate completed tests
                    results = await self.evaluate_ab_test(test_id)
                    logger.info(f"A/B test {test_id} completed: {results}")
            
        except Exception as e:
            logger.error(f"Error checking A/B tests: {e}")
    
    def _load_registry(self):
        """Load model registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                
                for model_id, model_data in data.items():
                    # Convert strings back to objects
                    model_data['environment'] = DeploymentEnvironment(model_data['environment'])
                    model_data['status'] = ModelStatus(model_data['status'])
                    model_data['deployed_at'] = datetime.fromisoformat(model_data['deployed_at'])
                    
                    if model_data.get('last_prediction'):
                        model_data['last_prediction'] = datetime.fromisoformat(model_data['last_prediction'])
                    
                    self.model_versions[model_id] = ModelVersion(**model_data)
                
                logger.info(f"Loaded {len(self.model_versions)} model versions")
                
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save model registry to disk"""
        try:
            data = {}
            for model_id, model_version in self.model_versions.items():
                model_dict = asdict(model_version)
                model_dict['environment'] = model_version.environment.value
                model_dict['status'] = model_version.status.value
                model_dict['deployed_at'] = model_version.deployed_at.isoformat()
                
                if model_version.last_prediction:
                    model_dict['last_prediction'] = model_version.last_prediction.isoformat()
                
                data[model_id] = model_dict
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _load_ab_tests(self):
        """Load A/B tests from disk"""
        try:
            if self.ab_test_file.exists():
                with open(self.ab_test_file, 'r') as f:
                    data = json.load(f)
                
                for test_id, test_data in data.items():
                    test_data['start_date'] = datetime.fromisoformat(test_data['start_date'])
                    test_data['end_date'] = datetime.fromisoformat(test_data['end_date'])
                    
                    self.ab_tests[test_id] = ABTestConfig(**test_data)
                
                logger.info(f"Loaded {len(self.ab_tests)} A/B tests")
                
        except Exception as e:
            logger.error(f"Failed to load A/B tests: {e}")
    
    def _save_ab_tests(self):
        """Save A/B tests to disk"""
        try:
            data = {}
            for test_id, ab_test in self.ab_tests.items():
                test_dict = asdict(ab_test)
                test_dict['start_date'] = ab_test.start_date.isoformat()
                test_dict['end_date'] = ab_test.end_date.isoformat()
                
                data[test_id] = test_dict
            
            with open(self.ab_test_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save A/B tests: {e}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get deployment status summary"""
        status = {
            'total_deployments': len(self.model_versions),
            'by_environment': {},
            'by_status': {},
            'active_ab_tests': 0,
            'healthy_models': 0,
            'error_models': 0
        }
        
        # Count by environment and status
        for mv in self.model_versions.values():
            env = mv.environment.value
            stat = mv.status.value
            
            status['by_environment'][env] = status['by_environment'].get(env, 0) + 1
            status['by_status'][stat] = status['by_status'].get(stat, 0) + 1
            
            if mv.health_status == "healthy":
                status['healthy_models'] += 1
            elif "error" in mv.health_status:
                status['error_models'] += 1
        
        # Count active A/B tests
        current_time = datetime.now()
        status['active_ab_tests'] = sum(
            1 for test in self.ab_tests.values()
            if test.start_date <= current_time <= test.end_date
        )
        
        return status
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self._monitoring_task:
                self._monitoring_task.cancel()
            
            logger.info("Model deployment service cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Global deployment service instance
model_deployment_service = ModelDeploymentService()