"""
Options Trading Service
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json

from app.models.options import (
    OptionsContract, OptionsPosition, OptionsOrder, OptionsStrategy,
    OptionsChain, OptionsPricing, OptionType, OptionStatus
)
from app.models.user import User
from app.models.organization import Organization
from app.services.options_pricing import OptionsPricingService, OptionsStrategyCalculator
from app.services.rbac import RBACService
from app.core.config import settings


class OptionsContractService:
    """Service for managing options contracts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = OptionsPricingService()
    
    async def get_options_chain(self, underlying_symbol: str, 
                              expiration_date: Optional[datetime] = None) -> List[OptionsContract]:
        """Get options chain for a symbol"""
        query = select(OptionsContract).where(
            OptionsContract.underlying_symbol == underlying_symbol,
            OptionsContract.status == OptionStatus.ACTIVE
        )
        
        if expiration_date:
            query = query.where(OptionsContract.expiration_date == expiration_date)
        else:
            # Get next 4 expiration dates
            query = query.where(OptionsContract.expiration_date >= datetime.now())
        
        query = query.order_by(
            OptionsContract.expiration_date,
            OptionsContract.option_type,
            OptionsContract.strike_price
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_contract_by_symbol(self, symbol: str) -> Optional[OptionsContract]:
        """Get options contract by symbol"""
        result = await self.db.execute(
            select(OptionsContract).where(OptionsContract.symbol == symbol)
        )
        return result.scalar_one_or_none()
    
    async def create_contract(self, contract_data: Dict[str, Any]) -> OptionsContract:
        """Create a new options contract"""
        contract = OptionsContract(**contract_data)
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract
    
    async def update_contract_pricing(self, contract_id: str, 
                                    market_data: Dict[str, Any]) -> OptionsContract:
        """Update options contract with latest market data"""
        contract = await self.db.get(OptionsContract, contract_id)
        if not contract:
            return None
        
        # Update market data fields
        for field, value in market_data.items():
            if hasattr(contract, field):
                setattr(contract, field, value)
        
        # Calculate theoretical pricing if we have underlying price
        if 'underlying_price' in market_data:
            self.pricing_service.update_contract_pricing(
                contract, market_data['underlying_price']
            )
        
        contract.last_trade_time = datetime.now()
        await self.db.commit()
        await self.db.refresh(contract)
        
        return contract
    
    async def get_expiration_dates(self, underlying_symbol: str) -> List[datetime]:
        """Get all available expiration dates for a symbol"""
        result = await self.db.execute(
            select(OptionsContract.expiration_date)
            .where(
                OptionsContract.underlying_symbol == underlying_symbol,
                OptionsContract.status == OptionStatus.ACTIVE,
                OptionsContract.expiration_date >= datetime.now()
            )
            .distinct()
            .order_by(OptionsContract.expiration_date)
        )
        return [row[0] for row in result.fetchall()]


class OptionsPositionService:
    """Service for managing options positions"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = OptionsPricingService()
        self.rbac_service = RBACService(db)
    
    async def get_user_positions(self, user_id: str, organization_id: str,
                               portfolio_id: Optional[str] = None,
                               active_only: bool = True) -> List[OptionsPosition]:
        """Get options positions for a user"""
        query = select(OptionsPosition).options(
            selectinload(OptionsPosition.contract)
        ).where(
            OptionsPosition.user_id == user_id,
            OptionsPosition.organization_id == organization_id
        )
        
        if portfolio_id:
            query = query.where(OptionsPosition.portfolio_id == portfolio_id)
        
        if active_only:
            query = query.where(OptionsPosition.is_active == True)
        
        query = query.order_by(desc(OptionsPosition.opened_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_position(self, position_data: Dict[str, Any]) -> OptionsPosition:
        """Create a new options position"""
        position = OptionsPosition(**position_data)
        self.db.add(position)
        await self.db.commit()
        await self.db.refresh(position)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=position_data['organization_id'],
            user_id=position_data['user_id'],
            event_type="options_position_opened",
            event_category="trading",
            action="create_position",
            resource_type="options_position",
            resource_id=str(position.id),
            details={
                "contract_symbol": position.contract.symbol,
                "quantity": position_data['quantity'],
                "cost_basis": float(position_data['cost_basis'])
            }
        )
        
        return position
    
    async def update_position(self, position_id: str, updates: Dict[str, Any],
                            updated_by: str) -> Optional[OptionsPosition]:
        """Update an options position"""
        position = await self.db.get(OptionsPosition, position_id)
        if not position:
            return None
        
        old_values = {
            "quantity": position.quantity,
            "market_value": float(position.market_value) if position.market_value else None
        }
        
        for field, value in updates.items():
            if hasattr(position, field):
                setattr(position, field, value)
        
        position.last_updated = datetime.now()
        await self.db.commit()
        await self.db.refresh(position)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=position.organization_id,
            user_id=updated_by,
            event_type="options_position_updated",
            event_category="trading",
            action="update_position",
            resource_type="options_position",
            resource_id=str(position.id),
            old_values=old_values,
            new_values=updates
        )
        
        return position
    
    async def close_position(self, position_id: str, closed_by: str,
                           closing_price: Decimal) -> Optional[OptionsPosition]:
        """Close an options position"""
        position = await self.db.get(OptionsPosition, position_id)
        if not position:
            return None
        
        # Calculate final P&L
        if position.quantity > 0:  # Long position
            final_pnl = (closing_price - position.average_price) * position.quantity * 100
        else:  # Short position
            final_pnl = (position.average_price - closing_price) * abs(position.quantity) * 100
        
        position.is_active = False
        position.closed_at = datetime.now()
        position.unrealized_pnl = final_pnl
        
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=position.organization_id,
            user_id=closed_by,
            event_type="options_position_closed",
            event_category="trading",
            action="close_position",
            resource_type="options_position",
            resource_id=str(position.id),
            details={
                "final_pnl": float(final_pnl),
                "closing_price": float(closing_price)
            }
        )
        
        return position
    
    async def calculate_position_greeks(self, position: OptionsPosition,
                                     underlying_price: float) -> Dict[str, float]:
        """Calculate Greeks for a position"""
        if not position.contract:
            return {}
        
        # Get contract quantity (negative for short positions)
        quantity = position.quantity
        
        # Calculate individual Greeks from contract
        contract_greeks = {
            'delta': float(position.contract.delta or 0),
            'gamma': float(position.contract.gamma or 0),
            'theta': float(position.contract.theta or 0),
            'vega': float(position.contract.vega or 0),
            'rho': float(position.contract.rho or 0)
        }
        
        # Scale by position size (multiply by 100 for per-share basis)
        position_greeks = {
            'delta': contract_greeks['delta'] * quantity * 100,
            'gamma': contract_greeks['gamma'] * quantity * 100,
            'theta': contract_greeks['theta'] * quantity * 100,
            'vega': contract_greeks['vega'] * quantity * 100,
            'rho': contract_greeks['rho'] * quantity * 100
        }
        
        return position_greeks


class OptionsOrderService:
    """Service for managing options orders"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rbac_service = RBACService(db)
    
    async def place_order(self, order_data: Dict[str, Any]) -> OptionsOrder:
        """Place an options order"""
        # Generate order ID
        order_data['order_id'] = f"OPT_{uuid.uuid4().hex[:12].upper()}"
        order_data['placed_at'] = datetime.now()
        
        order = OptionsOrder(**order_data)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=order_data['organization_id'],
            user_id=order_data['user_id'],
            event_type="options_order_placed",
            event_category="trading",
            action="place_order",
            resource_type="options_order",
            resource_id=str(order.id),
            details={
                "contract_symbol": order.contract.symbol,
                "side": order_data['side'],
                "quantity": order_data['quantity'],
                "order_type": order_data['order_type']
            }
        )
        
        return order
    
    async def get_user_orders(self, user_id: str, organization_id: str,
                            status: Optional[str] = None,
                            limit: int = 100) -> List[OptionsOrder]:
        """Get options orders for a user"""
        query = select(OptionsOrder).options(
            selectinload(OptionsOrder.contract)
        ).where(
            OptionsOrder.user_id == user_id,
            OptionsOrder.organization_id == organization_id
        )
        
        if status:
            query = query.where(OptionsOrder.status == status)
        
        query = query.order_by(desc(OptionsOrder.placed_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def cancel_order(self, order_id: str, cancelled_by: str) -> Optional[OptionsOrder]:
        """Cancel an options order"""
        order = await self.db.get(OptionsOrder, order_id)
        if not order or order.status not in ['pending', 'partial']:
            return None
        
        order.status = 'cancelled'
        order.cancelled_at = datetime.now()
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=order.organization_id,
            user_id=cancelled_by,
            event_type="options_order_cancelled",
            event_category="trading",
            action="cancel_order",
            resource_type="options_order",
            resource_id=str(order.id)
        )
        
        return order
    
    async def fill_order(self, order_id: str, fill_data: Dict[str, Any]) -> Optional[OptionsOrder]:
        """Fill an options order (simulate execution)"""
        order = await self.db.get(OptionsOrder, order_id)
        if not order or order.status not in ['pending', 'partial']:
            return None
        
        fill_quantity = fill_data.get('quantity', 0)
        fill_price = fill_data.get('price', 0)
        
        # Update order
        order.filled_quantity += fill_quantity
        order.remaining_quantity = order.quantity - order.filled_quantity
        
        if order.remaining_quantity <= 0:
            order.status = 'filled'
            order.filled_at = datetime.now()
        else:
            order.status = 'partial'
        
        order.filled_price = Decimal(str(fill_price))
        order.total_cost = order.filled_quantity * order.filled_price * 100  # Per share basis
        
        await self.db.commit()
        
        # Create or update position
        await self._update_position_from_fill(order, fill_quantity, fill_price)
        
        return order
    
    async def _update_position_from_fill(self, order: OptionsOrder, 
                                       fill_quantity: int, fill_price: float):
        """Update or create position from order fill"""
        # Find existing position
        result = await self.db.execute(
            select(OptionsPosition).where(
                OptionsPosition.user_id == order.user_id,
                OptionsPosition.portfolio_id == order.portfolio_id,
                OptionsPosition.contract_id == order.contract_id,
                OptionsPosition.is_active == True
            )
        )
        position = result.scalar_one_or_none()
        
        if not position:
            # Create new position
            position_data = {
                'organization_id': order.organization_id,
                'user_id': order.user_id,
                'portfolio_id': order.portfolio_id,
                'contract_id': order.contract_id,
                'quantity': fill_quantity if order.side.startswith('buy') else -fill_quantity,
                'average_price': Decimal(str(fill_price)),
                'cost_basis': Decimal(str(fill_quantity * fill_price * 100))
            }
            
            position_service = OptionsPositionService(self.db)
            await position_service.create_position(position_data)
        else:
            # Update existing position
            if order.side.startswith('buy'):
                new_quantity = position.quantity + fill_quantity
            else:
                new_quantity = position.quantity - fill_quantity
            
            if new_quantity == 0:
                # Position closed
                position.is_active = False
                position.closed_at = datetime.now()
            else:
                # Update average price and cost basis
                total_cost = (position.quantity * position.average_price * 100 + 
                            fill_quantity * fill_price * 100)
                position.quantity = new_quantity
                position.average_price = total_cost / (new_quantity * 100)
                position.cost_basis = total_cost
            
            await self.db.commit()


class OptionsStrategyService:
    """Service for managing options strategies"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = OptionsPricingService()
        self.strategy_calculator = OptionsStrategyCalculator(self.pricing_service)
        self.rbac_service = RBACService(db)
    
    async def create_strategy(self, strategy_data: Dict[str, Any]) -> OptionsStrategy:
        """Create a new options strategy"""
        strategy = OptionsStrategy(**strategy_data)
        self.db.add(strategy)
        await self.db.commit()
        await self.db.refresh(strategy)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=strategy_data['organization_id'],
            user_id=strategy_data['user_id'],
            event_type="options_strategy_created",
            event_category="trading",
            action="create_strategy",
            resource_type="options_strategy",
            resource_id=str(strategy.id),
            details={
                "strategy_type": strategy_data['strategy_type'],
                "underlying_symbol": strategy_data['underlying_symbol']
            }
        )
        
        return strategy
    
    async def get_user_strategies(self, user_id: str, organization_id: str) -> List[OptionsStrategy]:
        """Get options strategies for a user"""
        result = await self.db.execute(
            select(OptionsStrategy).where(
                OptionsStrategy.user_id == user_id,
                OptionsStrategy.organization_id == organization_id,
                OptionsStrategy.status == 'active'
            ).order_by(desc(OptionsStrategy.created_at))
        )
        return result.scalars().all()
    
    def create_covered_call_strategy(self, underlying_symbol: str, 
                                   stock_quantity: int, call_strike: float,
                                   call_expiration: datetime) -> Dict[str, Any]:
        """Create a covered call strategy definition"""
        return {
            'strategy_type': 'covered_call',
            'underlying_symbol': underlying_symbol,
            'legs': [
                {
                    'option_type': 'stock',
                    'side': 'long',
                    'quantity': stock_quantity,
                    'symbol': underlying_symbol
                },
                {
                    'option_type': 'call',
                    'side': 'short',
                    'quantity': stock_quantity // 100,  # Options are per 100 shares
                    'strike_price': call_strike,
                    'expiration_date': call_expiration.isoformat()
                }
            ],
            'market_outlook': 'neutral_bullish',
            'description': f'Covered call on {stock_quantity} shares of {underlying_symbol}'
        }
    
    def create_protective_put_strategy(self, underlying_symbol: str,
                                     stock_quantity: int, put_strike: float,
                                     put_expiration: datetime) -> Dict[str, Any]:
        """Create a protective put strategy definition"""
        return {
            'strategy_type': 'protective_put',
            'underlying_symbol': underlying_symbol,
            'legs': [
                {
                    'option_type': 'stock',
                    'side': 'long',
                    'quantity': stock_quantity,
                    'symbol': underlying_symbol
                },
                {
                    'option_type': 'put',
                    'side': 'long',
                    'quantity': stock_quantity // 100,
                    'strike_price': put_strike,
                    'expiration_date': put_expiration.isoformat()
                }
            ],
            'market_outlook': 'bullish',
            'description': f'Protective put on {stock_quantity} shares of {underlying_symbol}'
        }
    
    def create_iron_condor_strategy(self, underlying_symbol: str,
                                  put_strike_short: float, put_strike_long: float,
                                  call_strike_short: float, call_strike_long: float,
                                  expiration: datetime) -> Dict[str, Any]:
        """Create an iron condor strategy definition"""
        return {
            'strategy_type': 'iron_condor',
            'underlying_symbol': underlying_symbol,
            'legs': [
                {
                    'option_type': 'put',
                    'side': 'long',
                    'quantity': 1,
                    'strike_price': put_strike_long,
                    'expiration_date': expiration.isoformat()
                },
                {
                    'option_type': 'put',
                    'side': 'short',
                    'quantity': 1,
                    'strike_price': put_strike_short,
                    'expiration_date': expiration.isoformat()
                },
                {
                    'option_type': 'call',
                    'side': 'short',
                    'quantity': 1,
                    'strike_price': call_strike_short,
                    'expiration_date': expiration.isoformat()
                },
                {
                    'option_type': 'call',
                    'side': 'long',
                    'quantity': 1,
                    'strike_price': call_strike_long,
                    'expiration_date': expiration.isoformat()
                }
            ],
            'market_outlook': 'neutral',
            'description': f'Iron condor on {underlying_symbol} with {put_strike_short}/{call_strike_short} short strikes'
        }
    
    async def calculate_strategy_metrics(self, strategy: OptionsStrategy,
                                       underlying_price: float) -> Dict[str, Any]:
        """Calculate risk metrics for a strategy"""
        legs = strategy.legs
        
        # Calculate payoff diagram
        price_range = (underlying_price * 0.8, underlying_price * 1.2)
        payoff_diagram = self.strategy_calculator.calculate_payoff_diagram(
            legs, price_range
        )
        
        # Find breakeven points
        breakeven_points = self.strategy_calculator.find_breakeven_points(payoff_diagram)
        
        # Calculate max profit and loss
        max_profit, max_loss = self.strategy_calculator.calculate_max_profit_loss(payoff_diagram)
        
        # Calculate Greeks
        greeks = self.strategy_calculator.calculate_strategy_greeks(legs)
        
        return {
            'payoff_diagram': payoff_diagram,
            'breakeven_points': breakeven_points,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'greeks': {
                'delta': greeks.delta,
                'gamma': greeks.gamma,
                'theta': greeks.theta,
                'vega': greeks.vega,
                'rho': greeks.rho
            }
        }