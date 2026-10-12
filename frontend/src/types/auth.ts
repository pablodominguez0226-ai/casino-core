export type Role =
  | "SUPER_ADMIN"
  | "OPERATOR_ADMIN"
  | "PLAYER"
  | "COMPLIANCE"
  | "FINANCE"
  | "GAME_MANAGER"
  | string;

export interface User {
  id: string;
  operator_id: string;
  email: string;
  is_active: boolean;
  roles: Role[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  operator_slug: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  operator_slug: string;
  username: string;
  first_name?: string;
  last_name?: string;
  birth_date?: string;
}

export interface RefreshTokenPayload {
  refresh_token: string;
}
