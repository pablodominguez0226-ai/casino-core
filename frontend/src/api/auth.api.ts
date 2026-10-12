import { apiClient } from "./client";
import {
  LoginPayload,
  RefreshTokenPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "../types/auth";

export const authApi = {
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>("/auth/login", payload);
    return response.data;
  },

  async register(payload: RegisterPayload): Promise<User> {
    const response = await apiClient.post<User>("/auth/register", payload);
    return response.data;
  },

  async refresh(payload: RefreshTokenPayload): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>("/auth/refresh", payload);
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>("/users/me");
    return response.data;
  },
};
