export type LedgerEntryType =
  | "CREDIT"
  | "DEBIT"
  | "BET_SIMULATION"
  | "WIN_SIMULATION"
  | "BONUS"
  | "ADJUSTMENT"
  | "REVERSAL";

export interface Wallet {
  id: string;
  user_id: string;
  balance: number;
  currency: string;
  is_locked: boolean;
}

export interface LedgerEntry {
  id: string;
  wallet_id: string;
  entry_type: LedgerEntryType;
  amount: number;
  balance_before: number;
  balance_after: number;
  idempotency_key?: string | null;
  created_at: string;
  reference_id?: string | null;
  description?: string | null;
}

export interface FaucetPayload {
  amount: number;
}

export interface TransactionPayload {
  amount: number;
  reference_id?: string;
  description?: string;
}

export interface WalletReconciliation {
  wallet_id: string;
  cached_balance: number;
  calculated_ledger_balance: number;
  is_consistent: boolean;
}
