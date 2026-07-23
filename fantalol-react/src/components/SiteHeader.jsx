import {
  AppBar, Avatar, Box, Button, Container, IconButton, Tooltip, Typography,
} from '@mui/material';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useColorMode } from '../context/ThemeContext';

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Players', to: '/players' },
  { label: 'My leagues', to: '/leagues', private: true },
];

export function SiteHeader() {
  const { user, isAuthenticated, logout } = useAuth();
  const { mode, toggleMode } = useColorMode();
  const navigate = useNavigate();

  const signOut = () => {
    logout();
    navigate('/');
  };

  return (
    <AppBar position="sticky" color="transparent" elevation={0} className="site-header">
      <Container maxWidth="xl" className="header-inner">
        <NavLink to="/" className="brand">
          <Box className="brand-mark">F</Box>
          <Typography component="span">FANTA<span>LEAGUE</span></Typography>
        </NavLink>
        <Box component="nav" className="desktop-nav" aria-label="Primary navigation">
          {navItems.filter((item) => !item.private || isAuthenticated).map((item) => (
            <Button key={item.to} component={NavLink} to={item.to} className="nav-link">
              {item.label}
            </Button>
          ))}
        </Box>
        <Box className="header-actions">
          <Tooltip title={mode === 'dark' ? 'Use light theme' : 'Use dark theme'}>
            <IconButton onClick={toggleMode} aria-label="Toggle color theme">
              {mode === 'dark' ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Rules">
            <IconButton component={NavLink} to="/#rules" aria-label="Read the rules">
              <MenuBookOutlinedIcon />
            </IconButton>
          </Tooltip>
          {isAuthenticated ? (
            <>
              <Avatar className="user-avatar">{user.username[0].toUpperCase()}</Avatar>
              <Box className="user-copy">
                <Typography variant="body2" fontWeight={750}>{user.username}</Typography>
                <Typography variant="caption">{user.role}</Typography>
              </Box>
              <Button variant="outlined" onClick={signOut}>Sign out</Button>
            </>
          ) : (
            <Button variant="contained" component={NavLink} to="/login">Sign in</Button>
          )}
        </Box>
      </Container>
    </AppBar>
  );
}
