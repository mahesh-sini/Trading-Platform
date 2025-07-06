"""
Advanced Analytics API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.services.analytics.advanced_analytics import (
    advanced_analytics, MetricDefinition, DashboardWidget, Filter,
    MetricType, AggregationType, TimeFrame
)

router = APIRouter()


class FilterModel(BaseModel):
    """Filter model for API"""
    field: str = Field(..., min_length=1)
    operator: str = Field(..., regex=r"^(eq|ne|gt|lt|gte|lte|in|nin|contains|starts_with|ends_with)$")
    value: Any
    data_type: str = Field("string", regex=r"^(string|number|date|boolean|array)$")


class MetricDefinitionModel(BaseModel):
    """Metric definition model for API"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    metric_type: str = Field(..., regex=r"^(performance|risk|portfolio|trading|market|custom)$")
    calculation_formula: str = Field(..., min_length=1)
    data_sources: List[str] = Field(..., min_items=1)
    aggregation: str = Field(..., regex=r"^(sum|avg|count|min|max|median|percentile|std|var|corr)$")
    time_frame: str = Field(..., regex=r"^(real_time|1m|5m|15m|30m|1h|1d|1w|1mo|3mo|1y)$")
    filters: List[FilterModel] = Field(default_factory=list)
    custom_parameters: Optional[Dict[str, Any]] = None


class DashboardWidgetModel(BaseModel):
    """Dashboard widget model for API"""
    widget_id: str = Field(..., min_length=1, max_length=50)
    widget_type: str = Field(..., regex=r"^(chart|table|metric|heatmap|gauge)$")
    title: str = Field(..., min_length=1, max_length=100)
    metric_definitions: List[MetricDefinitionModel]
    visualization_config: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval: int = Field(30, ge=10, le=3600)
    position: Dict[str, int] = Field(..., description="x, y, width, height")
    filters: List[FilterModel] = Field(default_factory=list)


class CreateDashboardRequest(BaseModel):
    """Create dashboard request"""
    dashboard_id: str = Field(..., min_length=1, max_length=100)
    widgets: List[DashboardWidgetModel] = Field(..., min_items=1)


class CalculateMetricRequest(BaseModel):
    """Calculate metric request"""
    metric_name: str
    data: Dict[str, Any]
    additional_filters: Optional[List[FilterModel]] = None


class GenerateDashboardDataRequest(BaseModel):
    """Generate dashboard data request"""
    dashboard_id: str
    data_sources: Dict[str, Any]
    additional_filters: Optional[List[FilterModel]] = None


def convert_filter_model(filter_model: FilterModel) -> Filter:
    """Convert FilterModel to Filter"""
    return Filter(
        field=filter_model.field,
        operator=filter_model.operator,
        value=filter_model.value,
        data_type=filter_model.data_type
    )


def convert_metric_model(metric_model: MetricDefinitionModel) -> MetricDefinition:
    """Convert MetricDefinitionModel to MetricDefinition"""
    return MetricDefinition(
        name=metric_model.name,
        description=metric_model.description,
        metric_type=MetricType(metric_model.metric_type),
        calculation_formula=metric_model.calculation_formula,
        data_sources=metric_model.data_sources,
        aggregation=AggregationType(metric_model.aggregation),
        time_frame=TimeFrame(metric_model.time_frame),
        filters=[convert_filter_model(f) for f in metric_model.filters],
        custom_parameters=metric_model.custom_parameters
    )


def convert_widget_model(widget_model: DashboardWidgetModel) -> DashboardWidget:
    """Convert DashboardWidgetModel to DashboardWidget"""
    return DashboardWidget(
        widget_id=widget_model.widget_id,
        widget_type=widget_model.widget_type,
        title=widget_model.title,
        metric_definitions=[convert_metric_model(m) for m in widget_model.metric_definitions],
        visualization_config=widget_model.visualization_config,
        refresh_interval=widget_model.refresh_interval,
        position=widget_model.position,
        filters=[convert_filter_model(f) for f in widget_model.filters]
    )


@router.post("/metrics", status_code=status.HTTP_201_CREATED)
async def register_custom_metric(
    metric: MetricDefinitionModel,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:write"))
):
    """Register a custom metric definition"""
    try:
        metric_def = convert_metric_model(metric)
        success = await advanced_analytics.register_custom_metric(metric_def)
        
        if success:
            return {
                "message": f"Metric {metric.name} registered successfully",
                "metric_name": metric.name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register metric"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/metrics")
async def get_available_metrics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get list of available metrics"""
    try:
        metrics = await advanced_analytics.get_available_metrics()
        return {
            "metrics": metrics,
            "total_count": len(metrics)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/metrics/calculate")
async def calculate_metric(
    request: CalculateMetricRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Calculate a custom metric"""
    try:
        additional_filters = None
        if request.additional_filters:
            additional_filters = [convert_filter_model(f) for f in request.additional_filters]
        
        result = await advanced_analytics.calculate_metric(
            metric_name=request.metric_name,
            data=request.data,
            additional_filters=additional_filters
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/dashboards", status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    request: CreateDashboardRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:write"))
):
    """Create a custom dashboard"""
    try:
        widgets = [convert_widget_model(w) for w in request.widgets]
        
        success = await advanced_analytics.create_dashboard(
            dashboard_id=request.dashboard_id,
            widgets=widgets,
            user_id=str(current_user.id),
            organization_id=str(current_user.organization_id)
        )
        
        if success:
            return {
                "message": f"Dashboard {request.dashboard_id} created successfully",
                "dashboard_id": request.dashboard_id,
                "widget_count": len(widgets)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create dashboard"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/dashboards/{dashboard_id}/data")
async def generate_dashboard_data(
    dashboard_id: str,
    request: GenerateDashboardDataRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Generate data for dashboard widgets"""
    try:
        additional_filters = None
        if request.additional_filters:
            additional_filters = [convert_filter_model(f) for f in request.additional_filters]
        
        dashboard_data = await advanced_analytics.generate_dashboard_data(
            dashboard_id=request.dashboard_id,
            data_sources=request.data_sources,
            additional_filters=additional_filters
        )
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/filters/suggestions")
async def get_filter_suggestions(
    data_source: str = Query(..., description="Data source name"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get filter suggestions for a data source"""
    try:
        suggestions = await advanced_analytics.get_filter_suggestions(data_source)
        return {
            "data_source": data_source,
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/widget-types")
async def get_widget_types(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get available widget types and their configurations"""
    widget_types = {
        "chart": {
            "name": "Chart",
            "description": "Line, bar, pie, or area charts",
            "config_options": {
                "chart_type": ["line", "bar", "pie", "area", "scatter"],
                "x_axis": "string",
                "y_axis": "string",
                "color_scheme": ["default", "viridis", "plasma", "coolwarm"]
            }
        },
        "table": {
            "name": "Table",
            "description": "Tabular data display",
            "config_options": {
                "columns": "array",
                "sortable": "boolean",
                "pagination": "boolean",
                "max_rows": "number"
            }
        },
        "metric": {
            "name": "Metric",
            "description": "Single value display",
            "config_options": {
                "format": ["number", "currency", "percentage"],
                "unit": "string",
                "precision": "number",
                "comparison": "boolean"
            }
        },
        "gauge": {
            "name": "Gauge",
            "description": "Gauge or progress indicator",
            "config_options": {
                "min_value": "number",
                "max_value": "number",
                "thresholds": "array",
                "unit": "string",
                "color_scale": ["green-red", "blue-red", "rainbow"]
            }
        },
        "heatmap": {
            "name": "Heatmap",
            "description": "Heat map visualization",
            "config_options": {
                "color_scale": ["viridis", "plasma", "coolwarm", "reds", "blues"],
                "show_values": "boolean",
                "grid_size": "number"
            }
        }
    }
    
    return {"widget_types": widget_types}


@router.get("/aggregation-types")
async def get_aggregation_types(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get available aggregation types"""
    aggregation_types = {
        "sum": {
            "name": "Sum",
            "description": "Sum of all values",
            "applicable_to": ["number"]
        },
        "avg": {
            "name": "Average",
            "description": "Average of all values",
            "applicable_to": ["number"]
        },
        "count": {
            "name": "Count",
            "description": "Count of records",
            "applicable_to": ["any"]
        },
        "min": {
            "name": "Minimum",
            "description": "Minimum value",
            "applicable_to": ["number", "date"]
        },
        "max": {
            "name": "Maximum",
            "description": "Maximum value",
            "applicable_to": ["number", "date"]
        },
        "median": {
            "name": "Median",
            "description": "Median value",
            "applicable_to": ["number"]
        },
        "percentile": {
            "name": "Percentile",
            "description": "Percentile value (requires percentile parameter)",
            "applicable_to": ["number"],
            "parameters": ["percentile"]
        },
        "std": {
            "name": "Standard Deviation",
            "description": "Standard deviation of values",
            "applicable_to": ["number"]
        },
        "var": {
            "name": "Variance",
            "description": "Variance of values",
            "applicable_to": ["number"]
        },
        "corr": {
            "name": "Correlation",
            "description": "Correlation between two fields",
            "applicable_to": ["number"],
            "parameters": ["field1", "field2"]
        }
    }
    
    return {"aggregation_types": aggregation_types}


@router.get("/time-frames")
async def get_time_frames(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get available time frames"""
    time_frames = {
        "real_time": "Real-time",
        "1m": "1 Minute",
        "5m": "5 Minutes",
        "15m": "15 Minutes",
        "30m": "30 Minutes",
        "1h": "1 Hour",
        "1d": "1 Day",
        "1w": "1 Week",
        "1mo": "1 Month",
        "3mo": "3 Months",
        "1y": "1 Year"
    }
    
    return {"time_frames": time_frames}


@router.get("/data-sources")
async def get_data_sources(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("analytics:read"))
):
    """Get available data sources"""
    data_sources = {
        "trades": {
            "name": "Trades",
            "description": "Trading execution data",
            "fields": {
                "symbol": "string",
                "side": "string",
                "quantity": "number",
                "price": "number",
                "timestamp": "date",
                "commission": "number",
                "status": "string"
            }
        },
        "positions": {
            "name": "Positions",
            "description": "Current portfolio positions",
            "fields": {
                "symbol": "string",
                "quantity": "number",
                "average_price": "number",
                "current_price": "number",
                "unrealized_pnl": "number",
                "asset_type": "string"
            }
        },
        "market_data": {
            "name": "Market Data",
            "description": "Real-time and historical market data",
            "fields": {
                "symbol": "string",
                "price": "number",
                "volume": "number",
                "timestamp": "date",
                "high": "number",
                "low": "number",
                "open": "number",
                "close": "number"
            }
        },
        "portfolio_performance": {
            "name": "Portfolio Performance",
            "description": "Portfolio performance metrics",
            "fields": {
                "date": "date",
                "total_value": "number",
                "daily_pnl": "number",
                "cumulative_return": "number",
                "drawdown": "number"
            }
        },
        "risk_metrics": {
            "name": "Risk Metrics",
            "description": "Portfolio risk analytics",
            "fields": {
                "date": "date",
                "var_95": "number",
                "beta": "number",
                "sharpe_ratio": "number",
                "volatility": "number"
            }
        }
    }
    
    return {"data_sources": data_sources}