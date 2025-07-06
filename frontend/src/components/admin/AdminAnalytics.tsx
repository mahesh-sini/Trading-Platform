import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  ButtonGroup,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  People as UsersIcon,
  AttachMoney as RevenueIcon,
  ShowChart as TradingIcon,
  Speed as PerformanceIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  DateRange as DateRangeIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  ComposedChart,
  Legend
} from 'recharts';
import { useTheme } from '@mui/material/styles';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

// Types
interface AnalyticsData {
  users: UserAnalytics[];
  revenue: RevenueAnalytics[];
  trading: TradingAnalytics[];
  system: SystemMetrics[];
}

interface UserAnalytics {
  date: string;
  total_users: number;
  new_registrations: number;
  active_users_daily: number;
  churned_users: number;
}

interface RevenueAnalytics {
  date: string;
  daily_revenue: number;
  mrr: number;
  subscription_revenue: number;
  commission_revenue: number;
  costs: number;
}

interface TradingAnalytics {
  date: string;
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  total_volume: number;
  win_rate: number;
  avg_execution_time: number;
}

interface SystemMetrics {
  timestamp: string;
  api_response_time_avg: number;
  api_error_rate: number;
  active_user_sessions: number;
  websocket_connections: number;
}

const AdminAnalytics: React.FC = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [timeRange, setTimeRange] = useState('30');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [customDateRange, setCustomDateRange] = useState<{start: Date | null, end: Date | null}>({
    start: null,
    end: null
  });

  useEffect(() => {
    loadAnalyticsData();
  }, [timeRange]);

  const loadAnalyticsData = async () => {
    setLoading(true);
    try {
      const [userResponse, revenueResponse, tradingResponse] = await Promise.all([
        fetch(`/api/admin/analytics/users?days=${timeRange}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        }),
        fetch(`/api/admin/analytics/revenue?days=${timeRange}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        }),
        fetch(`/api/admin/analytics/trading?days=${timeRange}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        })
      ]);

      const userData = await userResponse.json();
      const revenueData = await revenueResponse.json();
      const tradingData = await tradingResponse.json();

      setData({
        users: userData.analytics,
        revenue: revenueData.analytics,
        trading: tradingData.analytics,
        system: [] // Would load from system metrics endpoint
      });
    } catch (error) {
      console.error('Failed to load analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportData = async (type: string) => {
    try {
      const response = await fetch(`/api/admin/analytics/export?type=${type}&days=${timeRange}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
      });
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_analytics_${timeRange}days.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const calculateGrowthRate = (current: number, previous: number): number => {
    if (previous === 0) return 0;
    return ((current - previous) / previous) * 100;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const getGrowthColor = (growth: number) => {
    if (growth > 0) return theme.palette.success.main;
    if (growth < 0) return theme.palette.error.main;
    return theme.palette.grey[500];
  };

  const getGrowthIcon = (growth: number) => {
    return growth >= 0 ? <TrendingUp /> : <TrendingDown />;
  };

  if (loading && !data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Analytics Dashboard
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {/* Time Range Selector */}
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value="7">Last 7 days</MenuItem>
              <MenuItem value="30">Last 30 days</MenuItem>
              <MenuItem value="90">Last 90 days</MenuItem>
              <MenuItem value="365">Last year</MenuItem>
            </Select>
          </FormControl>

          {/* Refresh Button */}
          <IconButton onClick={loadAnalyticsData} disabled={loading}>
            <RefreshIcon />
          </IconButton>

          {/* Export Button */}
          <Button
            startIcon={<DownloadIcon />}
            variant="outlined"
            onClick={() => exportData('all')}
          >
            Export
          </Button>
        </Box>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab icon={<UsersIcon />} label="User Analytics" />
          <Tab icon={<RevenueIcon />} label="Revenue Analytics" />
          <Tab icon={<TradingIcon />} label="Trading Analytics" />
          <Tab icon={<PerformanceIcon />} label="System Performance" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {activeTab === 0 && <UserAnalyticsTab data={data?.users || []} />}
      {activeTab === 1 && <RevenueAnalyticsTab data={data?.revenue || []} />}
      {activeTab === 2 && <TradingAnalyticsTab data={data?.trading || []} />}
      {activeTab === 3 && <SystemPerformanceTab data={data?.system || []} />}
    </Box>
  );
};

// User Analytics Tab
const UserAnalyticsTab: React.FC<{ data: UserAnalytics[] }> = ({ data }) => {
  const theme = useTheme();

  const latestData = data[data.length - 1];
  const previousData = data[data.length - 2];

  const metrics = [
    {
      title: 'Total Users',
      value: latestData?.total_users || 0,
      growth: previousData ? calculateGrowthRate(latestData?.total_users || 0, previousData.total_users) : 0,
      icon: <UsersIcon />
    },
    {
      title: 'New Registrations',
      value: latestData?.new_registrations || 0,
      growth: previousData ? calculateGrowthRate(latestData?.new_registrations || 0, previousData.new_registrations) : 0,
      icon: <TrendingUp />
    },
    {
      title: 'Daily Active Users',
      value: latestData?.active_users_daily || 0,
      growth: previousData ? calculateGrowthRate(latestData?.active_users_daily || 0, previousData.active_users_daily) : 0,
      icon: <UsersIcon />
    },
    {
      title: 'Churn Rate',
      value: latestData?.churned_users || 0,
      growth: previousData ? calculateGrowthRate(latestData?.churned_users || 0, previousData.churned_users) : 0,
      icon: <TrendingDown />
    }
  ];

  return (
    <Box>
      {/* Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: `${theme.palette.primary.main}20`,
                      color: theme.palette.primary.main,
                      mr: 2
                    }}
                  >
                    {metric.icon}
                  </Box>
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    {metric.title}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
                  {metric.value.toLocaleString()}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      color: getGrowthColor(metric.growth)
                    }}
                  >
                    {getGrowthIcon(metric.growth)}
                    <Typography variant="body2" sx={{ ml: 0.5 }}>
                      {formatPercentage(metric.growth)}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                    vs yesterday
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                User Growth Trend
              </Typography>
              <Box sx={{ height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date" 
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value, name) => [value.toLocaleString(), name]}
                    />
                    <Legend />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="total_users"
                      fill={theme.palette.primary.light}
                      stroke={theme.palette.primary.main}
                      name="Total Users"
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="new_registrations"
                      fill={theme.palette.success.main}
                      name="New Registrations"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                User Activity
              </Typography>
              <Box sx={{ height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Active', value: latestData?.active_users_daily || 0, color: theme.palette.success.main },
                        { name: 'Inactive', value: (latestData?.total_users || 0) - (latestData?.active_users_daily || 0), color: theme.palette.grey[400] }
                      ]}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

// Revenue Analytics Tab
const RevenueAnalyticsTab: React.FC<{ data: RevenueAnalytics[] }> = ({ data }) => {
  const theme = useTheme();

  const totalRevenue = data.reduce((sum, item) => sum + item.daily_revenue, 0);
  const totalCosts = data.reduce((sum, item) => sum + item.costs, 0);
  const profit = totalRevenue - totalCosts;
  const profitMargin = totalRevenue > 0 ? (profit / totalRevenue) * 100 : 0;

  return (
    <Box>
      {/* Revenue Summary */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Total Revenue
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: 'success.main' }}>
                {formatCurrency(totalRevenue)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Total Costs
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: 'error.main' }}>
                {formatCurrency(totalCosts)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Net Profit
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: profit >= 0 ? 'success.main' : 'error.main' }}>
                {formatCurrency(profit)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Profit Margin
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600 }}>
                {formatPercentage(profitMargin)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Revenue Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Revenue vs Costs Trend
              </Typography>
              <Box sx={{ height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value, name) => [formatCurrency(Number(value)), name]}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="daily_revenue"
                      fill={theme.palette.success.light}
                      stroke={theme.palette.success.main}
                      name="Revenue"
                    />
                    <Area
                      type="monotone"
                      dataKey="costs"
                      fill={theme.palette.error.light}
                      stroke={theme.palette.error.main}
                      name="Costs"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

// Trading Analytics Tab
const TradingAnalyticsTab: React.FC<{ data: TradingAnalytics[] }> = ({ data }) => {
  const theme = useTheme();

  const totalTrades = data.reduce((sum, item) => sum + item.total_trades, 0);
  const successfulTrades = data.reduce((sum, item) => sum + item.successful_trades, 0);
  const totalVolume = data.reduce((sum, item) => sum + item.total_volume, 0);
  const avgWinRate = data.length > 0 ? data.reduce((sum, item) => sum + item.win_rate, 0) / data.length : 0;

  return (
    <Box>
      {/* Trading Summary */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Total Trades
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600 }}>
                {totalTrades.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: 'success.main' }}>
                {formatPercentage(avgWinRate)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Total Volume
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600 }}>
                {formatCurrency(totalVolume)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Avg Execution Time
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 600 }}>
                {data.length > 0 ? 
                  `${(data.reduce((sum, item) => sum + item.avg_execution_time, 0) / data.length).toFixed(0)}ms`
                  : '0ms'
                }
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Trading Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Trading Volume Trend
              </Typography>
              <Box sx={{ height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <Legend />
                    <Bar
                      yAxisId="left"
                      dataKey="total_trades"
                      fill={theme.palette.primary.main}
                      name="Total Trades"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="win_rate"
                      stroke={theme.palette.success.main}
                      name="Win Rate (%)"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Trade Success Distribution
              </Typography>
              <Box sx={{ height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Successful', value: successfulTrades, color: theme.palette.success.main },
                        { name: 'Failed', value: totalTrades - successfulTrades, color: theme.palette.error.main }
                      ]}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

// System Performance Tab
const SystemPerformanceTab: React.FC<{ data: SystemMetrics[] }> = ({ data }) => {
  const theme = useTheme();

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 3 }}>
        System performance metrics are updated in real-time and show the last 24 hours of data.
      </Alert>
      
      {/* Performance indicators would go here */}
      <Card>
        <CardContent>
          <Typography variant="h6">
            System Performance Dashboard - Coming Soon
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This section will display real-time system metrics including API response times, 
            error rates, database performance, and infrastructure health.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

// Utility functions
const calculateGrowthRate = (current: number, previous: number): number => {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
};

const formatPercentage = (value: number) => {
  return `${value.toFixed(1)}%`;
};

const getGrowthColor = (growth: number) => {
  if (growth > 0) return '#4caf50';
  if (growth < 0) return '#f44336';
  return '#9e9e9e';
};

const getGrowthIcon = (growth: number) => {
  return growth >= 0 ? <TrendingUp /> : <TrendingDown />;
};

export default AdminAnalytics;