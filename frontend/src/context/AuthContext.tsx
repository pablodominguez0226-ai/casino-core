import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { authApi } from "../api/auth.api";
import {
  clearStoredTokens,
  getStoredAccessToken,
  setStoredTokens,
} from "../api/client";
import { LoginPayload, RegisterPayload, Role, User } from "../types/auth";

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  roles: Role[];
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
  hasRole: (role: Role) => boolean;
  hasAnyRole: (roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(getStoredAccessToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    clearStoredTokens();
    setUser(null);
    setAccessToken(null);
  }, []);

  const fetchCurrentUser = useCallback(async () => {
    try {
      const profile = await authApi.getMe();
      setUser(profile);
      setAccessToken(getStoredAccessToken());
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener("casinocore:unauthorized", handleUnauthorized);

    const token = getStoredAccessToken();
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }

    return () => {
      window.removeEventListener("casinocore:unauthorized", handleUnauthorized);
    };
  }, [fetchCurrentUser, logout]);

  const login = async (payload: LoginPayload): Promise<void> => {
    setIsLoading(true);
    try {
      const tokens = await authApi.login(payload);
      setStoredTokens(tokens.access_token, tokens.refresh_token);
      setAccessToken(tokens.access_token);
      const profile = await authApi.getMe();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload): Promise<User> => {
    return await authApi.register(payload);
  };

  const hasRole = (role: Role): boolean => {
    if (!user) return false;
    return user.roles.includes(role);
  };

  const hasAnyRole = (checkRoles: Role[]): boolean => {
    if (!user) return false;
    return checkRoles.some((r) => user.roles.includes(r));
  };

  const roles = user?.roles ?? [];
  const isAuthenticated = !!user && !!accessToken;

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated,
        roles,
        isLoading,
        login,
        register,
        logout,
        hasRole,
        hasAnyRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
