export type GameType = "SLOT" | "ROULETTE" | "BLACKJACK";

export type GameSessionStatus = "ACTIVE" | "CLOSED" | "CANCELLED";

export type SlotSymbol = "CHERRY" | "LEMON" | "ORANGE" | "BELL" | "SEVEN";

export interface Game {
  id: string;
  code: string;
  name: string;
  game_type: GameType;
  min_bet: number;
  max_bet: number;
  is_active: boolean;
}

export interface GameSession {
  id: string;
  game_id: string;
  user_id: string;
  status: GameSessionStatus;
  started_at: string;
  ended_at?: string | null;
}

export interface SpinRequest {
  bet_amount: number;
}

export interface SpinResponse {
  round_id: string;
  symbols: string[];
  bet_amount: number;
  payout_amount: number;
  is_win: boolean;
  current_balance: number;
}

export interface GameRound {
  id: string;
  session_id: string;
  bet_amount: number;
  payout_amount: number;
  round_data: Record<string, unknown>;
  created_at: string;
}
