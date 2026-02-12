import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getMe } from '../services/auth';
import type { User, UserStats } from '../types';

interface AuthContextValue {
  user: User | null;
  stats: UserStats | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  stats: null,
  isAuthenticated: false,
  isLoading: true,
  refreshAuth: async () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAuth = async () => {
    try {
      const data = await getMe();
      setUser(data.user);
      setStats(data.stats);
    } catch {
      setUser(null);
      setStats(null);
    }
  };

  const refreshAuth = async () => {
    await fetchAuth();
  };

  useEffect(() => {
    fetchAuth().finally(() => setIsLoading(false));
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, stats, isAuthenticated: !!user, isLoading, refreshAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
