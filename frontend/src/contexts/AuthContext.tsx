import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setAuth: (user: User, token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

async function fetchAuth(endpoint: string, email: string, password: string): Promise<{ user: User; token: string }> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Authentication failed');
  }

  const data = await response.json();
  return {
    user: { id: data.id, email: data.email, created_at: data.created_at },
    token: data.token,
  };
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setAuth = (newUser: User, newToken: string): void => {
    setUser(newUser);
    setToken(newToken);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  };

  const clearAuth = (): void => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const { user, token } = await fetchAuth('/auth/login', email, password);
      setAuth(user, token);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const { user, token } = await fetchAuth('/auth/register', email, password);
      setAuth(user, token);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    setUser(null);
    setToken(null);
    clearAuth();
  };

  useEffect(() => {
    async function initializeAuth(): Promise<void> {
      try {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          return;
        }

        const autoLogin = import.meta.env.VITE_AUTO_LOGIN === 'true';
        const devEmail = import.meta.env.VITE_DEV_EMAIL;
        const devPassword = import.meta.env.VITE_DEV_PASSWORD;

        if (autoLogin && devEmail && devPassword) {
          console.log('Auto-login enabled...');
          const { user, token } = await fetchAuth('/auth/login', devEmail, devPassword);
          setAuth(user, token);
          console.log('Auto-login successful');
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        clearAuth();
      } finally {
        setIsLoading(false);
      }
    }

    initializeAuth();
  }, []);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    register,
    logout,
    setAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
