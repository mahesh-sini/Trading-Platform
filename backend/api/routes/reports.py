from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta, date
from io import BytesIO
import csv
import json
import tempfile
import os

from services.database import get_db
from services.auth_service import get_current_user
from models.user import User
from models.auto_trade import AutoTrade, AutoTradeStatus, AutoTradeReason
from models.trade import Trade, Order, OrderStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class ReportFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    symbols: Optional[List[str]] = None
    status: Optional[str] = None
    trade_type: Literal["auto", "manual", "all"] = "all"
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class ReportFormat(str):
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"

class TradeReportSummary(BaseModel):
    period_start: date
    period_end: date
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_volume: float
    total_pnl: float
    success_rate: float
    average_trade_size: float
    best_performing_symbol: Optional[str]
    worst_performing_symbol: Optional[str]

class DetailedTradeReport(BaseModel):
    summary: TradeReportSummary
    trades: List[Dict[str, Any]]
    daily_breakdown: List[Dict[str, Any]]
    symbol_breakdown: List[Dict[str, Any]]

# Report generation endpoints
@router.get("/auto-trades/summary")
async def get_auto_trades_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get summary of auto-executed trades for a period"""
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Convert dates to datetime for database query
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get auto trades for the period
        result = await db.execute(
            select(AutoTrade).where(
                and_(
                    AutoTrade.user_id == current_user.id,
                    AutoTrade.created_at >= start_datetime,
                    AutoTrade.created_at <= end_datetime
                )
            )
        )
        trades = result.scalars().all()
        
        if not trades:
            return TradeReportSummary(
                period_start=start_date,
                period_end=end_date,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                total_volume=0.0,
                total_pnl=0.0,
                success_rate=0.0,
                average_trade_size=0.0,
                best_performing_symbol=None,
                worst_performing_symbol=None
            )
        
        # Calculate metrics
        total_trades = len(trades)
        successful_trades = len([t for t in trades if t.status == AutoTradeStatus.EXECUTED])
        failed_trades = len([t for t in trades if t.status == AutoTradeStatus.FAILED])
        
        executed_trades = [t for t in trades if t.status == AutoTradeStatus.EXECUTED]
        total_volume = sum([t.quantity * t.price for t in executed_trades])
        total_pnl = sum([t.realized_pnl or 0 for t in executed_trades])
        success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
        average_trade_size = total_volume / successful_trades if successful_trades > 0 else 0
        
        # Find best/worst performing symbols
        symbol_performance = {}
        for trade in executed_trades:
            if trade.realized_pnl:
                if trade.symbol not in symbol_performance:
                    symbol_performance[trade.symbol] = 0
                symbol_performance[trade.symbol] += trade.realized_pnl
        
        best_symbol = max(symbol_performance.items(), key=lambda x: x[1])[0] if symbol_performance else None
        worst_symbol = min(symbol_performance.items(), key=lambda x: x[1])[0] if symbol_performance else None
        
        return TradeReportSummary(
            period_start=start_date,
            period_end=end_date,
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            total_volume=round(total_volume, 2),
            total_pnl=round(total_pnl, 2),
            success_rate=round(success_rate, 2),
            average_trade_size=round(average_trade_size, 2),
            best_performing_symbol=best_symbol,
            worst_performing_symbol=worst_symbol
        )
        
    except Exception as e:
        logger.error(f"Error generating auto trades summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate trades summary"
        )

@router.post("/auto-trades/detailed")
async def get_detailed_auto_trades_report(
    filters: ReportFilters,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed auto-trades report with filters"""
    try:
        # Default date range if not provided
        if not filters.end_date:
            filters.end_date = date.today()
        if not filters.start_date:
            filters.start_date = filters.end_date - timedelta(days=30)
        
        start_datetime = datetime.combine(filters.start_date, datetime.min.time())
        end_datetime = datetime.combine(filters.end_date, datetime.max.time())
        
        # Build query with filters
        query = select(AutoTrade).where(
            and_(
                AutoTrade.user_id == current_user.id,
                AutoTrade.created_at >= start_datetime,
                AutoTrade.created_at <= end_datetime
            )
        )
        
        # Apply additional filters
        if filters.symbols:
            query = query.where(AutoTrade.symbol.in_([s.upper() for s in filters.symbols]))
        
        if filters.status:
            try:
                status_enum = AutoTradeStatus(filters.status)
                query = query.where(AutoTrade.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {filters.status}"
                )
        
        if filters.min_amount or filters.max_amount:
            if filters.min_amount:
                query = query.where((AutoTrade.quantity * AutoTrade.price) >= filters.min_amount)
            if filters.max_amount:
                query = query.where((AutoTrade.quantity * AutoTrade.price) <= filters.max_amount)
        
        query = query.order_by(desc(AutoTrade.created_at))
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
        # Generate summary
        summary = await get_auto_trades_summary(
            filters.start_date, filters.end_date, current_user, db
        )
        
        # Format trades data
        trades_data = []
        for trade in trades:
            trades_data.append({
                "id": str(trade.id),
                "date": trade.created_at.date().isoformat(),
                "time": trade.created_at.time().strftime("%H:%M:%S"),
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "executed_price": trade.executed_price,
                "total_value": trade.quantity * trade.price,
                "confidence": trade.confidence,
                "expected_return": trade.expected_return,
                "realized_pnl": trade.realized_pnl,
                "status": trade.status.value,
                "reason": trade.reason.value,
                "execution_time": trade.execution_time.isoformat() if trade.execution_time else None
            })
        
        # Daily breakdown
        daily_stats = {}
        for trade in trades:
            date_key = trade.created_at.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "date": date_key,
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_volume": 0,
                    "total_pnl": 0
                }
            
            daily_stats[date_key]["total_trades"] += 1
            if trade.status == AutoTradeStatus.EXECUTED:
                daily_stats[date_key]["successful_trades"] += 1
                daily_stats[date_key]["total_volume"] += trade.quantity * trade.price
                daily_stats[date_key]["total_pnl"] += trade.realized_pnl or 0
        
        daily_breakdown = list(daily_stats.values())
        daily_breakdown.sort(key=lambda x: x["date"])
        
        # Symbol breakdown
        symbol_stats = {}
        for trade in trades:
            if trade.symbol not in symbol_stats:
                symbol_stats[trade.symbol] = {
                    "symbol": trade.symbol,
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_volume": 0,
                    "total_pnl": 0,
                    "avg_confidence": 0
                }
            
            stats = symbol_stats[trade.symbol]
            stats["total_trades"] += 1
            if trade.status == AutoTradeStatus.EXECUTED:
                stats["successful_trades"] += 1
                stats["total_volume"] += trade.quantity * trade.price
                stats["total_pnl"] += trade.realized_pnl or 0
            
            # Calculate rolling average confidence
            old_avg = stats["avg_confidence"]
            stats["avg_confidence"] = (old_avg * (stats["total_trades"] - 1) + trade.confidence) / stats["total_trades"]
        
        symbol_breakdown = list(symbol_stats.values())
        symbol_breakdown.sort(key=lambda x: x["total_pnl"], reverse=True)
        
        return DetailedTradeReport(
            summary=summary,
            trades=trades_data,
            daily_breakdown=daily_breakdown,
            symbol_breakdown=symbol_breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating detailed trades report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate detailed trades report"
        )

@router.get("/auto-trades/export")
async def export_auto_trades_report(
    format: Literal["csv", "json"] = "csv",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    symbols: Optional[str] = None,  # Comma-separated symbols
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export auto-trades report in CSV or JSON format"""
    try:
        # Parse symbols
        symbol_list = symbols.split(",") if symbols else None
        
        # Get detailed report
        filters = ReportFilters(
            start_date=start_date,
            end_date=end_date,
            symbols=symbol_list,
            status=status
        )
        
        report = await get_detailed_auto_trades_report(filters, current_user, db)
        
        # Generate filename
        start_str = (start_date or date.today() - timedelta(days=30)).strftime("%Y%m%d")
        end_str = (end_date or date.today()).strftime("%Y%m%d")
        filename = f"auto_trades_report_{start_str}_{end_str}.{format}"
        
        if format == "csv":
            # Create CSV file
            output = BytesIO()
            writer = csv.DictWriter(
                output, 
                fieldnames=[
                    "date", "time", "symbol", "side", "quantity", "price", 
                    "executed_price", "total_value", "confidence", "expected_return", 
                    "realized_pnl", "status", "reason"
                ],
                encoding='utf-8'
            )
            
            # Write header
            output.write("Date,Time,Symbol,Side,Quantity,Price,Executed Price,Total Value,Confidence,Expected Return,Realized P&L,Status,Reason\n".encode('utf-8'))
            
            # Write trades data
            for trade in report.trades:
                row = f"{trade['date']},{trade['time']},{trade['symbol']},{trade['side']},{trade['quantity']},{trade['price']},{trade['executed_price'] or ''},{trade['total_value']},{trade['confidence']},{trade['expected_return']},{trade['realized_pnl'] or ''},{trade['status']},{trade['reason']}\n"
                output.write(row.encode('utf-8'))
            
            output.seek(0)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as f:
                f.write(output.getvalue())
                temp_path = f.name
            
            return FileResponse(
                path=temp_path,
                filename=filename,
                media_type="text/csv",
                background=lambda: os.unlink(temp_path)  # Clean up temp file
            )
            
        elif format == "json":
            # Create JSON file
            report_dict = {
                "summary": report.summary.dict(),
                "trades": report.trades,
                "daily_breakdown": report.daily_breakdown,
                "symbol_breakdown": report.symbol_breakdown,
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": str(current_user.id)
            }
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(report_dict, f, indent=2, default=str)
                temp_path = f.name
            
            return FileResponse(
                path=temp_path,
                filename=filename,
                media_type="application/json",
                background=lambda: os.unlink(temp_path)  # Clean up temp file
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting trades report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export trades report"
        )

@router.get("/eod-summary")
async def get_end_of_day_summary(
    trade_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get end-of-day trading summary"""
    try:
        if not trade_date:
            trade_date = date.today()
        
        start_datetime = datetime.combine(trade_date, datetime.min.time())
        end_datetime = datetime.combine(trade_date, datetime.max.time())
        
        # Get auto trades for the day
        auto_trades_result = await db.execute(
            select(AutoTrade).where(
                and_(
                    AutoTrade.user_id == current_user.id,
                    AutoTrade.created_at >= start_datetime,
                    AutoTrade.created_at <= end_datetime
                )
            )
        )
        auto_trades = auto_trades_result.scalars().all()
        
        # Get manual trades for the day (if any)
        manual_trades_result = await db.execute(
            select(Trade).where(
                and_(
                    Trade.user_id == current_user.id,
                    Trade.executed_at >= start_datetime,
                    Trade.executed_at <= end_datetime
                )
            )
        )
        manual_trades = manual_trades_result.scalars().all()
        
        # Calculate auto trades metrics
        auto_executed = [t for t in auto_trades if t.status == AutoTradeStatus.EXECUTED]
        auto_volume = sum([t.quantity * t.price for t in auto_executed])
        auto_pnl = sum([t.realized_pnl or 0 for t in auto_executed])
        
        # Calculate manual trades metrics
        manual_volume = sum([t.trade_value for t in manual_trades])
        manual_pnl = 0  # Would need to calculate based on current prices
        
        # Market performance for comparison
        market_symbols = list(set([t.symbol for t in auto_executed]))
        
        return {
            "date": trade_date.isoformat(),
            "auto_trading": {
                "total_trades": len(auto_trades),
                "executed_trades": len(auto_executed),
                "failed_trades": len([t for t in auto_trades if t.status == AutoTradeStatus.FAILED]),
                "total_volume": round(auto_volume, 2),
                "realized_pnl": round(auto_pnl, 2),
                "success_rate": round((len(auto_executed) / len(auto_trades)) * 100, 2) if auto_trades else 0,
                "symbols_traded": market_symbols
            },
            "manual_trading": {
                "total_trades": len(manual_trades),
                "total_volume": round(manual_volume, 2),
                "estimated_pnl": round(manual_pnl, 2)
            },
            "overall": {
                "total_trades": len(auto_trades) + len(manual_trades),
                "total_volume": round(auto_volume + manual_volume, 2),
                "total_pnl": round(auto_pnl + manual_pnl, 2)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating EOD summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate end-of-day summary"
        )

@router.get("/performance-metrics")
async def get_performance_metrics(
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive performance metrics"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get auto trades for the period
        result = await db.execute(
            select(AutoTrade).where(
                and_(
                    AutoTrade.user_id == current_user.id,
                    AutoTrade.created_at >= start_date,
                    AutoTrade.created_at <= end_date
                )
            )
        )
        trades = result.scalars().all()
        
        executed_trades = [t for t in trades if t.status == AutoTradeStatus.EXECUTED]
        
        if not executed_trades:
            return {
                "period_days": period_days,
                "total_trades": 0,
                "metrics": {}
            }
        
        # Calculate performance metrics
        returns = [t.realized_pnl or 0 for t in executed_trades if t.realized_pnl]
        total_return = sum(returns)
        avg_return = total_return / len(returns) if returns else 0
        
        # Win rate
        winning_trades = len([r for r in returns if r > 0])
        win_rate = (winning_trades / len(returns)) * 100 if returns else 0
        
        # Risk metrics
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r < 0]
        
        avg_win = sum(positive_returns) / len(positive_returns) if positive_returns else 0
        avg_loss = sum(negative_returns) / len(negative_returns) if negative_returns else 0
        
        profit_factor = abs(sum(positive_returns) / sum(negative_returns)) if negative_returns else float('inf')
        
        # Confidence analysis
        confidence_scores = [t.confidence for t in executed_trades]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "period_days": period_days,
            "total_trades": len(executed_trades),
            "metrics": {
                "total_return": round(total_return, 2),
                "average_return_per_trade": round(avg_return, 2),
                "win_rate": round(win_rate, 2),
                "average_win": round(avg_win, 2),
                "average_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "N/A",
                "average_confidence": round(avg_confidence * 100, 2),
                "best_trade": round(max(returns), 2) if returns else 0,
                "worst_trade": round(min(returns), 2) if returns else 0,
                "total_winning_trades": winning_trades,
                "total_losing_trades": len(negative_returns)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate performance metrics"
        )