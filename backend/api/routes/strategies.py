from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from services.database import get_db
from models.strategy import Strategy, StrategyType
from models.user import User
from services.auth_service import get_current_user
from services.strategy_engine import (
    strategy_engine, MomentumStrategy, MeanReversionStrategy, MLBasedStrategy,
    TradingSignal, SignalType
)
from services.backtesting_engine import backtesting_engine, strategy_optimizer

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class StrategyCreate(BaseModel):
    name: str
    description: str
    strategy_type: StrategyType
    parameters: Dict[str, Any]
    is_active: bool = False

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str
    strategy_type: StrategyType
    parameters: Dict[str, Any]
    is_active: bool
    performance_metrics: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class BacktestRequest(BaseModel):
    strategy_id: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('symbols')
    def symbols_not_empty(cls, v):
        if not v:
            raise ValueError('symbols list cannot be empty')
        return v

class OptimizationRequest(BaseModel):
    strategy_type: StrategyType
    base_parameters: Dict[str, Any]
    parameter_ranges: Dict[str, List]
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    optimization_metric: str = "sharpe_ratio"
    
    @validator('optimization_metric')
    def valid_optimization_metric(cls, v):
        valid_metrics = [
            "total_return", "sharpe_ratio", "calmar_ratio", "sortino_ratio",
            "win_rate", "profit_factor", "max_drawdown"
        ]
        if v not in valid_metrics:
            raise ValueError(f'optimization_metric must be one of: {valid_metrics}')
        return v

@router.post("/", response_model=StrategyResponse)
async def create_strategy(
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new trading strategy"""
    try:
        # Create database record
        db_strategy = Strategy(
            user_id=current_user.id,
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            is_active=strategy.is_active
        )
        
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        
        # Register strategy in engine
        strategy_class_map = {
            StrategyType.MOMENTUM: MomentumStrategy,
            StrategyType.MEAN_REVERSION: MeanReversionStrategy,
            StrategyType.ML_BASED: MLBasedStrategy
        }
        
        if strategy.strategy_type in strategy_class_map:
            strategy_instance = strategy_class_map[strategy.strategy_type](
                str(db_strategy.id), strategy.parameters
            )
            strategy_engine.register_strategy(strategy_instance)
            
            if strategy.is_active:
                strategy_engine.activate_strategy(str(db_strategy.id))
        
        return StrategyResponse(
            id=str(db_strategy.id),
            name=db_strategy.name,
            description=db_strategy.description,
            strategy_type=db_strategy.strategy_type,
            parameters=db_strategy.parameters,
            is_active=db_strategy.is_active,
            performance_metrics={},
            created_at=db_strategy.created_at,
            updated_at=db_strategy.updated_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create strategy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create strategy"
        )

@router.get("/", response_model=List[StrategyResponse])
async def get_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's trading strategies"""
    try:
        query = db.query(Strategy).filter(Strategy.user_id == current_user.id)
        
        if active_only:
            query = query.filter(Strategy.is_active == True)
        
        strategies = query.offset(skip).limit(limit).all()
        
        result = []
        for strategy in strategies:
            # Get performance metrics from engine
            performance = strategy_engine.get_strategy_performance(str(strategy.id))
            
            result.append(StrategyResponse(
                id=str(strategy.id),
                name=strategy.name,
                description=strategy.description,
                strategy_type=strategy.strategy_type,
                parameters=strategy.parameters,
                is_active=strategy.is_active,
                performance_metrics=performance,
                created_at=strategy.created_at,
                updated_at=strategy.updated_at
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get strategies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategies"
        )

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Get performance metrics
        performance = strategy_engine.get_strategy_performance(strategy_id)
        
        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            is_active=strategy.is_active,
            performance_metrics=performance,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategy"
        )

@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    strategy_update: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Update fields
        update_data = strategy_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(strategy, field, value)
        
        db.commit()
        db.refresh(strategy)
        
        # Update strategy in engine
        if strategy_update.is_active is not None:
            if strategy_update.is_active:
                strategy_engine.activate_strategy(strategy_id)
            else:
                strategy_engine.deactivate_strategy(strategy_id)
        
        # Get performance metrics
        performance = strategy_engine.get_strategy_performance(strategy_id)
        
        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            is_active=strategy.is_active,
            performance_metrics=performance,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update strategy"
        )

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Deactivate and remove from engine
        strategy_engine.deactivate_strategy(strategy_id)
        
        # Delete from database
        db.delete(strategy)
        db.commit()
        
        return {"message": "Strategy deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete strategy"
        )

@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Activate in database
        strategy.is_active = True
        db.commit()
        
        # Activate in engine
        strategy_engine.activate_strategy(strategy_id)
        
        return {"message": "Strategy activated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate strategy"
        )

@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Deactivate in database
        strategy.is_active = False
        db.commit()
        
        # Deactivate in engine
        strategy_engine.deactivate_strategy(strategy_id)
        
        return {"message": "Strategy deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate strategy"
        )

@router.post("/{strategy_id}/backtest")
async def run_backtest(
    strategy_id: str,
    backtest_request: BacktestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run backtest for a strategy"""
    try:
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Create strategy instance for backtesting
        strategy_class_map = {
            StrategyType.MOMENTUM: MomentumStrategy,
            StrategyType.MEAN_REVERSION: MeanReversionStrategy,
            StrategyType.ML_BASED: MLBasedStrategy
        }
        
        if strategy.strategy_type not in strategy_class_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported strategy type for backtesting"
            )
        
        strategy_instance = strategy_class_map[strategy.strategy_type](
            strategy_id, strategy.parameters
        )
        
        # Configure backtesting engine
        backtesting_engine.initial_capital = backtest_request.initial_capital
        backtesting_engine.commission_rate = backtest_request.commission_rate
        
        # Run backtest
        results = await backtesting_engine.run_backtest(
            strategy_instance,
            backtest_request.symbols,
            backtest_request.start_date,
            backtest_request.end_date
        )
        
        return {
            "status": "success",
            "backtest_results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run backtest for strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run backtest"
        )

@router.post("/optimize")
async def optimize_strategy_parameters(
    optimization_request: OptimizationRequest,
    current_user: User = Depends(get_current_user)
):
    """Optimize strategy parameters"""
    try:
        # Map strategy type to class
        strategy_class_map = {
            StrategyType.MOMENTUM: MomentumStrategy,
            StrategyType.MEAN_REVERSION: MeanReversionStrategy,
            StrategyType.ML_BASED: MLBasedStrategy
        }
        
        if optimization_request.strategy_type not in strategy_class_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported strategy type for optimization"
            )
        
        strategy_class = strategy_class_map[optimization_request.strategy_type]
        
        # Run optimization
        results = await strategy_optimizer.optimize_parameters(
            strategy_class,
            optimization_request.base_parameters,
            optimization_request.parameter_ranges,
            optimization_request.symbols,
            optimization_request.start_date,
            optimization_request.end_date,
            optimization_request.optimization_metric
        )
        
        return {
            "status": "success",
            "optimization_results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize strategy parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize strategy parameters"
        )

@router.get("/engine/status")
async def get_strategy_engine_status(
    current_user: User = Depends(get_current_user)
):
    """Get strategy engine status"""
    try:
        all_strategies = strategy_engine.get_all_strategies()
        active_strategies = strategy_engine.active_strategies
        
        return {
            "total_strategies": len(all_strategies),
            "active_strategies": len(active_strategies),
            "strategy_details": all_strategies,
            "active_strategy_ids": active_strategies
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategy engine status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get strategy engine status"
        )

@router.get("/templates")
async def get_strategy_templates():
    """Get available strategy templates with default parameters"""
    try:
        templates = {
            "momentum": {
                "name": "Momentum Strategy",
                "description": "Buy when price momentum is strong, sell on momentum reversal",
                "strategy_type": StrategyType.MOMENTUM,
                "default_parameters": {
                    "lookback_period": 20,
                    "momentum_threshold": 0.02,
                    "stop_loss": 0.05,
                    "take_profit": 0.10,
                    "max_position_size": 0.05
                },
                "parameter_descriptions": {
                    "lookback_period": "Number of periods to calculate momentum",
                    "momentum_threshold": "Minimum momentum to trigger signal",
                    "stop_loss": "Stop loss percentage",
                    "take_profit": "Take profit percentage",
                    "max_position_size": "Maximum position size as fraction of portfolio"
                }
            },
            "mean_reversion": {
                "name": "Mean Reversion Strategy",
                "description": "Buy oversold securities, sell overbought securities",
                "strategy_type": StrategyType.MEAN_REVERSION,
                "default_parameters": {
                    "lookback_period": 20,
                    "bollinger_std": 2.0,
                    "rsi_oversold": 30,
                    "rsi_overbought": 70,
                    "max_position_size": 0.03
                },
                "parameter_descriptions": {
                    "lookback_period": "Period for moving average calculation",
                    "bollinger_std": "Standard deviations for Bollinger Bands",
                    "rsi_oversold": "RSI threshold for oversold condition",
                    "rsi_overbought": "RSI threshold for overbought condition",
                    "max_position_size": "Maximum position size as fraction of portfolio"
                }
            },
            "ml_based": {
                "name": "ML-Based Strategy",
                "description": "Use machine learning predictions for trading decisions",
                "strategy_type": StrategyType.ML_BASED,
                "default_parameters": {
                    "model_confidence_threshold": 0.6,
                    "prediction_horizon": "1d",
                    "max_position_size": 0.04,
                    "feature_importance_threshold": 0.1
                },
                "parameter_descriptions": {
                    "model_confidence_threshold": "Minimum model confidence to act on predictions",
                    "prediction_horizon": "Time horizon for predictions",
                    "max_position_size": "Maximum position size as fraction of portfolio",
                    "feature_importance_threshold": "Minimum feature importance to include in model"
                }
            }
        }
        
        return {
            "templates": templates
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategy templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get strategy templates"
        )