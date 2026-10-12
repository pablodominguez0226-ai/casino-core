import { apiClient } from "./client";
import {
  FaucetPayload,
  LedgerEntry,
  TransactionPayload,
  Wallet,
  WalletReconciliation,
} from "../types/wallet";

export const walletApi = {
  async getWallet(): Promise<Wallet> {
    const response = await apiClient.get<Wallet>("/wallet");
    return response.data;
  },

  async requestFaucet(payload: FaucetPayload): Promise<LedgerEntry> {
    const idempotencyKey = crypto.randomUUID();
    const response = await apiClient.post<LedgerEntry>("/wallet/faucet", payload, {
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    });
    return response.data;
  },

  async debit(payload: TransactionPayload): Promise<LedgerEntry> {
    const idempotencyKey = crypto.randomUUID();
    const response = await apiClient.post<LedgerEntry>("/wallet/debit", payload, {
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    });
    return response.data;
  },

  async credit(payload: TransactionPayload): Promise<LedgerEntry> {
    const idempotencyKey = crypto.randomUUID();
    const response = await apiClient.post<LedgerEntry>("/wallet/credit", payload, {
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    });
    return response.data;
  },

  async getLedger(skip = 0, limit = 50): Promise<LedgerEntry[]> {
    const response = await apiClient.get<LedgerEntry[]>("/wallet/ledger", {
      params: { skip, limit },
    });
    return response.data;
  },

  async reconcile(): Promise<WalletReconciliation> {
    const response = await apiClient.get<WalletReconciliation>("/wallet/reconcile");
    return response.data;
  },
};
