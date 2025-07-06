import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  Paper,
  Container,
  Avatar,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  AdminPanelSettings as AdminIcon,
  Security as SecurityIcon,
  Lock as LockIcon
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

interface LoginResponse {
  success: boolean;
  token?: string;
  admin?: {
    id: string;
    username: string;
    email: string;
    role: string;
    permissions: string[];
  };
  session?: {
    id: string;
    expires_at: string;
  };
  message?: string;
  error_code?: string;
  requires_mfa?: boolean;
}

const AdminLogin: React.FC = () => {
  const theme = useTheme();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    mfaToken: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [requiresMfa, setRequiresMfa] = useState(false);
  const [mfaDialogOpen, setMfaDialogOpen] = useState(false);
  const [loginAttempts, setLoginAttempts] = useState(0);

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
    setError(''); // Clear error when user starts typing
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!formData.username.trim() || !formData.password.trim()) {
      setError('Please enter both username and password');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/admin/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: formData.username.trim(),
          password: formData.password,
          mfa_token: formData.mfaToken || undefined
        })
      });

      const data: LoginResponse = await response.json();

      if (data.success) {
        // Store auth token
        localStorage.setItem('adminToken', data.token!);
        localStorage.setItem('adminUser', JSON.stringify(data.admin));
        
        setSuccess('Login successful! Redirecting...');
        setTimeout(() => {
          window.location.href = '/admin/dashboard';
        }, 1500);
      } else {
        if (data.requires_mfa && !requiresMfa) {
          setRequiresMfa(true);
          setMfaDialogOpen(true);
          setError('');
        } else {
          setError(data.message || 'Login failed');
          setLoginAttempts(prev => prev + 1);
          
          // Clear password on failed attempt
          setFormData(prev => ({ ...prev, password: '', mfaToken: '' }));
          
          // Show account lockout warning
          if (data.error_code === 'ACCOUNT_LOCKED') {
            setError('Account has been locked due to multiple failed login attempts. Please contact your administrator.');
          } else if (loginAttempts >= 3) {
            setError('Multiple failed attempts detected. Account may be locked after 5 failed attempts.');
          }
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = () => {
    if (!formData.mfaToken.trim()) {
      setError('Please enter your MFA code');
      return;
    }
    
    setMfaDialogOpen(false);
    handleLogin(new Event('submit') as any);
  };

  const validateMfaToken = (token: string) => {
    // Basic validation for 6-digit MFA token
    return /^\d{6}$/.test(token);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${theme.palette.primary.main}20, ${theme.palette.secondary.main}20)`,
        p: 2
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={8}
          sx={{
            borderRadius: 3,
            overflow: 'hidden'
          }}
        >
          {/* Header */}
          <Box
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              p: 3,
              textAlign: 'center'
            }}
          >
            <Avatar
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                width: 64,
                height: 64,
                mx: 'auto',
                mb: 2
              }}
            >
              <AdminIcon sx={{ fontSize: 40 }} />
            </Avatar>
            <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
              Admin Panel
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              Trading Platform Administration
            </Typography>
          </Box>

          {/* Login Form */}
          <CardContent sx={{ p: 4 }}>
            {loading && <LinearProgress sx={{ mb: 2 }} />}
            
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 3 }}>
                {success}
              </Alert>
            )}

            <form onSubmit={handleLogin}>
              <TextField
                fullWidth
                label="Username or Email"
                variant="outlined"
                value={formData.username}
                onChange={handleInputChange('username')}
                disabled={loading}
                sx={{ mb: 3 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <AdminIcon color="action" />
                    </InputAdornment>
                  )
                }}
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                variant="outlined"
                value={formData.password}
                onChange={handleInputChange('password')}
                disabled={loading}
                sx={{ mb: 3 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockIcon color="action" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading || !formData.username.trim() || !formData.password.trim()}
                sx={{
                  py: 1.5,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  textTransform: 'none'
                }}
              >
                {loading ? 'Signing In...' : 'Sign In'}
              </Button>
            </form>

            {/* Security Notice */}
            <Box
              sx={{
                mt: 4,
                p: 2,
                bgcolor: 'grey.50',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'grey.200'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <SecurityIcon sx={{ mr: 1, color: 'warning.main', fontSize: '1.2rem' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Security Notice
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                • All admin actions are logged and monitored
                <br />
                • Maximum 5 login attempts before account lockout
                <br />
                • Session will expire after inactivity
                <br />
                • Use only authorized devices and networks
              </Typography>
            </Box>

            {/* Login Attempts Warning */}
            {loginAttempts > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {5 - loginAttempts} login attempts remaining before account lockout
              </Alert>
            )}
          </CardContent>
        </Paper>
      </Container>

      {/* MFA Dialog */}
      <Dialog
        open={mfaDialogOpen}
        onClose={() => setMfaDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: 'center' }}>
          <SecurityIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="h6">Multi-Factor Authentication</Typography>
        </DialogTitle>
        
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
            Enter the 6-digit code from your authenticator app
          </Typography>
          
          <TextField
            fullWidth
            label="MFA Code"
            variant="outlined"
            value={formData.mfaToken}
            onChange={handleInputChange('mfaToken')}
            placeholder="000000"
            inputProps={{
              maxLength: 6,
              pattern: '[0-9]*',
              inputMode: 'numeric'
            }}
            error={formData.mfaToken.length > 0 && !validateMfaToken(formData.mfaToken)}
            helperText={
              formData.mfaToken.length > 0 && !validateMfaToken(formData.mfaToken)
                ? 'Please enter a valid 6-digit code'
                : ''
            }
            sx={{
              '& input': {
                textAlign: 'center',
                fontSize: '1.5rem',
                letterSpacing: '0.5rem'
              }
            }}
          />
        </DialogContent>
        
        <DialogActions sx={{ p: 3, pt: 1 }}>
          <Button
            onClick={() => {
              setMfaDialogOpen(false);
              setRequiresMfa(false);
              setFormData(prev => ({ ...prev, mfaToken: '' }));
            }}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleMfaSubmit}
            variant="contained"
            disabled={loading || !validateMfaToken(formData.mfaToken)}
            sx={{ ml: 1 }}
          >
            {loading ? 'Verifying...' : 'Verify'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminLogin;