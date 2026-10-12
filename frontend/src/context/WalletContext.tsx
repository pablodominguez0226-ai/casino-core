import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { walletApi } from "../api/wallet.api";
import { LedgerEntry, WalletReconciliation } from "../types/wallet";
import { useAuth } from "./AuthContext";
import { soundManager } from "../utils/audio";

interface WalletContextType {
  balance: number;
  currency: string;
  isLocked: boolean;
  isLoading: boolean;
  recentLedger: LedgerEntry[];
  refreshBalance: () => Promise<void>;
  requestFaucet: (amount: number) => Promise<LedgerEntry>;
  updateBalanceLocally: (newBalance: number) => void;
  fetchLedger: (limit?: number) => Promise<void>;
  reconcileWallet: () => Promise<WalletReconciliation>;
}

const WalletContext = createContext<WalletContextType | undefined>(undefined);

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [balance, setBalance] = useState<number>(0);
  const [currency, setCurrency] = useState<string>("CREDITS");
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [recentLedger, setRecentLedger] = useState<LedgerEntry[]>([]);

  const fetchLedger = useCallback(async (limit = 20): Promise<void> => {
    if (!isAuthenticated) return;
    try {
      const entries = await walletApi.getLedger(0, limit);
      setRecentLedger(entries);
    } catch {
      // Error fetching ledger
    }
  }, [isAuthenticated]);

  const refreshBalance = useCallback(async (): Promise<void> => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const wallet = await walletApi.getWallet();
      setBalance(wallet.balance);
      setCurrency(wallet.currency || "CREDITS");
      setIsLocked(wallet.is_locked);
      await fetchLedger(20);
    } catch {
      // Error fetching wallet
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, fetchLedger]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshBalance();
    } else {
      setBalance(0);
      setRecentLedger([]);
    }
  }, [isAuthenticated, refreshBalance]);

  const requestFaucet = async (amount: number): Promise<LedgerEntry> => {
    setIsLoading(true);
    try {
      const entry = await walletApi.requestFaucet({ amount });
      setBalance(entry.balance_after);
      soundManager.playCoin();
      await fetchLedger(20);
      return entry;
    } finally {
      setIsLoading(false);
    }
  };

  const updateBalanceLocally = (newBalance: number): void => {
    setBalance(newBalance);
    // Refresh ledger in background
    fetchLedger(20);
  };

  const reconcileWallet = async (): Promise<WalletReconciliation> => {
    return await walletApi.reconcile();
  };

  return (
    <WalletContext.Provider
      value={{
        balance,
        currency,
        isLocked,
        isLoading,
        recentLedger,
        refreshBalance,
        requestFaucet,
        updateBalanceLocally,
        fetchLedger,
        reconcileWallet,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};

export const useWallet = (): WalletContextType => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWallet must be used within a WalletProvider");
  }
  return context;
};
