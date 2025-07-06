import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  AppBar,
  Toolbar,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as UsersIcon,
  AttachMoney as RevenueIcon,
  TrendingUp as TradingIcon,
  Support as SupportIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Analytics as AnalyticsIcon,
  ContentPaste as ContentIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountIcon,
  ExitToApp as LogoutIcon,
  AdminPanelSettings as AdminIcon
} from '@mui/icons-material';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import SystemConfigPanel from './SystemConfigPanel';

// Types
interface DashboardOverview {
  users: {
    total: number;
    new_today: number;
    active_today: number;
  };
  revenue: {
    daily: number;
    mrr: number;
    arr: number;
  };
  trading: {
    trades_today: number;
    success_rate: number;
    total_volume: number;
  };
  system: {
    api_response_time: number;
    active_sessions: number;
    system_status: string;
  };
  support: {
    pending_tickets: number;
    unread_notifications: number;
  };
}

interface AdminUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  department: string;
  permissions: string[];
  last_login: string;
}

// Main Admin Dashboard Component
const AdminDashboard: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [currentAdmin, setCurrentAdmin] = useState<AdminUser | null>(null);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [notificationAnchor, setNotificationAnchor] = useState<null | HTMLElement>(null);

  const drawerWidth = 280;

  useEffect(() => {
    loadDashboardData();
    loadCurrentAdmin();
  }, []);

  const loadDashboardData = async () => {
    try {
      const response = await fetch('/api/admin/dashboard/overview', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
        }
      });
      const data = await response.json();
      setOverview(data.overview);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  const loadCurrentAdmin = async () => {
    try {
      const response = await fetch('/api/admin/auth/me', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
        }
      });
      const data = await response.json();
      setCurrentAdmin(data.admin);
    } catch (error) {
      console.error('Failed to load admin info:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/admin/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
        }
      });
      localStorage.removeItem('adminToken');
      window.location.href = '/admin/login';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <DashboardIcon />, permission: 'VIEW_DASHBOARD' },
    { id: 'users', label: 'User Management', icon: <UsersIcon />, permission: 'VIEW_USERS' },
    { id: 'subscriptions', label: 'Subscriptions', icon: <RevenueIcon />, permission: 'VIEW_SUBSCRIPTIONS' },
    { id: 'trading', label: 'Trading Operations', icon: <TradingIcon />, permission: 'VIEW_TRADING' },
    { id: 'analytics', label: 'Analytics', icon: <AnalyticsIcon />, permission: 'VIEW_ANALYTICS' },
    { id: 'system-config', label: 'System Configuration', icon: <SettingsIcon />, permission: 'MANAGE_SYSTEM_CONFIG' },
    { id: 'support', label: 'Support Tickets', icon: <SupportIcon />, permission: 'VIEW_SUPPORT' },
    { id: 'content', label: 'Content Management', icon: <ContentIcon />, permission: 'MANAGE_CONTENT' },
    { id: 'security', label: 'Security', icon: <SecurityIcon />, permission: 'VIEW_SECURITY' }
  ];

  const hasPermission = (permission: string): boolean => {
    if (!currentAdmin) return false;
    return currentAdmin.permissions.includes('ALL') || currentAdmin.permissions.includes(permission);
  };

  const filteredMenuItems = menuItems.filter(item => hasPermission(item.permission));

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return theme.palette.success.main;
      case 'warning': return theme.palette.warning.main;
      case 'error': return theme.palette.error.main;
      default: return theme.palette.grey[500];
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-IN').format(num);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'grey.50' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: 'white',
          color: 'text.primary',
          boxShadow: 1
        }}
      >
        <Toolbar>
          <IconButton
            edge="start"
            onClick={() => setDrawerOpen(!drawerOpen)}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
            Trading Platform Admin
          </Typography>

          {/* Notifications */}
          <IconButton
            onClick={(e) => setNotificationAnchor(e.currentTarget)}
            sx={{ mr: 1 }}
          >
            <Badge 
              badgeContent={overview?.support.unread_notifications || 0} 
              color="error"
            >
              <NotificationsIcon />
            </Badge>
          </IconButton>

          {/* Admin Profile Menu */}
          <Button
            onClick={(e) => setAnchorEl(e.currentTarget)}
            startIcon={<Avatar sx={{ width: 32, height: 32 }} />}
            sx={{ textTransform: 'none', color: 'text.primary' }}
          >
            {currentAdmin?.first_name || currentAdmin?.username}
          </Button>
          
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
          >
            <MenuItem>
              <ListItemIcon><AccountIcon /></ListItemIcon>
              Profile
            </MenuItem>
            <MenuItem>
              <ListItemIcon><SettingsIcon /></ListItemIcon>
              Settings
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><LogoutIcon /></ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Drawer
        variant={isMobile ? 'temporary' : 'permanent'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            borderRight: '1px solid',
            borderColor: 'divider'
          }
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
          <AdminIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Admin Panel
          </Typography>
        </Box>
        
        <Divider />
        
        <List sx={{ p: 1 }}>
          {filteredMenuItems.map((item) => (
            <ListItem
              key={item.id}
              button
              selected={activeTab === item.id}
              onClick={() => {
                setActiveTab(item.id);
                if (isMobile) setDrawerOpen(false);
              }}
              sx={{
                borderRadius: 1,
                mb: 0.5,
                '&.Mui-selected': {
                  bgcolor: 'primary.light',
                  color: 'primary.main',
                  '& .MuiListItemIcon-root': {
                    color: 'primary.main'
                  }
                }
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: 8
        }}
      >
        {activeTab === 'dashboard' && <DashboardOverviewContent overview={overview} />}
        {activeTab === 'users' && <UserManagementContent />}
        {activeTab === 'subscriptions' && <SubscriptionManagementContent />}
        {activeTab === 'trading' && <TradingOperationsContent />}
        {activeTab === 'analytics' && <AnalyticsContent />}
        {activeTab === 'system-config' && <SystemConfigPanel />}
        {activeTab === 'support' && <SupportTicketsContent />}
        {activeTab === 'content' && <ContentManagementContent />}
        {activeTab === 'security' && <SecurityContent />}
      </Box>
    </Box>
  );
};

// Dashboard Overview Content Component
const DashboardOverviewContent: React.FC<{ overview: DashboardOverview | null }> = ({ overview }) => {
  const theme = useTheme();

  if (!overview) {
    return <Typography>Loading dashboard data...</Typography>;
  }

  const metricCards = [
    {
      title: 'Total Users',
      value: formatNumber(overview.users.total),
      change: `+${overview.users.new_today} today`,
      icon: <UsersIcon />,
      color: theme.palette.primary.main
    },
    {
      title: 'Monthly Revenue',
      value: formatCurrency(overview.revenue.mrr),
      change: formatCurrency(overview.revenue.daily) + ' today',
      icon: <RevenueIcon />,
      color: theme.palette.success.main
    },
    {
      title: 'Trades Today',
      value: formatNumber(overview.trading.trades_today),
      change: `${(overview.trading.success_rate * 100).toFixed(1)}% success rate`,
      icon: <TradingIcon />,
      color: theme.palette.info.main
    },
    {
      title: 'System Status',
      value: overview.system.system_status.toUpperCase(),
      change: `${overview.system.api_response_time}ms avg response`,
      icon: <SecurityIcon />,
      color: getStatusColor(overview.system.system_status)
    }
  ];

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
        Dashboard Overview
      </Typography>

      {/* Metric Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {metricCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: `${card.color}20`,
                      color: card.color,
                      mr: 2
                    }}
                  >
                    {card.icon}
                  </Box>
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    {card.title}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
                  {card.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {card.change}
                </Typography>
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
                Revenue Trend (Last 30 Days)
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={generateMockData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value) => formatCurrency(value as number)} />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke={theme.palette.primary.main}
                      fill={theme.palette.primary.light}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                User Distribution
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Free', value: 45, color: theme.palette.grey[400] },
                        { name: 'Basic', value: 30, color: theme.palette.primary.main },
                        { name: 'Pro', value: 20, color: theme.palette.success.main },
                        { name: 'Enterprise', value: 5, color: theme.palette.warning.main }
                      ]}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {[].map((entry, index) => (
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

// Placeholder components for other tabs
const UserManagementContent: React.FC = () => (
  <Typography variant="h4">User Management - Coming Soon</Typography>
);

const SubscriptionManagementContent: React.FC = () => (
  <Typography variant="h4">Subscription Management - Coming Soon</Typography>
);

const TradingOperationsContent: React.FC = () => (
  <Typography variant="h4">Trading Operations - Coming Soon</Typography>
);

const AnalyticsContent: React.FC = () => (
  <Typography variant="h4">Analytics - Coming Soon</Typography>
);

const SupportTicketsContent: React.FC = () => (
  <Typography variant="h4">Support Tickets - Coming Soon</Typography>
);

const SecurityContent: React.FC = () => (
  <Typography variant="h4">Security - Coming Soon</Typography>
);

const ContentManagementContent: React.FC = () => (
  <Typography variant="h4">Content Management - Coming Soon</Typography>
);

// Utility functions
const getStatusColor = (status: string) => {
  switch (status) {
    case 'healthy': return '#4caf50';
    case 'warning': return '#ff9800';
    case 'error': return '#f44336';
    default: return '#9e9e9e';
  }
};

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR'
  }).format(amount);
};

const formatNumber = (num: number) => {
  return new Intl.NumberFormat('en-IN').format(num);
};

const generateMockData = () => {
  const data = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
      revenue: Math.floor(Math.random() * 100000) + 50000,
      users: Math.floor(Math.random() * 500) + 100
    });
  }
  return data;
};

export default AdminDashboard;