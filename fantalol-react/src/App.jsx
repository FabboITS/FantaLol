import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import { SiteHeader } from './components/SiteHeader';
import { SiteFooter } from './components/SiteFooter';
import { DemoBanner } from './components/DemoBanner';
import { LoadingState } from './components/LoadingState';
import { useAuth } from './context/AuthContext';

const HomePage = lazy(() => import('./pages/HomePage').then((module) => ({ default: module.HomePage })));
const PlayersPage = lazy(() => import('./pages/PlayersPage').then((module) => ({ default: module.PlayersPage })));
const LeaguesPage = lazy(() => import('./pages/LeaguesPage').then((module) => ({ default: module.LeaguesPage })));
const LeaguePage = lazy(() => import('./pages/LeaguePage').then((module) => ({ default: module.LeaguePage })));
const AuthPage = lazy(() => import('./pages/AuthPage').then((module) => ({ default: module.AuthPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })));

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  return isAuthenticated ? children : <Navigate to="/login" replace state={{ from: location }} />;
}

export function App() {
  return (
    <Box className="app-shell">
      <DemoBanner />
      <SiteHeader />
      <Box component="main" className="app-main">
        <Suspense fallback={<LoadingState />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/players" element={<PlayersPage />} />
            <Route path="/login" element={<AuthPage />} />
            <Route
              path="/leagues"
              element={<ProtectedRoute><LeaguesPage /></ProtectedRoute>}
            />
            <Route
              path="/leagues/:leagueId"
              element={<ProtectedRoute><LeaguePage /></ProtectedRoute>}
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </Box>
      <SiteFooter />
    </Box>
  );
}
