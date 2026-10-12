/**
 * Tipos de datos para el motor de reportes y analíticas operativas (Sprint 7).
 * Todas las métricas financieras corresponden a créditos virtuales simulados (CREDITS / VIRTUAL).
 */

export interface DateRangeParams {
  from_date?: string;
  to_date?: string;
  operator_id?: string;
}

export interface OverviewMetrics {
  total_players: number;
  daily_active_users: number;
  total_sessions: number;
  total_game_rounds: number;
  total_turnover_credits: number;
  total_payout_credits: number;
  simulated_ggr_credits: number;
  overall_observed_rtp: number;
  circulating_virtual_credits: number;
}

export interface GamePerformanceItem {
  game_id: string;
  game_code: string;
  game_name: string;
  rounds_played: number;
  total_bet: number;
  total_won: number;
  simulated_ggr: number;
  observed_rtp: number;
  hold_percentage: number;
}

export interface GamePerformanceReportResponse {
  items: GamePerformanceItem[];
}

export interface WalletFlowItem {
  entry_type: string;
  count: number;
  total_volume: number;
}

export interface WalletFlowReportResponse {
  flows: WalletFlowItem[];
  total_minted: number;
  total_burned_or_lost: number;
}

export interface DailyTrendPoint {
  date: string;
  active_users: number;
  rounds: number;
  turnover: number;
  payout: number;
}

export interface DailyTrendsResponse {
  trends: DailyTrendPoint[];
}
