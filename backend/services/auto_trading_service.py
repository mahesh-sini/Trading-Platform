import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from models.user import User
from models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan
from models.broker import BrokerAccount, BrokerAccountStatus
from models.trade import Trade, OrderStatus, OrderSide
from models.auto_trade import AutoTrade, AutoTradeStatus, AutoTradeReason
from services.database import AsyncSessionLocal
from services.strategy_engine import strategy_engine, TradingSignal
from services.broker_service import trading_service as broker_service
from services.ml_service_client import ml_service_client
from services.market_data_client import market_data_client
from services.risk_management import risk_manager
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

class AutoTradingMode(Enum):
    DISABLED = "disabled"
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

@dataclass
class MarketHours:
    open_time: time
    close_time: time
    timezone: str

class AutoTradingService:
    """Core automatic trading service that executes AI-powered trades"""
    
    def __init__(self):
        self.is_running = False
        self.active_sessions = {}  # user_id -> trading session
        self.market_hours = {
            "NSE": MarketHours(
                open_time=time(9, 15),  # 9:15 AM IST
                close_time=time(15, 30),  # 3:30 PM IST
                timezone="Asia/Kolkata"
            ),
            "BSE": MarketHours(
                open_time=time(9, 15),  # 9:15 AM IST
                close_time=time(15, 30),  # 3:30 PM IST
                timezone="Asia/Kolkata"
            )
        }
        
    async def start_service(self):
        """Start the automatic trading service"""
        if self.is_running:
            logger.warning("Auto trading service already running")
            return
            
        self.is_running = True
        logger.info("🚀 Starting Automatic Trading Service")
        
        # Start main trading loop
        asyncio.create_task(self._main_trading_loop())
        
        # Start market hours monitor
        asyncio.create_task(self._market_hours_monitor())
        
        logger.info("✅ Automatic Trading Service started successfully")
    
    async def stop_service(self):
        """Stop the automatic trading service"""
        self.is_running = False
        
        # Stop all active trading sessions
        for user_id, session in self.active_sessions.items():
            await self._stop_user_trading_session(user_id)
            
        logger.info("🛑 Automatic Trading Service stopped")
    
    async def _main_trading_loop(self):
        """Main trading loop that runs during market hours"""
        while self.is_running:
            try:
                if await self._is_market_open():
                    # Get all active users with auto-trading enabled
                    active_users = await self._get_active_auto_trading_users()
                    
                    logger.info(f"📊 Processing {len(active_users)} active auto-trading users")
                    
                    # Process each user's trading session
                    for user in active_users:
                        try:
                            await self._process_user_trading_session(user)
                        except Exception as e:
                            logger.error(f"Error processing user {user.id}: {e}")
                            
                    # Wait before next iteration (30 seconds during market hours)
                    await asyncio.sleep(30)
                else:
                    # Market closed - wait longer (5 minutes)
                    logger.debug("Market closed - auto trading paused")
                    await asyncio.sleep(300)
                    
            except Exception as e:
                logger.error(f"Error in main trading loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _is_market_open(self) -> bool:
        """Check if any relevant market is currently open"""
        ist = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(ist).time()
        current_weekday = datetime.now(ist).weekday()
        
        # Skip weekends (Saturday=5, Sunday=6)
        if current_weekday >= 5:
            return False
            
        # Check if NSE/BSE is open
        nse_hours = self.market_hours["NSE"]
        return nse_hours.open_time <= current_time <= nse_hours.close_time
    
    async def _get_active_auto_trading_users(self) -> List[User]:
        """Get all users with active auto-trading subscriptions"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(User)
                    .join(Subscription)
                    .join(SubscriptionPlan)
                    .join(BrokerAccount)
                    .where(
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            SubscriptionPlan.automated_trading == True,
                            BrokerAccount.status == BrokerAccountStatus.CONNECTED,
                            BrokerAccount.is_primary == True,
                            User.auto_trading_enabled == True
                        )
                    )
                    .options(
                        selectinload(User.subscriptions).selectinload(Subscription.plan),
                        selectinload(User.broker_accounts)
                    )
                    .distinct()
                )
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"Error getting active auto-trading users: {e}")
                return []
    
    async def _process_user_trading_session(self, user: User):
        """Process automatic trading for a single user"""
        try:
            # Check if trading is paused for this user
            if self._is_trading_paused(str(user.id)):
                logger.debug(f"Auto-trading paused for user {user.id}")
                return
            
            # Check daily trade limits
            remaining_trades = await self._get_remaining_daily_trades(user)
            if remaining_trades <= 0:
                logger.debug(f"User {user.id} has reached daily trade limit")
                return
            
            # Get user's primary broker account
            primary_broker = self._get_primary_broker_account(user)
            if not primary_broker:
                logger.warning(f"No primary broker account for user {user.id}")
                return
            
            # Fetch available funds
            available_funds = await self._get_available_funds(user, primary_broker)
            if available_funds < 1000:  # Minimum 1000 INR required
                logger.debug(f"Insufficient funds for user {user.id}: ₹{available_funds}")
                return
            
            # Get user's trading preferences
            trading_mode = user.auto_trading_mode or AutoTradingMode.CONSERVATIVE
            watchlist_symbols = await self._get_user_watchlist(user)
            
            # Process each symbol in watchlist
            signals_generated = []
            for symbol in watchlist_symbols:
                try:
                    # Get market data and ML predictions
                    market_data = await market_data_client.get_live_quote(symbol)
                    ml_prediction = await ml_service_client.get_prediction(symbol, "intraday")
                    
                    # Generate trading signals
                    signal = await self._generate_trading_signal(
                        user, symbol, market_data, ml_prediction, trading_mode
                    )
                    
                    if signal:
                        signals_generated.append(signal)
                        
                except Exception as e:
                    logger.error(f"Error processing symbol {symbol} for user {user.id}: {e}")
            
            # Execute top signals based on available funds and limits
            await self._execute_user_signals(user, signals_generated, available_funds, remaining_trades)
            
        except Exception as e:
            logger.error(f"Error in user trading session for {user.id}: {e}")
    
    async def _generate_trading_signal(
        self, 
        user: User, 
        symbol: str, 
        market_data: Dict, 
        ml_prediction: Dict,
        trading_mode: AutoTradingMode
    ) -> Optional[TradingSignal]:
        """Generate trading signal for a specific symbol"""
        try:
            if not ml_prediction or ml_prediction.get("confidence", 0) < 0.6:
                return None
            
            current_price = market_data.get("price", 0)
            predicted_price = ml_prediction.get("predicted_price", 0)
            confidence = ml_prediction.get("confidence", 0)
            
            # Calculate expected return
            expected_return = (predicted_price - current_price) / current_price
            
            # Apply trading mode filters
            min_return_threshold = {
                AutoTradingMode.CONSERVATIVE: 0.02,  # 2% minimum
                AutoTradingMode.MODERATE: 0.015,     # 1.5% minimum
                AutoTradingMode.AGGRESSIVE: 0.01     # 1% minimum
            }.get(trading_mode, 0.02)
            
            min_confidence_threshold = {
                AutoTradingMode.CONSERVATIVE: 0.8,   # 80% minimum
                AutoTradingMode.MODERATE: 0.7,       # 70% minimum
                AutoTradingMode.AGGRESSIVE: 0.6      # 60% minimum
            }.get(trading_mode, 0.8)
            
            # Check if signal meets criteria
            if (abs(expected_return) >= min_return_threshold and 
                confidence >= min_confidence_threshold):
                
                signal_type = "buy" if expected_return > 0 else "sell"
                
                # Calculate position size based on user's risk profile
                position_size = await self._calculate_position_size(
                    user, current_price, expected_return, confidence, trading_mode
                )
                
                return TradingSignal(
                    signal=signal_type,
                    symbol=symbol,
                    confidence=confidence,
                    price=current_price,
                    quantity=position_size,
                    reason=f"ML Auto-Trade: {expected_return:.2%} expected return",
                    timestamp=datetime.utcnow(),
                    metadata={
                        "predicted_price": predicted_price,
                        "expected_return": expected_return,
                        "trading_mode": trading_mode.value,
                        "user_id": str(user.id)
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating trading signal: {e}")
            return None
    
    async def _execute_user_signals(
        self, 
        user: User, 
        signals: List[TradingSignal], 
        available_funds: float,
        remaining_trades: int
    ):
        """Execute trading signals for a user"""
        if not signals:
            return
            
        # Sort signals by confidence and expected return
        signals.sort(key=lambda s: s.confidence * abs(s.metadata.get("expected_return", 0)), reverse=True)
        
        # Execute top signals within limits
        executed_count = 0
        funds_used = 0
        
        for signal in signals[:remaining_trades]:
            try:
                trade_value = signal.price * signal.quantity
                
                # Check if we have enough funds
                if funds_used + trade_value > available_funds * 0.8:  # Use max 80% of available funds
                    logger.debug(f"Insufficient funds for signal: {signal.symbol}")
                    continue
                
                # Execute the trade
                success = await self._execute_auto_trade(user, signal)
                
                if success:
                    executed_count += 1
                    funds_used += trade_value
                    
                    # Log successful auto-trade
                    await self._log_auto_trade(user, signal, AutoTradeStatus.EXECUTED)
                    
                    # Send notification to user
                    await notification_service.send_auto_trade_notification(
                        user, signal, "executed"
                    )
                    
                    logger.info(f"✅ Auto-trade executed for {user.email}: {signal.symbol} {signal.signal}")
                else:
                    await self._log_auto_trade(user, signal, AutoTradeStatus.FAILED)
                    
            except Exception as e:
                logger.error(f"Error executing signal for user {user.id}: {e}")
                await self._log_auto_trade(user, signal, AutoTradeStatus.FAILED)
        
        if executed_count > 0:
            logger.info(f"📈 Executed {executed_count} auto-trades for user {user.email}")
    
    async def _execute_auto_trade(self, user: User, signal: TradingSignal) -> bool:
        """Execute a single automatic trade"""
        try:
            primary_broker = self._get_primary_broker_account(user)
            if not primary_broker:
                return False
            
            # Prepare order data
            order_data = {
                "symbol": signal.symbol,
                "side": signal.signal,
                "type": "market",
                "quantity": signal.quantity,
                "broker_account_id": primary_broker.id,
                "is_auto_trade": True,
                "auto_trade_reason": signal.reason
            }
            
            # Risk management check
            risk_assessment = await risk_manager.assess_auto_trade_risk(user, order_data)
            if risk_assessment["risk_score"] > 0.7:
                logger.warning(f"High risk auto-trade rejected for user {user.id}: {signal.symbol}")
                return False
            
            # Execute through broker service
            result = await broker_service.place_auto_trade(user, order_data)
            
            return result.get("status") == "success"
            
        except Exception as e:
            logger.error(f"Error executing auto-trade: {e}")
            return False
    
    async def _get_remaining_daily_trades(self, user: User) -> int:
        """Get remaining daily trades for user based on subscription plan"""
        async with AsyncSessionLocal() as db:
            try:
                # Get user's current plan
                subscription = user.subscriptions[0] if user.subscriptions else None
                if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
                    return 0
                
                plan = subscription.plan
                daily_limit = self._get_plan_daily_trade_limit(plan.plan_id)
                
                # Count today's auto-trades
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                
                result = await db.execute(
                    select(AutoTrade)
                    .where(
                        and_(
                            AutoTrade.user_id == user.id,
                            AutoTrade.status == AutoTradeStatus.EXECUTED,
                            AutoTrade.created_at >= today_start
                        )
                    )
                )
                
                today_trades = len(result.scalars().all())
                return max(0, daily_limit - today_trades)
                
            except Exception as e:
                logger.error(f"Error getting remaining daily trades: {e}")
                return 0
    
    def _get_plan_daily_trade_limit(self, plan_id: str) -> int:
        """Get daily trade limit based on subscription plan"""
        limits = {
            "free": 0,
            "basic": 10,
            "pro": 50,
            "enterprise": 1000
        }
        return limits.get(plan_id, 0)
    
    def _get_primary_broker_account(self, user: User) -> Optional[BrokerAccount]:
        """Get user's primary broker account"""
        for account in user.broker_accounts:
            if (account.is_primary and 
                account.status == BrokerAccountStatus.CONNECTED):
                return account
        return None
    
    async def _get_available_funds(self, user: User, broker_account: BrokerAccount) -> float:
        """Get available trading funds from broker"""
        try:
            funds_data = await broker_service.get_account_balance(user, broker_account)
            return funds_data.get("available_cash", 0)
        except Exception as e:
            logger.error(f"Error getting available funds: {e}")
            return 0
    
    async def _get_user_watchlist(self, user: User) -> List[str]:
        """Get user's watchlist symbols for auto-trading"""
        # Default Indian stocks for auto-trading
        default_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        
        # TODO: Get from user's actual watchlist
        return default_symbols
    
    async def _calculate_position_size(
        self, 
        user: User, 
        price: float, 
        expected_return: float, 
        confidence: float,
        trading_mode: AutoTradingMode
    ) -> int:
        """Calculate position size for auto-trade"""
        try:
            # Get available funds
            primary_broker = self._get_primary_broker_account(user)
            available_funds = await self._get_available_funds(user, primary_broker)
            
            # Risk-based position sizing
            max_position_percent = {
                AutoTradingMode.CONSERVATIVE: 0.05,  # 5% max per trade
                AutoTradingMode.MODERATE: 0.08,      # 8% max per trade
                AutoTradingMode.AGGRESSIVE: 0.10     # 10% max per trade
            }.get(trading_mode, 0.05)
            
            max_position_value = available_funds * max_position_percent
            base_quantity = int(max_position_value / price)
            
            # Adjust based on confidence and expected return
            confidence_multiplier = confidence
            return_multiplier = min(abs(expected_return) * 10, 1.0)
            
            adjusted_quantity = int(base_quantity * confidence_multiplier * return_multiplier)
            
            return max(1, adjusted_quantity)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 1
    
    async def _log_auto_trade(self, user: User, signal: TradingSignal, status: AutoTradeStatus):
        """Log auto-trade execution for tracking and analytics"""
        async with AsyncSessionLocal() as db:
            try:
                auto_trade = AutoTrade(
                    user_id=user.id,
                    symbol=signal.symbol,
                    side=signal.signal,
                    quantity=signal.quantity,
                    price=signal.price,
                    confidence=signal.confidence,
                    expected_return=signal.metadata.get("expected_return", 0),
                    status=status,
                    reason=AutoTradeReason.ML_PREDICTION,
                    trade_metadata=signal.metadata
                )
                
                db.add(auto_trade)
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error logging auto-trade: {e}")
    
    async def _market_hours_monitor(self):
        """Monitor market hours and manage trading sessions"""
        while self.is_running:
            try:
                is_open = await self._is_market_open()
                
                if is_open:
                    # Market is open - ensure all eligible users have active sessions
                    active_users = await self._get_active_auto_trading_users()
                    for user in active_users:
                        if user.id not in self.active_sessions:
                            await self._start_user_trading_session(user)
                else:
                    # Market is closed - stop all trading sessions
                    for user_id in list(self.active_sessions.keys()):
                        await self._stop_user_trading_session(user_id)
                
                # Check every 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in market hours monitor: {e}")
                await asyncio.sleep(300)
    
    async def _start_user_trading_session(self, user: User):
        """Start trading session for a user"""
        self.active_sessions[user.id] = {
            "user": user,
            "started_at": datetime.utcnow(),
            "trades_executed": 0
        }
        logger.info(f"🟢 Started auto-trading session for {user.email}")
    
    async def _stop_user_trading_session(self, user_id: str):
        """Stop trading session for a user"""
        if user_id in self.active_sessions:
            session = self.active_sessions.pop(user_id)
            logger.info(f"🔴 Stopped auto-trading session for user {user_id}")
    
    # Public API methods
    
    async def enable_auto_trading(self, user_id: str) -> bool:
        """Enable auto-trading for a user"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Check if user has valid subscription
                subscription = user.subscriptions[0] if user.subscriptions else None
                if (not subscription or 
                    subscription.status != SubscriptionStatus.ACTIVE or
                    not subscription.plan.automated_trading):
                    return False
                
                user.auto_trading_enabled = True
                await db.commit()
                
                logger.info(f"Auto-trading enabled for user {user.email}")
                return True
                
            except Exception as e:
                logger.error(f"Error enabling auto-trading: {e}")
                return False
    
    async def disable_auto_trading(self, user_id: str) -> bool:
        """Disable auto-trading for a user"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                user.auto_trading_enabled = False
                await db.commit()
                
                # Stop active session if exists
                if user_id in self.active_sessions:
                    await self._stop_user_trading_session(user_id)
                
                logger.info(f"Auto-trading disabled for user {user.email}")
                return True
                
            except Exception as e:
                logger.error(f"Error disabling auto-trading: {e}")
                return False
    
    async def emergency_stop_all_trading(self, user_id: str, reason: str = "Manual intervention") -> bool:
        """Emergency stop all auto-trading activity for a user"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Immediately disable auto-trading
                user.auto_trading_enabled = False
                await db.commit()
                
                # Stop active session
                if user_id in self.active_sessions:
                    await self._stop_user_trading_session(user_id)
                
                # Cancel any pending auto-trades
                await self._cancel_pending_auto_trades(user_id, reason)
                
                logger.warning(f"🚨 EMERGENCY STOP: Auto-trading halted for user {user.email}. Reason: {reason}")
                
                # Send immediate notification
                await notification_service.send_emergency_notification(
                    user, f"Auto-trading emergency stop activated: {reason}"
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Error in emergency stop: {e}")
                return False
    
    async def pause_auto_trading(self, user_id: str, duration_minutes: int = 30) -> bool:
        """Temporarily pause auto-trading for a specified duration"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Set pause until timestamp
                from datetime import datetime, timedelta
                pause_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
                
                # Store pause info in user metadata or create a separate pause mechanism
                if user_id in self.active_sessions:
                    self.active_sessions[user_id]["paused_until"] = pause_until
                    self.active_sessions[user_id]["pause_reason"] = "Manual pause"
                
                logger.info(f"⏸️ Auto-trading paused for user {user.email} until {pause_until}")
                
                await notification_service.send_notification(
                    user, f"Auto-trading paused for {duration_minutes} minutes"
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Error pausing auto-trading: {e}")
                return False
    
    async def resume_auto_trading(self, user_id: str) -> bool:
        """Resume auto-trading after manual pause"""
        try:
            if user_id in self.active_sessions:
                # Remove pause
                if "paused_until" in self.active_sessions[user_id]:
                    del self.active_sessions[user_id]["paused_until"]
                if "pause_reason" in self.active_sessions[user_id]:
                    del self.active_sessions[user_id]["pause_reason"]
                
                logger.info(f"▶️ Auto-trading resumed for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resuming auto-trading: {e}")
            return False
    
    async def _cancel_pending_auto_trades(self, user_id: str, reason: str):
        """Cancel all pending auto-trades for a user"""
        async with AsyncSessionLocal() as db:
            try:
                # Update pending auto-trades to cancelled status
                from sqlalchemy import update
                
                await db.execute(
                    update(AutoTrade)
                    .where(
                        and_(
                            AutoTrade.user_id == user_id,
                            AutoTrade.status == AutoTradeStatus.PENDING
                        )
                    )
                    .values(
                        status=AutoTradeStatus.CANCELLED,
                        error_message=f"Cancelled due to manual intervention: {reason}"
                    )
                )
                
                await db.commit()
                logger.info(f"Cancelled pending auto-trades for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error cancelling pending trades: {e}")
    
    def _is_trading_paused(self, user_id: str) -> bool:
        """Check if trading is currently paused for a user"""
        if user_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[user_id]
        if "paused_until" not in session:
            return False
        
        from datetime import datetime
        pause_until = session["paused_until"]
        
        if datetime.utcnow() >= pause_until:
            # Pause period expired, remove it
            del session["paused_until"]
            if "pause_reason" in session:
                del session["pause_reason"]
            return False
        
        return True
    
    async def get_auto_trading_status(self, user_id: str) -> Dict[str, Any]:
        """Get auto-trading status and statistics for a user"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(User)
                    .options(
                        selectinload(User.subscriptions).selectinload(Subscription.plan),
                        selectinload(User.broker_accounts)
                    )
                    .where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return {"error": "User not found"}
                
                # Get today's trades
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                result = await db.execute(
                    select(AutoTrade).where(
                        and_(
                            AutoTrade.user_id == user_id,
                            AutoTrade.created_at >= today_start
                        )
                    )
                )
                today_trades = result.scalars().all()
                
                subscription = user.subscriptions[0] if user.subscriptions else None
                daily_limit = 0
                if subscription and subscription.plan:
                    daily_limit = self._get_plan_daily_trade_limit(subscription.plan.plan_id)
                
                return {
                    "enabled": user.auto_trading_enabled,
                    "subscription_plan": subscription.plan.plan_id if subscription else "free",
                    "daily_limit": daily_limit,
                    "trades_today": len(today_trades),
                    "remaining_trades": max(0, daily_limit - len(today_trades)),
                    "successful_trades_today": len([t for t in today_trades if t.status == AutoTradeStatus.EXECUTED]),
                    "is_market_open": await self._is_market_open(),
                    "has_active_session": user_id in self.active_sessions,
                    "primary_broker_connected": bool(self._get_primary_broker_account(user))
                }
                
            except Exception as e:
                logger.error(f"Error getting auto-trading status: {e}")
                return {"error": str(e)}

# Global auto trading service instance
auto_trading_service = AutoTradingService()