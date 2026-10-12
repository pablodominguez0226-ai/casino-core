export interface AuditLog {
  id: string;
  user_id?: string | null;
  operator_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  details?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
}

export interface PaginatedAuditLogs {
  items: AuditLog[];
  total: number;
  page: number;
  size: number;
}

export interface AuditFilterParams {
  action?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  size?: number;
}
