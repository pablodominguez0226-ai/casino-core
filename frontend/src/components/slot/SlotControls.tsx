import React from "react";
import { Minus, Plus, Play, Sparkles } from "lucide-react";

interface SlotControlsProps {
  betAmount: number;
  minBet: number;
  maxBet: number;
  balance: number;
  isSpinning: boolean;
  onBetChange: (amount: number) => void;
  onSpin: () => void;
}

export const SlotControls: React.FC<SlotControlsProps> = ({
  betAmount,
  minBet,
  maxBet,
  balance,
  isSpinning,
  onBetChange,
  onSpin,
}) => {
  const step = 10;
  const hasInsufficientFunds = balance < betAmount;

  const handleDecrease = () => {
    if (betAmount - step >= minBet) {
      onBetChange(betAmount - step);
    } else {
      onBetChange(minBet);
    }
  };

  const handleIncrease = () => {
    if (betAmount + step <= maxBet) {
      onBetChange(betAmount + step);
    } else {
      onBetChange(maxBet);
    }
  };

  const quickBets = [minBet, 25, 50, 100, 250].filter(
    (val, idx, self) => val <= maxBet && self.indexOf(val) === idx
  );

  return (
    <div className="w-full bg-gray-900/90 border border-gray-800 rounded-2xl p-4 md:p-6 shadow-xl backdrop-blur-md">
      <div className="flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Selector de apuesta */}
        <div className="flex flex-col items-center md:items-start w-full md:w-auto">
          <span className="text-xs font-semibold tracking-wider text-gray-400 uppercase mb-2">
            Apuesta por Giro
          </span>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDecrease}
              disabled={isSpinning || betAmount <= minBet}
              className="p-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition border border-gray-700"
              aria-label="Disminuir apuesta"
            >
              <Minus className="w-4 h-4" />
            </button>

            <div className="flex flex-col items-center justify-center min-w-[140px] px-4 py-2 bg-black/60 rounded-xl border border-amber-500/40 shadow-inner">
              <span className="text-xl md:text-2xl font-black text-amber-400 tracking-tight">
                {betAmount.toLocaleString()}
              </span>
              <span className="text-[10px] font-bold text-amber-500/80 tracking-widest uppercase">
                VIRTUAL CREDITS
              </span>
            </div>

            <button
              type="button"
              onClick={handleIncrease}
              disabled={isSpinning || betAmount >= maxBet}
              className="p-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition border border-gray-700"
              aria-label="Aumentar apuesta"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Botones de apuesta rápida */}
          <div className="flex items-center gap-1.5 mt-3">
            {quickBets.map((val) => (
              <button
                key={val}
                type="button"
                onClick={() => onBetChange(val)}
                disabled={isSpinning}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition border ${
                  betAmount === val
                    ? "bg-amber-500 text-black border-amber-400 font-bold"
                    : "bg-gray-800/80 text-gray-400 border-gray-700 hover:bg-gray-700 hover:text-white"
                } disabled:opacity-40`}
              >
                {val}
              </button>
            ))}
            <button
              type="button"
              onClick={() => onBetChange(maxBet)}
              disabled={isSpinning}
              className="px-2.5 py-1 text-xs font-bold rounded-lg transition bg-amber-950/80 text-amber-400 border border-amber-600/50 hover:bg-amber-900"
            >
              MAX ({maxBet})
            </button>
          </div>
        </div>

        {/* Botón Principal SPIN */}
        <div className="w-full md:w-auto flex flex-col items-center">
          <button
            type="button"
            onClick={onSpin}
            disabled={isSpinning || hasInsufficientFunds}
            className={`relative group w-full md:w-64 h-16 rounded-2xl flex items-center justify-center gap-3 text-lg md:text-xl font-black tracking-wider uppercase transition-all duration-200 ${
              isSpinning
                ? "bg-amber-600/60 text-amber-200 cursor-wait animate-pulse"
                : hasInsufficientFunds
                ? "bg-gray-800 text-gray-500 border border-gray-700 cursor-not-allowed"
                : "bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500 text-black shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 hover:scale-[1.02] active:scale-[0.98] border-2 border-yellow-200"
            }`}
          >
            {isSpinning ? (
              <>
                <Sparkles className="w-6 h-6 animate-spin text-amber-200" />
                <span>GIRANDO...</span>
              </>
            ) : (
              <>
                <Play className="w-6 h-6 fill-black" />
                <span>GIRAR / SPIN</span>
              </>
            )}
          </button>

          {hasInsufficientFunds && (
            <p className="mt-2 text-xs text-rose-400 font-medium">
              Saldo insuficiente ({balance} CREDITS disponibles)
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
