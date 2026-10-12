import React, { useState } from "react";
import { Reel } from "./Reel";
import { SlotControls } from "./SlotControls";
import { useSlotEngine } from "../../hooks/useSlotEngine";
import { useWallet } from "../../context/WalletContext";
import {
  Trophy,
  Volume2,
  VolumeX,
  Info,
  RotateCcw,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { soundManager } from "../../utils/audio";

export const SlotMachine: React.FC = () => {
  const { balance } = useWallet();
  const {
    game,
    reels,
    isSpinning,
    spinningReels,
    betAmount,
    setBetAmount,
    lastPayout,
    lastWin,
    errorMessage,
    isLoadingCatalog,
    spin,
    initGame,
  } = useSlotEngine();

  const [isMuted, setIsMuted] = useState<boolean>(soundManager.isMuted);
  const [showPaytable, setShowPaytable] = useState<boolean>(false);

  const handleToggleSound = () => {
    const muted = soundManager.toggleMute();
    setIsMuted(muted);
  };

  const paytable = [
    { symbol: "7️⃣", name: "SEVEN", mult: "100x", desc: "Jackpot Máximo" },
    { symbol: "🔔", name: "BELL", mult: "25x", desc: "Premio Alto" },
    { symbol: "🍊", name: "ORANGE", mult: "10x", desc: "Premio Medio" },
    { symbol: "🍋", name: "LEMON", mult: "5x", desc: "Premio Regular" },
    { symbol: "🍒", name: "CHERRY", mult: "2x", desc: "Premio Base" },
  ];

  if (isLoadingCatalog) {
    return (
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center justify-center p-12 bg-gray-900/60 rounded-3xl border border-gray-800">
        <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-gray-400 font-medium">Iniciando motor de juego y sesión...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center">
      {/* Mensaje de Error */}
      {errorMessage && (
        <div className="w-full mb-4 flex items-center justify-between p-4 bg-rose-950/80 border border-rose-700/60 rounded-xl text-rose-200 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={initGame}
            className="flex items-center gap-1.5 px-3 py-1 bg-rose-900/80 hover:bg-rose-800 rounded-lg text-xs font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reintentar
          </button>
        </div>
      )}

      {/* Cabina Tragamonedas (Cabinet Visual) */}
      <div className="w-full casino-cabinet rounded-3xl p-6 md:p-8 relative overflow-hidden">
        {/* Luces superiores decorativas */}
        <div className="flex items-center justify-between mb-4 border-b border-amber-500/30 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10B981]" />
            <span className="text-xs font-bold tracking-wider text-amber-300 uppercase">
              {game?.name || "Classic Fruit Slot"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPaytable(!showPaytable)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition"
              title="Tabla de Pagos"
            >
              <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Pagos</span>
            </button>

            <button
              onClick={handleToggleSound}
              className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition"
              title={isMuted ? "Activar Sonido" : "Silenciar"}
            >
              {isMuted ? (
                <VolumeX className="w-4 h-4 text-gray-400" />
              ) : (
                <Volume2 className="w-4 h-4 text-amber-400" />
              )}
            </button>
          </div>
        </div>

        {/* Modal / Panel de Tabla de Pagos */}
        {showPaytable && (
          <div className="mb-6 p-4 rounded-2xl bg-black/80 border border-amber-500/40 backdrop-blur-md animate-fadeIn">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-bold text-amber-400 flex items-center gap-2">
                <Info className="w-4 h-4" /> Tabla de Premios (3 Símbolos Iguales)
              </h4>
              <button
                onClick={() => setShowPaytable(false)}
                className="text-xs text-gray-400 hover:text-white"
              >
                Cerrar
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
              {paytable.map((item) => (
                <div
                  key={item.name}
                  className="p-2 rounded-xl bg-gray-900/90 border border-gray-800 flex flex-col items-center"
                >
                  <span className="text-2xl">{item.symbol}</span>
                  <span className="text-xs font-black text-amber-300 mt-1">{item.mult}</span>
                  <span className="text-[10px] text-gray-400">{item.desc}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pantalla Superior de Resultados / Banner de Premio */}
        <div className="mb-6 w-full py-3 px-4 rounded-2xl bg-black/70 border border-amber-500/40 flex items-center justify-between shadow-inner">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              Último Premio
            </span>
            <div className="flex items-center gap-2">
              <Trophy
                className={`w-5 h-5 ${
                  lastWin ? "text-amber-400 animate-bounce" : "text-gray-600"
                }`}
              />
              <span
                className={`text-xl md:text-2xl font-black ${
                  lastWin ? "text-amber-400 drop-shadow-[0_0_10px_#EAB308]" : "text-gray-500"
                }`}
              >
                {lastPayout > 0 ? `+${lastPayout.toLocaleString()} CREDITS` : "0 CREDITS"}
              </span>
            </div>
          </div>

          {lastWin && (
            <div className="px-4 py-1.5 rounded-full bg-gradient-to-r from-amber-500 to-yellow-400 text-black font-black text-xs md:text-sm animate-pulse shadow-[0_0_15px_#EAB308]">
              ¡PREMIO GANADO!
            </div>
          )}
        </div>

        {/* Los 3 Rodillos */}
        <div className="relative py-4 px-2 md:px-6 bg-black/90 rounded-2xl border-2 border-amber-600/60 shadow-2xl flex items-center justify-center gap-3 md:gap-6">
          {/* Guía visual de línea de pago lateral */}
          <div className="absolute left-1 top-1/2 -translate-y-1/2 w-2 h-8 bg-amber-500 rounded-r-full shadow-[0_0_10px_#EAB308]" />
          <div className="absolute right-1 top-1/2 -translate-y-1/2 w-2 h-8 bg-amber-500 rounded-l-full shadow-[0_0_10px_#EAB308]" />

          <Reel
            isSpinning={spinningReels[0]}
            finalSymbol={reels[0]}
            reelIndex={0}
          />
          <Reel
            isSpinning={spinningReels[1]}
            finalSymbol={reels[1]}
            reelIndex={1}
          />
          <Reel
            isSpinning={spinningReels[2]}
            finalSymbol={reels[2]}
            reelIndex={2}
          />
        </div>

        {/* Panel de Controles Inferior */}
        <div className="mt-6">
          <SlotControls
            betAmount={betAmount}
            minBet={game?.min_bet || 10}
            maxBet={game?.max_bet || 1000}
            balance={balance}
            isSpinning={isSpinning}
            onBetChange={setBetAmount}
            onSpin={spin}
          />
        </div>
      </div>
    </div>
  );
};
