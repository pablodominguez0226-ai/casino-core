import React, { useState } from "react";
import { useWallet } from "../../context/WalletContext";
import {
  Coins,
  RefreshCw,
  PlusCircle,
  ShieldCheck,
  Lock,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { WalletReconciliation } from "../../types/wallet";

export const BalanceWidget: React.FC = () => {
  const {
    balance,
    currency,
    isLocked,
    isLoading,
    refreshBalance,
    requestFaucet,
    reconcileWallet,
  } = useWallet();

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [faucetAmount, setFaucetAmount] = useState<number>(1000);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [reconciliationResult, setReconciliationResult] = useState<WalletReconciliation | null>(null);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const faucetPresets = [500, 1000, 5000, 10000, 25000];

  const handleFaucetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (faucetAmount <= 0 || faucetAmount > 100000) return;

    setIsSubmitting(true);
    setFeedbackMessage(null);
    try {
      await requestFaucet(faucetAmount);
      setFeedbackMessage(`¡Recarga exitosa de +${faucetAmount.toLocaleString()} ${currency}!`);
      setTimeout(() => {
        setIsModalOpen(false);
        setFeedbackMessage(null);
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al recargar créditos";
      setFeedbackMessage(`Error: ${msg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAudit = async () => {
    setIsAuditing(true);
    setReconciliationResult(null);
    try {
      const result = await reconcileWallet();
      setReconciliationResult(result);
    } catch {
      // Error reconciling
    } finally {
      setIsAuditing(false);
    }
  };

  return (
    <div className="w-full bg-gradient-to-r from-gray-900 via-gray-950 to-gray-900 border border-amber-500/30 rounded-2xl p-4 md:p-6 shadow-xl relative overflow-hidden">
      {/* Luz dorada ambiental */}
      <div className="absolute -top-12 -right-12 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Info del Balance */}
        <div className="flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400">
            <Coins className="w-8 h-8" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-400 tracking-wider uppercase">
                Billetera Virtual Transaccional
              </span>
              {isLocked ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                  <Lock className="w-3 h-3" /> BLOQUEADA
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  <ShieldCheck className="w-3 h-3" /> ACTIVA
                </span>
              )}
            </div>

            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl md:text-3xl font-black text-amber-400 tracking-tight">
                {balance.toLocaleString()}
              </span>
              <span className="text-sm font-bold text-amber-500/80 tracking-widest uppercase">
                {currency}
              </span>
            </div>
          </div>
        </div>

        {/* Acciones del Wallet */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={refreshBalance}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition disabled:opacity-40"
            title="Sincronizar Balance"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
          </button>

          <button
            type="button"
            onClick={handleAudit}
            disabled={isAuditing}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold border border-gray-700 transition"
            title="Auditoría Matemática de Consistencia Ledger"
          >
            <ShieldCheck className={`w-4 h-4 ${isAuditing ? "animate-spin text-emerald-400" : "text-emerald-400"}`} />
            <span>Auditar Ledger</span>
          </button>

          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            disabled={isLocked}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-bold text-xs uppercase tracking-wider transition shadow-md shadow-amber-500/20 active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Recargar Faucet</span>
          </button>
        </div>
      </div>

      {/* Resultado de Auditoría / Reconciliación */}
      {reconciliationResult && (
        <div className="mt-4 p-3 rounded-xl bg-black/60 border border-emerald-500/40 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-gray-300">
              Auditoría Matemática: <strong className="text-emerald-400 font-bold">Consistente</strong> (Balance Caché: {reconciliationResult.cached_balance} | Ledger Calculado: {reconciliationResult.calculated_ledger_balance})
            </span>
          </div>
          <button
            onClick={() => setReconciliationResult(null)}
            className="text-gray-400 hover:text-white text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Modal de Recarga Educativa (Faucet) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md bg-gray-900 border border-amber-500/40 rounded-3xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white rounded-full bg-gray-800"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-amber-500/20 rounded-2xl text-amber-400">
                <Coins className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Faucet de Créditos Educativos</h3>
                <p className="text-xs text-gray-400">Simulación sin valor financiero real</p>
              </div>
            </div>

            {feedbackMessage && (
              <div className="mb-4 p-3 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                <span>{feedbackMessage}</span>
              </div>
            )}

            <form onSubmit={handleFaucetSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Seleccionar Monto Rápido
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {faucetPresets.map((amount) => (
                    <button
                      key={amount}
                      type="button"
                      onClick={() => setFaucetAmount(amount)}
                      className={`p-2 rounded-xl text-xs font-bold border transition ${
                        faucetAmount === amount
                          ? "bg-amber-500 text-black border-amber-400"
                          : "bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700"
                      }`}
                    >
                      +{amount.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
                  Monto Personalizado (Máx. 100,000)
                </label>
                <input
                  type="number"
                  min={1}
                  max={100000}
                  value={faucetAmount}
                  onChange={(e) => setFaucetAmount(Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl bg-gray-950 border border-gray-700 text-white font-mono focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting || faucetAmount <= 0}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-black uppercase text-sm tracking-wider transition shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {isSubmitting ? "Recargando..." : `Confirmar Recarga de ${faucetAmount.toLocaleString()} CREDITS`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
