import { apiClient } from "./client";
import {
  Game,
  GameRound,
  GameSession,
  SpinRequest,
  SpinResponse,
} from "../types/gaming";

export const gamesApi = {
  async listGames(): Promise<Game[]> {
    const response = await apiClient.get<Game[]>("/games");
    return response.data;
  },

  async createSession(gameId: string): Promise<GameSession> {
    const response = await apiClient.post<GameSession>("/games/sessions", {
      game_id: gameId,
    });
    return response.data;
  },

  async executeSpin(sessionId: string, payload: SpinRequest): Promise<SpinResponse> {
    const idempotencyKey = crypto.randomUUID();
    const response = await apiClient.post<SpinResponse>(
      `/games/sessions/${sessionId}/spin`,
      payload,
      {
        headers: {
          "Idempotency-Key": idempotencyKey,
        },
      }
    );
    return response.data;
  },

  async endSession(sessionId: string): Promise<GameSession> {
    const response = await apiClient.post<GameSession>(`/games/sessions/${sessionId}/end`);
    return response.data;
  },

  async getSessionRounds(sessionId: string, skip = 0, limit = 50): Promise<GameRound[]> {
    const response = await apiClient.get<GameRound[]>(`/games/sessions/${sessionId}/rounds`, {
      params: { skip, limit },
    });
    return response.data;
  },
};
