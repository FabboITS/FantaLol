import { createContext, useContext, useMemo, useState } from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';

const ColorModeContext = createContext(null);

export function AppThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem('fantalol_react_theme') || 'dark');
  const toggleMode = () => {
    setMode((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('fantalol_react_theme', next);
      return next;
    });
  };

  const theme = useMemo(() => createTheme({
    cssVariables: true,
    palette: {
      mode,
      primary: { main: mode === 'dark' ? '#a78bfa' : '#6d28d9' },
      secondary: { main: '#ec4899' },
      background: {
        default: mode === 'dark' ? '#0b0c12' : '#f7f5fb',
        paper: mode === 'dark' ? '#151720' : '#ffffff',
      },
    },
    typography: {
      fontFamily: '"Inter", "Segoe UI", sans-serif',
      h1: { fontWeight: 850, letterSpacing: '-0.055em' },
      h2: { fontWeight: 800, letterSpacing: '-0.04em' },
      h3: { fontWeight: 750, letterSpacing: '-0.025em' },
      button: { fontWeight: 750, textTransform: 'none' },
    },
    shape: { borderRadius: 16 },
    components: {
      MuiButton: { styleOverrides: { root: { borderRadius: 12, paddingInline: 18 } } },
      MuiCard: { styleOverrides: { root: { backgroundImage: 'none' } } },
    },
  }), [mode]);

  const value = useMemo(() => ({ mode, toggleMode }), [mode]);
  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export function useColorMode() {
  const context = useContext(ColorModeContext);
  if (!context) throw new Error('useColorMode must be used inside AppThemeProvider');
  return context;
}
