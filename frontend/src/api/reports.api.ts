import { apiClient } from "./client";
import {
  DailyTrendsResponse,
  DateRangeParams,
  GamePerformanceReportResponse,
  OverviewMetrics,
  WalletFlowReportResponse,
} from "../types/reports";

export const getOverview = async (params?: DateRangeParams): Promise<OverviewMetrics> => {
  const response = await apiClient.get<OverviewMetrics>("/reports/overview", {
    params: {
      from_date: params?.from_date || undefined,
      to_date: params?.to_date || undefined,
      operator_id: params?.operator_id || undefined,
    },
  });
  return response.data;
};

export const getGamePerformance = async (
  params?: DateRangeParams
): Promise<GamePerformanceReportResponse> => {
  const response = await apiClient.get<GamePerformanceReportResponse>("/reports/games", {
    params: {
      from_date: params?.from_date || undefined,
      to_date: params?.to_date || undefined,
      operator_id: params?.operator_id || undefined,
    },
  });
  return response.data;
};

export const getWalletFlow = async (
  params?: DateRangeParams
): Promise<WalletFlowReportResponse> => {
  const response = await apiClient.get<WalletFlowReportResponse>("/reports/wallet-flow", {
    params: {
      from_date: params?.from_date || undefined,
      to_date: params?.to_date || undefined,
      operator_id: params?.operator_id || undefined,
    },
  });
  return response.data;
};

export const getDailyTrends = async (
  days: number = 14,
  operatorId?: string
): Promise<DailyTrendsResponse> => {
  const response = await apiClient.get<DailyTrendsResponse>("/reports/trends", {
    params: {
      days,
      operator_id: operatorId || undefined,
    },
  });
  return response.data;
};

export const reportsApi = {
  getOverview,
  getGamePerformance,
  getWalletFlow,
  getDailyTrends,
};
