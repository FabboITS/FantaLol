import { useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Container, Tab, Tabs, TextField, Typography,
} from '@mui/material';
import SportsEsportsOutlinedIcon from '@mui/icons-material/SportsEsportsOutlined';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isDemoMode } from '../services/api';

export function AuthPage() {
  const { isAuthenticated, login, register, loading } = useAuth();
  const [mode, setMode] = useState('login');
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();

  if (isAuthenticated) return <Navigate to="/leagues" replace />;

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (mode === 'login') await login(values);
      else await register(values);
      navigate(location.state?.from?.pathname || '/leagues', { replace: true });
    } catch (reason) {
      setError(reason.message);
    }
  };

  return (
    <Container maxWidth="sm" className="auth-page">
      <Card className="auth-card">
        <CardContent>
          <Box className="auth-icon"><SportsEsportsOutlinedIcon /></Box>
          <Typography className="eyebrow">WELCOME, SUMMONER</Typography>
          <Typography variant="h3">Enter the arena.</Typography>
          <Tabs value={mode} onChange={(_event, value) => { setMode(value); setError(''); }} variant="fullWidth">
            <Tab label="Sign in" value="login" />
            <Tab label="Create account" value="register" />
          </Tabs>
          {isDemoMode && (
            <Alert severity="info">Demo credentials: <strong>demo</strong> / <strong>demo123</strong></Alert>
          )}
          {error && <Alert severity="error">{error}</Alert>}
          <Box component="form" onSubmit={submit} className="auth-form">
            <TextField name="username" label="Username" required inputProps={{ minLength: 3 }} />
            {mode === 'register' && <TextField name="email" label="Email" type="email" required />}
            <TextField name="password" label="Password" type="password" required inputProps={{ minLength: 6 }} />
            <Button type="submit" variant="contained" size="large" disabled={loading}>
              {loading ? 'Entering…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}
