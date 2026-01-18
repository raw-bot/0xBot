import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext.js';
import LoginPage from './pages/auth/LoginPage.js';
import RegisterPage from './pages/auth/RegisterPage.js';
import DashboardPage from './pages/DashboardPage.js';
import BotDetailPage from './pages/BotDetailPage.js';
import HomePage from './pages/HomePage.js';

interface RouteGuardProps {
  children: React.ReactNode;
  requireAuth: boolean;
  redirectTo: string;
}

function RouteGuard({ children, requireAuth, redirectTo }: RouteGuardProps): JSX.Element {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  const shouldRedirect = requireAuth ? !isAuthenticated : isAuthenticated;
  if (shouldRedirect) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/login"
        element={
          <RouteGuard requireAuth={false} redirectTo="/dashboard">
            <LoginPage />
          </RouteGuard>
        }
      />
      <Route
        path="/register"
        element={
          <RouteGuard requireAuth={false} redirectTo="/dashboard">
            <RegisterPage />
          </RouteGuard>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RouteGuard requireAuth={true} redirectTo="/login">
            <DashboardPage />
          </RouteGuard>
        }
      />
      <Route
        path="/bots/:botId"
        element={
          <RouteGuard requireAuth={true} redirectTo="/login">
            <BotDetailPage />
          </RouteGuard>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App(): JSX.Element {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
