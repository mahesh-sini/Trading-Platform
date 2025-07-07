import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Alert,
  Collapse,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Tooltip,
  Badge
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  VisibilityOff as HideIcon,
  CheckCircle as HealthyIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Api as ApiIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
  Notifications as NotificationsIcon
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

// Types
interface APIConfig {
  id: string;
  provider: string;
  display_name: string;
  description: string;
  status: 'active' | 'inactive' | 'error' | 'testing' | 'rate_limited';
  is_enabled: boolean;
  base_url: string;
  rate_limit_per_minute: number;
  last_health_check: string | null;
  requests_today: number;
  success_rate: number;
  monthly_cost: number;
  plan_type: string;
  features_enabled: Record<string, boolean>;
  has_api_key: boolean;
  has_secret_key: boolean;
  api_key_preview: string;
  configured_by: string;
  last_modified: string;
}

interface SystemFeature {
  id: string;
  feature_name: string;
  display_name: string;
  description: string;
  is_enabled: boolean;
  required_apis: string[];
  optional_apis: string[];
  api_status: {
    all_required_healthy: boolean;
    missing_apis: string[];
    unhealthy_apis: string[];
  };
  can_enable: boolean;
  config_values: Record<string, any>;
  priority: number;
}

interface HealthOverview {
  system_status: 'healthy' | 'warning' | 'critical';
  apis: {
    total: number;
    healthy: number;
    unhealthy: number;
    health_percentage: number;
  };
  features: {
    enabled: number;
    available: number;
  };
  recent_activity: {
    health_checks_24h: number;
    failed_checks_24h: number;
  };
}

const SystemConfigPanel: React.FC = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [apis, setApis] = useState<Record<string, APIConfig[]>>({});
  const [features, setFeatures] = useState<Record<string, SystemFeature[]>>({});
  const [healthOverview, setHealthOverview] = useState<HealthOverview | null>(null);
  const [selectedApi, setSelectedApi] = useState<APIConfig | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [viewCredentials, setViewCredentials] = useState(false);
  const [testingApi, setTestingApi] = useState<string | null>(null);

  useEffect(() => {
    loadSystemData();
  }, []);

  const loadSystemData = async () => {
    setLoading(true);
    try {
      const [apisResponse, featuresResponse, healthResponse] = await Promise.all([
        fetch('/api/admin/system-config/apis', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        }),
        fetch('/api/admin/system-config/features', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        }),
        fetch('/api/admin/system-config/health/overview', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        })
      ]);

      const apisData = await apisResponse.json();
      const featuresData = await featuresResponse.json();
      const healthData = await healthResponse.json();

      setApis(apisData.apis_by_category);
      setFeatures(featuresData.features_by_category);
      setHealthOverview(healthData);
    } catch (error) {
      console.error('Failed to load system data:', error);
    } finally {
      setLoading(false);
    }
  };

  const testApiConnection = async (apiId: string) => {
    setTestingApi(apiId);
    try {
      const response = await fetch(`/api/admin/system-config/apis/${apiId}/test`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
      });
      
      const result = await response.json();
      
      // Refresh data to show updated status
      await loadSystemData();
      
      // Show result notification (you could use a toast library)
      console.log('Test result:', result);
    } catch (error) {
      console.error('API test failed:', error);
    } finally {
      setTestingApi(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return theme.palette.success.main;
      case 'error': return theme.palette.error.main;
      case 'warning': return theme.palette.warning.main;
      case 'inactive': return theme.palette.grey[500];
      case 'testing': return theme.palette.info.main;
      case 'rate_limited': return theme.palette.warning.main;
      default: return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <HealthyIcon />;
      case 'error': return <ErrorIcon />;
      case 'warning': return <WarningIcon />;
      default: return <ErrorIcon />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          System Configuration
        </Typography>
        <Button
          startIcon={<RefreshIcon />}
          onClick={loadSystemData}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {/* System Health Overview */}
      {healthOverview && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: `${getStatusColor(healthOverview.system_status)}20`,
                      color: getStatusColor(healthOverview.system_status),
                      mr: 2
                    }}
                  >
                    {getStatusIcon(healthOverview.system_status)}
                  </Box>
                  <Typography variant="h6">System Status</Typography>
                </Box>
                <Typography variant="h4" sx={{ 
                  fontWeight: 600, 
                  color: getStatusColor(healthOverview.system_status),
                  textTransform: 'capitalize'
                }}>
                  {healthOverview.system_status}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
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
                    <ApiIcon />
                  </Box>
                  <Typography variant="h6">APIs Health</Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
                  {healthOverview.apis.healthy}/{healthOverview.apis.total}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {healthOverview.apis.health_percentage.toFixed(1)}% healthy
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: `${theme.palette.success.main}20`,
                      color: theme.palette.success.main,
                      mr: 2
                    }}
                  >
                    <SettingsIcon />
                  </Box>
                  <Typography variant="h6">Features</Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
                  {healthOverview.features.enabled}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {healthOverview.features.available} available
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: `${theme.palette.info.main}20`,
                      color: theme.palette.info.main,
                      mr: 2
                    }}
                  >
                    <AssessmentIcon />
                  </Box>
                  <Typography variant="h6">Health Checks</Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
                  {healthOverview.recent_activity.health_checks_24h}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {healthOverview.recent_activity.failed_checks_24h} failed
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab icon={<ApiIcon />} label="API Management" />
          <Tab icon={<SettingsIcon />} label="System Features" />
          <Tab icon={<SpeedIcon />} label="Performance" />
          <Tab icon={<SecurityIcon />} label="Security" />
        </Tabs>
      </Paper>

      {/* API Management Tab */}
      {activeTab === 0 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h5">API Configurations</Typography>
            <Button
              startIcon={<AddIcon />}
              variant="contained"
              onClick={() => setConfigDialogOpen(true)}
            >
              Add API
            </Button>
          </Box>

          {Object.entries(apis).map(([category, categoryApis]) => (
            <Accordion key={category} defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6" sx={{ textTransform: 'capitalize', fontWeight: 600 }}>
                  {category.replace('_', ' ')} ({categoryApis.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Provider</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Health</TableCell>
                        <TableCell>Usage Today</TableCell>
                        <TableCell>Monthly Cost</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {categoryApis.map((api) => (
                        <TableRow key={api.id}>
                          <TableCell>
                            <Box>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                {api.display_name}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {api.description}
                              </Typography>
                              <Box sx={{ mt: 1 }}>
                                <Chip
                                  size="small"
                                  label={api.plan_type}
                                  variant="outlined"
                                />
                              </Box>
                            </Box>
                          </TableCell>
                          
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Switch
                                checked={api.is_enabled}
                                size="small"
                                onChange={() => {
                                  // Handle enable/disable
                                }}
                              />
                              <Chip
                                size="small"
                                label={api.status}
                                sx={{
                                  bgcolor: `${getStatusColor(api.status)}20`,
                                  color: getStatusColor(api.status),
                                  textTransform: 'capitalize'
                                }}
                              />
                            </Box>
                          </TableCell>
                          
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box
                                sx={{
                                  color: getStatusColor(api.status)
                                }}
                              >
                                {getStatusIcon(api.status)}
                              </Box>
                              <Box>
                                <Typography variant="body2">
                                  {api.success_rate.toFixed(1)}% success
                                </Typography>
                                {api.last_health_check && (
                                  <Typography variant="caption" color="text.secondary">
                                    Last: {new Date(api.last_health_check).toLocaleString()}
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                          </TableCell>
                          
                          <TableCell>
                            <Typography variant="body2">
                              {api.requests_today.toLocaleString()} requests
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {api.rate_limit_per_minute}/min limit
                            </Typography>
                          </TableCell>
                          
                          <TableCell>
                            <Typography variant="body2">
                              {formatCurrency(api.monthly_cost)}
                            </Typography>
                          </TableCell>
                          
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Tooltip title="Test Connection">
                                <span>
                                  <Button
                                    size="small"
                                    onClick={() => testApiConnection(api.id)}
                                    disabled={!api.is_enabled || testingApi === api.id}
                                  >
                                    {testingApi === api.id ? <CircularProgress size={16} /> : <SpeedIcon fontSize="small" />}
                                  </Button>
                                </span>
                              </Tooltip>
                              
                              <Tooltip title="Edit Configuration">
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    setSelectedApi(api);
                                    setConfigDialogOpen(true);
                                  }}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              
                              <Tooltip title="View Details">
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    // Navigate to detailed view
                                  }}
                                >
                                  <ViewIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}

      {/* System Features Tab */}
      {activeTab === 1 && (
        <Box>
          <Typography variant="h5" sx={{ mb: 3 }}>
            System Features
          </Typography>

          {Object.entries(features).map(([category, categoryFeatures]) => (
            <Accordion key={category} defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6" sx={{ textTransform: 'capitalize', fontWeight: 600 }}>
                  {category.replace('_', ' ')} ({categoryFeatures.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  {categoryFeatures.map((feature) => (
                    <Grid item xs={12} md={6} lg={4} key={feature.id}>
                      <Card sx={{ height: '100%' }}>
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              {feature.display_name}
                            </Typography>
                            <Switch
                              checked={feature.is_enabled}
                              disabled={!feature.can_enable}
                              onChange={() => {
                                // Handle feature toggle
                              }}
                            />
                          </Box>
                          
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {feature.description}
                          </Typography>

                          {/* API Requirements */}
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>
                              Required APIs:
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {feature.required_apis.map((api) => (
                                <Chip
                                  key={api}
                                  size="small"
                                  label={api}
                                  color={
                                    feature.api_status.missing_apis.includes(api) ? 'error' :
                                    feature.api_status.unhealthy_apis.includes(api) ? 'warning' :
                                    'success'
                                  }
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>

                          {/* Status Alerts */}
                          {!feature.can_enable && (
                            <Alert severity="warning" sx={{ mt: 1 }}>
                              {feature.api_status.missing_apis.length > 0 && (
                                <>Missing APIs: {feature.api_status.missing_apis.join(', ')}</>
                              )}
                              {feature.api_status.unhealthy_apis.length > 0 && (
                                <>Unhealthy APIs: {feature.api_status.unhealthy_apis.join(', ')}</>
                              )}
                            </Alert>
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}

      {/* Performance Tab */}
      {activeTab === 2 && (
        <Box>
          <Typography variant="h5" sx={{ mb: 3 }}>
            Performance Monitoring
          </Typography>
          
          <Alert severity="info">
            Performance monitoring dashboard with real-time metrics, API response times, 
            usage analytics, and cost optimization recommendations.
          </Alert>
        </Box>
      )}

      {/* Security Tab */}
      {activeTab === 3 && (
        <Box>
          <Typography variant="h5" sx={{ mb: 3 }}>
            Security Management
          </Typography>
          
          <Alert severity="info">
            Security management panel for API key rotation, access logs, 
            security alerts, and compliance monitoring.
          </Alert>
        </Box>
      )}

      {/* API Configuration Dialog */}
      <Dialog
        open={configDialogOpen}
        onClose={() => {
          setConfigDialogOpen(false);
          setSelectedApi(null);
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedApi ? 'Edit API Configuration' : 'Add New API Configuration'}
        </DialogTitle>
        <DialogContent>
          <APIConfigurationForm
            api={selectedApi}
            onSave={() => {
              setConfigDialogOpen(false);
              setSelectedApi(null);
              loadSystemData();
            }}
            viewCredentials={viewCredentials}
            setViewCredentials={setViewCredentials}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

// API Configuration Form Component
const APIConfigurationForm: React.FC<{
  api: APIConfig | null;
  onSave: () => void;
  viewCredentials: boolean;
  setViewCredentials: (view: boolean) => void;
}> = ({ api, onSave, viewCredentials, setViewCredentials }) => {
  const [formData, setFormData] = useState({
    provider: '',
    display_name: '',
    description: '',
    api_key: '',
    secret_key: '',
    base_url: '',
    rate_limit_per_minute: 60,
    plan_type: 'free',
    is_enabled: false
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (api) {
      setFormData({
        provider: api.provider,
        display_name: api.display_name,
        description: api.description,
        api_key: '', // Don't populate for security
        secret_key: '', // Don't populate for security
        base_url: api.base_url,
        rate_limit_per_minute: api.rate_limit_per_minute,
        plan_type: api.plan_type,
        is_enabled: api.is_enabled
      });
    }
  }, [api]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = api ? 'PUT' : 'POST';
      const url = api ? `/api/admin/system-config/apis/${api.id}` : '/api/admin/system-config/apis';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        onSave();
      }
    } catch (error) {
      console.error('Failed to save API configuration:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ pt: 2 }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Provider"
            select
            value={formData.provider}
            onChange={(e) => setFormData(prev => ({ ...prev, provider: e.target.value }))}
            SelectProps={{
              native: true
            }}
          >
            <option value="">Select Provider</option>
            <optgroup label="Market Data">
              <option value="alpha_vantage">Alpha Vantage</option>
              <option value="polygon">Polygon.io</option>
              <option value="yahoo_finance">Yahoo Finance</option>
              <option value="finnhub">Finnhub</option>
              <option value="iex_cloud">IEX Cloud</option>
            </optgroup>
            <optgroup label="Indian Markets">
              <option value="nse_official">NSE Official</option>
              <option value="bse_official">BSE Official</option>
            </optgroup>
            <optgroup label="News & Sentiment">
              <option value="news_api">News API</option>
              <option value="twitter_api">Twitter API</option>
            </optgroup>
            <optgroup label="AI/ML Services">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="google_ai">Google AI</option>
            </optgroup>
            <optgroup label="Communication">
              <option value="sendgrid">SendGrid</option>
              <option value="twilio">Twilio</option>
              <option value="aws_ses">AWS SES</option>
            </optgroup>
          </TextField>
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Display Name"
            value={formData.display_name}
            onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
          />
        </Grid>

        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Description"
            multiline
            rows={2}
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="API Key"
            type={viewCredentials ? 'text' : 'password'}
            value={formData.api_key}
            onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
            InputProps={{
              endAdornment: (
                <IconButton onClick={() => setViewCredentials(!viewCredentials)}>
                  {viewCredentials ? <HideIcon /> : <ViewIcon />}
                </IconButton>
              )
            }}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Secret Key"
            type={viewCredentials ? 'text' : 'password'}
            value={formData.secret_key}
            onChange={(e) => setFormData(prev => ({ ...prev, secret_key: e.target.value }))}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Base URL"
            value={formData.base_url}
            onChange={(e) => setFormData(prev => ({ ...prev, base_url: e.target.value }))}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Rate Limit (per minute)"
            type="number"
            value={formData.rate_limit_per_minute}
            onChange={(e) => setFormData(prev => ({ ...prev, rate_limit_per_minute: parseInt(e.target.value) }))}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Plan Type"
            select
            value={formData.plan_type}
            onChange={(e) => setFormData(prev => ({ ...prev, plan_type: e.target.value }))}
            SelectProps={{
              native: true
            }}
          >
            <option value="free">Free</option>
            <option value="basic">Basic</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </TextField>
        </Grid>

        <Grid item xs={12} md={6}>
          <FormControlLabel
            control={
              <Switch
                checked={formData.is_enabled}
                onChange={(e) => setFormData(prev => ({ ...prev, is_enabled: e.target.checked }))}
              />
            }
            label="Enable API"
          />
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
        <Button onClick={() => onSave()}>
          Cancel
        </Button>
        <Button
          variant="contained"
          disabled={saving}
          onClick={handleSave}
          startIcon={saving ? <CircularProgress size={16} /> : undefined}
        >
          {api ? 'Update' : 'Create'}
        </Button>
      </Box>
    </Box>
  );
};

export default SystemConfigPanel;