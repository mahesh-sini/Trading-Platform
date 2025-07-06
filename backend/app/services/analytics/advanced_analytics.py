"""
Advanced Analytics Service with Custom Dashboard Filters
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of analytics metrics"""
    PERFORMANCE = "performance"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    TRADING = "trading"
    MARKET = "market"
    CUSTOM = "custom"


class AggregationType(Enum):
    """Types of aggregations"""
    SUM = "sum"
    AVERAGE = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    STANDARD_DEVIATION = "std"
    VARIANCE = "var"
    CORRELATION = "corr"


class TimeFrame(Enum):
    """Time frame options"""
    REAL_TIME = "real_time"
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    HOURLY = "1h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1mo"
    QUARTERLY = "3mo"
    YEARLY = "1y"


@dataclass
class Filter:
    """Analytics filter definition"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, nin, contains, starts_with, ends_with
    value: Any
    data_type: str = "string"  # string, number, date, boolean, array


@dataclass
class MetricDefinition:
    """Custom metric definition"""
    name: str
    description: str
    metric_type: MetricType
    calculation_formula: str
    data_sources: List[str]
    aggregation: AggregationType
    time_frame: TimeFrame
    filters: List[Filter]
    custom_parameters: Optional[Dict[str, Any]] = None


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    widget_id: str
    widget_type: str  # chart, table, metric, heatmap, gauge
    title: str
    metric_definitions: List[MetricDefinition]
    visualization_config: Dict[str, Any]
    refresh_interval: int  # seconds
    position: Dict[str, int]  # x, y, width, height
    filters: List[Filter]


class AdvancedAnalyticsService:
    """Advanced analytics service with custom filtering and aggregation"""
    
    def __init__(self):
        self.custom_metrics: Dict[str, MetricDefinition] = {}
        self.dashboard_configs: Dict[str, List[DashboardWidget]] = {}
        self.data_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        
    async def register_custom_metric(self, metric: MetricDefinition) -> bool:
        """Register a custom metric definition"""
        try:
            # Validate metric definition
            if not self._validate_metric_definition(metric):
                raise ValueError(f"Invalid metric definition for {metric.name}")
            
            self.custom_metrics[metric.name] = metric
            logger.info(f"Registered custom metric: {metric.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register metric {metric.name}: {str(e)}")
            return False
    
    def _validate_metric_definition(self, metric: MetricDefinition) -> bool:
        """Validate metric definition"""
        # Check required fields
        if not metric.name or not metric.calculation_formula:
            return False
        
        # Validate calculation formula syntax
        try:
            # Basic syntax check - would need more sophisticated parsing in production
            if not any(source in metric.calculation_formula for source in metric.data_sources):
                return False
        except Exception:
            return False
        
        return True
    
    async def create_dashboard(
        self, 
        dashboard_id: str, 
        widgets: List[DashboardWidget],
        user_id: str,
        organization_id: str
    ) -> bool:
        """Create a custom dashboard"""
        try:
            # Validate widgets
            for widget in widgets:
                if not self._validate_widget(widget):
                    raise ValueError(f"Invalid widget configuration: {widget.widget_id}")
            
            self.dashboard_configs[dashboard_id] = widgets
            
            # Store dashboard configuration (would normally save to database)
            dashboard_config = {
                'dashboard_id': dashboard_id,
                'user_id': user_id,
                'organization_id': organization_id,
                'widgets': [self._widget_to_dict(widget) for widget in widgets],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            logger.info(f"Created dashboard: {dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create dashboard {dashboard_id}: {str(e)}")
            return False
    
    def _validate_widget(self, widget: DashboardWidget) -> bool:
        """Validate widget configuration"""
        # Check required fields
        if not widget.widget_id or not widget.widget_type or not widget.title:
            return False
        
        # Validate position
        required_position_keys = ['x', 'y', 'width', 'height']
        if not all(key in widget.position for key in required_position_keys):
            return False
        
        return True
    
    def _widget_to_dict(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Convert widget to dictionary"""
        return {
            'widget_id': widget.widget_id,
            'widget_type': widget.widget_type,
            'title': widget.title,
            'metric_definitions': [self._metric_to_dict(metric) for metric in widget.metric_definitions],
            'visualization_config': widget.visualization_config,
            'refresh_interval': widget.refresh_interval,
            'position': widget.position,
            'filters': [self._filter_to_dict(f) for f in widget.filters]
        }
    
    def _metric_to_dict(self, metric: MetricDefinition) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            'name': metric.name,
            'description': metric.description,
            'metric_type': metric.metric_type.value,
            'calculation_formula': metric.calculation_formula,
            'data_sources': metric.data_sources,
            'aggregation': metric.aggregation.value,
            'time_frame': metric.time_frame.value,
            'filters': [self._filter_to_dict(f) for f in metric.filters],
            'custom_parameters': metric.custom_parameters
        }
    
    def _filter_to_dict(self, filter_obj: Filter) -> Dict[str, Any]:
        """Convert filter to dictionary"""
        return {
            'field': filter_obj.field,
            'operator': filter_obj.operator,
            'value': filter_obj.value,
            'data_type': filter_obj.data_type
        }
    
    async def calculate_metric(
        self, 
        metric_name: str, 
        data: Dict[str, Any],
        additional_filters: Optional[List[Filter]] = None
    ) -> Dict[str, Any]:
        """Calculate a custom metric"""
        try:
            if metric_name not in self.custom_metrics:
                raise ValueError(f"Metric not found: {metric_name}")
            
            metric = self.custom_metrics[metric_name]
            
            # Apply filters
            filtered_data = await self._apply_filters(data, metric.filters + (additional_filters or []))
            
            # Calculate metric
            result = await self._execute_calculation(metric, filtered_data)
            
            return {
                'metric_name': metric_name,
                'value': result,
                'calculation_time': datetime.now(),
                'data_points': len(filtered_data) if isinstance(filtered_data, (list, pd.DataFrame)) else 1
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate metric {metric_name}: {str(e)}")
            raise
    
    async def _apply_filters(self, data: Dict[str, Any], filters: List[Filter]) -> Any:
        """Apply filters to data"""
        try:
            # Convert to DataFrame if it's not already
            if isinstance(data, dict) and 'records' in data:
                df = pd.DataFrame(data['records'])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                return data
            
            # Apply each filter
            for filter_obj in filters:
                df = self._apply_single_filter(df, filter_obj)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to apply filters: {str(e)}")
            return data
    
    def _apply_single_filter(self, df: pd.DataFrame, filter_obj: Filter) -> pd.DataFrame:
        """Apply a single filter to DataFrame"""
        if filter_obj.field not in df.columns:
            return df
        
        field = df[filter_obj.field]
        value = filter_obj.value
        
        # Convert value to appropriate type
        if filter_obj.data_type == "number":
            value = float(value) if not isinstance(value, (int, float)) else value
        elif filter_obj.data_type == "date":
            if isinstance(value, str):
                value = pd.to_datetime(value)
        
        # Apply operator
        if filter_obj.operator == "eq":
            mask = field == value
        elif filter_obj.operator == "ne":
            mask = field != value
        elif filter_obj.operator == "gt":
            mask = field > value
        elif filter_obj.operator == "lt":
            mask = field < value
        elif filter_obj.operator == "gte":
            mask = field >= value
        elif filter_obj.operator == "lte":
            mask = field <= value
        elif filter_obj.operator == "in":
            mask = field.isin(value if isinstance(value, list) else [value])
        elif filter_obj.operator == "nin":
            mask = ~field.isin(value if isinstance(value, list) else [value])
        elif filter_obj.operator == "contains":
            mask = field.str.contains(str(value), na=False)
        elif filter_obj.operator == "starts_with":
            mask = field.str.startswith(str(value), na=False)
        elif filter_obj.operator == "ends_with":
            mask = field.str.endswith(str(value), na=False)
        else:
            return df
        
        return df[mask]
    
    async def _execute_calculation(self, metric: MetricDefinition, data: Any) -> float:
        """Execute metric calculation"""
        try:
            if isinstance(data, pd.DataFrame):
                # Prepare calculation context
                context = {'data': data, 'pd': pd, 'np': np}
                
                # Add common functions
                context.update({
                    'sum': lambda col: data[col].sum() if col in data.columns else 0,
                    'avg': lambda col: data[col].mean() if col in data.columns else 0,
                    'count': lambda col: data[col].count() if col in data.columns else 0,
                    'min': lambda col: data[col].min() if col in data.columns else 0,
                    'max': lambda col: data[col].max() if col in data.columns else 0,
                    'std': lambda col: data[col].std() if col in data.columns else 0,
                    'var': lambda col: data[col].var() if col in data.columns else 0,
                    'median': lambda col: data[col].median() if col in data.columns else 0,
                    'percentile': lambda col, p: data[col].quantile(p/100) if col in data.columns else 0,
                    'corr': lambda col1, col2: data[col1].corr(data[col2]) if col1 in data.columns and col2 in data.columns else 0
                })
                
                # Add custom parameters
                if metric.custom_parameters:
                    context.update(metric.custom_parameters)
                
                # Execute formula safely
                result = eval(metric.calculation_formula, {"__builtins__": {}}, context)
                
                return float(result) if not pd.isna(result) else 0.0
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to execute calculation for {metric.name}: {str(e)}")
            return 0.0
    
    async def generate_dashboard_data(
        self, 
        dashboard_id: str,
        data_sources: Dict[str, Any],
        additional_filters: Optional[List[Filter]] = None
    ) -> Dict[str, Any]:
        """Generate data for dashboard widgets"""
        try:
            if dashboard_id not in self.dashboard_configs:
                raise ValueError(f"Dashboard not found: {dashboard_id}")
            
            widgets = self.dashboard_configs[dashboard_id]
            dashboard_data = {}
            
            for widget in widgets:
                widget_data = await self._generate_widget_data(
                    widget, 
                    data_sources, 
                    additional_filters
                )
                dashboard_data[widget.widget_id] = widget_data
            
            return {
                'dashboard_id': dashboard_id,
                'generated_at': datetime.now(),
                'widgets': dashboard_data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard data for {dashboard_id}: {str(e)}")
            raise
    
    async def _generate_widget_data(
        self, 
        widget: DashboardWidget,
        data_sources: Dict[str, Any],
        additional_filters: Optional[List[Filter]] = None
    ) -> Dict[str, Any]:
        """Generate data for a single widget"""
        try:
            widget_results = {}
            
            # Combine widget filters with additional filters
            all_filters = widget.filters + (additional_filters or [])
            
            for metric in widget.metric_definitions:
                # Get data for metric's data sources
                metric_data = {}
                for source in metric.data_sources:
                    if source in data_sources:
                        metric_data[source] = data_sources[source]
                
                # Calculate metric
                result = await self.calculate_metric(metric.name, metric_data, all_filters)
                widget_results[metric.name] = result
            
            # Format data based on widget type
            formatted_data = await self._format_widget_data(widget, widget_results)
            
            return {
                'widget_id': widget.widget_id,
                'widget_type': widget.widget_type,
                'title': widget.title,
                'data': formatted_data,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate widget data for {widget.widget_id}: {str(e)}")
            return {
                'widget_id': widget.widget_id,
                'error': str(e),
                'last_updated': datetime.now()
            }
    
    async def _format_widget_data(
        self, 
        widget: DashboardWidget, 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format widget data based on widget type"""
        try:
            if widget.widget_type == "metric":
                # Single value display
                metric_name = list(results.keys())[0] if results else "N/A"
                value = results[metric_name]['value'] if metric_name in results else 0
                
                return {
                    'value': value,
                    'format': widget.visualization_config.get('format', 'number'),
                    'unit': widget.visualization_config.get('unit', ''),
                    'precision': widget.visualization_config.get('precision', 2)
                }
            
            elif widget.widget_type == "chart":
                # Chart data
                chart_data = []
                for metric_name, result in results.items():
                    chart_data.append({
                        'label': metric_name,
                        'value': result['value'],
                        'timestamp': result['calculation_time']
                    })
                
                return {
                    'chart_type': widget.visualization_config.get('chart_type', 'line'),
                    'data': chart_data,
                    'x_axis': widget.visualization_config.get('x_axis', 'timestamp'),
                    'y_axis': widget.visualization_config.get('y_axis', 'value')
                }
            
            elif widget.widget_type == "table":
                # Table data
                table_rows = []
                for metric_name, result in results.items():
                    table_rows.append({
                        'metric': metric_name,
                        'value': result['value'],
                        'data_points': result['data_points'],
                        'last_calculated': result['calculation_time']
                    })
                
                return {
                    'columns': widget.visualization_config.get('columns', ['metric', 'value']),
                    'rows': table_rows,
                    'sortable': widget.visualization_config.get('sortable', True)
                }
            
            elif widget.widget_type == "gauge":
                # Gauge display
                metric_name = list(results.keys())[0] if results else "N/A"
                value = results[metric_name]['value'] if metric_name in results else 0
                
                return {
                    'value': value,
                    'min_value': widget.visualization_config.get('min_value', 0),
                    'max_value': widget.visualization_config.get('max_value', 100),
                    'thresholds': widget.visualization_config.get('thresholds', []),
                    'unit': widget.visualization_config.get('unit', '')
                }
            
            elif widget.widget_type == "heatmap":
                # Heatmap data
                heatmap_data = []
                for metric_name, result in results.items():
                    heatmap_data.append({
                        'x': metric_name,
                        'y': 'value',
                        'value': result['value']
                    })
                
                return {
                    'data': heatmap_data,
                    'color_scale': widget.visualization_config.get('color_scale', 'viridis')
                }
            
            else:
                # Default format
                return results
                
        except Exception as e:
            logger.error(f"Failed to format widget data: {str(e)}")
            return {'error': str(e)}
    
    async def get_available_metrics(self) -> List[Dict[str, Any]]:
        """Get list of available metrics"""
        metrics = []
        
        # Built-in metrics
        built_in_metrics = [
            {
                'name': 'portfolio_value',
                'description': 'Total portfolio value',
                'type': 'performance',
                'built_in': True
            },
            {
                'name': 'daily_pnl',
                'description': 'Daily profit and loss',
                'type': 'performance',
                'built_in': True
            },
            {
                'name': 'win_rate',
                'description': 'Percentage of winning trades',
                'type': 'trading',
                'built_in': True
            },
            {
                'name': 'sharpe_ratio',
                'description': 'Risk-adjusted return metric',
                'type': 'risk',
                'built_in': True
            },
            {
                'name': 'max_drawdown',
                'description': 'Maximum portfolio drawdown',
                'type': 'risk',
                'built_in': True
            }
        ]
        
        metrics.extend(built_in_metrics)
        
        # Custom metrics
        for metric_name, metric in self.custom_metrics.items():
            metrics.append({
                'name': metric.name,
                'description': metric.description,
                'type': metric.metric_type.value,
                'built_in': False,
                'aggregation': metric.aggregation.value,
                'time_frame': metric.time_frame.value
            })
        
        return metrics
    
    async def get_filter_suggestions(self, data_source: str) -> Dict[str, Any]:
        """Get filter suggestions for a data source"""
        # Mock filter suggestions - would analyze actual data in production
        filter_suggestions = {
            'trades': {
                'symbol': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'],
                'side': ['buy', 'sell'],
                'status': ['filled', 'cancelled', 'pending'],
                'asset_type': ['stock', 'option', 'etf']
            },
            'positions': {
                'symbol': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'],
                'asset_type': ['stock', 'option', 'etf'],
                'side': ['long', 'short']
            },
            'market_data': {
                'symbol': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'],
                'exchange': ['NASDAQ', 'NYSE', 'CBOE'],
                'sector': ['Technology', 'Healthcare', 'Finance']
            }
        }
        
        return filter_suggestions.get(data_source, {})


# Global analytics service instance
advanced_analytics = AdvancedAnalyticsService()