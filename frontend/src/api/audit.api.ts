import { apiClient } from "./client";
import { AuditFilterParams, PaginatedAuditLogs } from "../types/audit";

export const auditApi = {
  async getAuditLogs(params?: AuditFilterParams): Promise<PaginatedAuditLogs> {
    const response = await apiClient.get<PaginatedAuditLogs>("/audit", {
      params: {
        action: params?.action || undefined,
        start_date: params?.start_date || undefined,
        end_date: params?.end_date || undefined,
        page: params?.page ?? 1,
        size: params?.size ?? 20,
      },
    });
    return response.data;
  },
};
