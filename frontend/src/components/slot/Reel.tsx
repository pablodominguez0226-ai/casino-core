import React, { useEffect, useState } from "react";

export interface ReelProps {
  isSpinning: boolean;
  finalSymbol: string;
  delay?: number;
  reelIndex?: number;
}

const SYMBOLS_DATA: Record<string, { icon: string; name: string; color: string; bg: string }> = {
  SEVEN: { icon: "7️⃣", name: "SEVEN", color: "text-amber-400", bg: "from-amber-900/40 to-yellow-600/20" },
  BELL: { icon: "🔔", name: "BELL", color: "text-yellow-400", bg: "from-yellow-900/40 to-amber-600/20" },
  ORANGE: { icon: "🍊", name: "ORANGE", color: "text-orange-400", bg: "from-orange-900/40 to-amber-600/20" },
  LEMON: { icon: "🍋", name: "LEMON", color: "text-lime-300", bg: "from-lime-900/40 to-green-600/20" },
  CHERRY: { icon: "🍒", name: "CHERRY", color: "text-red-400", bg: "from-red-900/40 to-rose-600/20" },
};

const ALL_SYMBOLS = ["SEVEN", "BELL", "ORANGE", "LEMON", "CHERRY"];

export const Reel: React.FC<ReelProps> = ({ isSpinning, finalSymbol, reelIndex = 0 }) => {
  const [displayedSymbol, setDisplayedSymbol] = useState<string>(finalSymbol || "SEVEN");
  const [bounce, setBounce] = useState<boolean>(false);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isSpinning) {
      setBounce(false);
      interval = setInterval(() => {
        const randomIndex = Math.floor(Math.random() * ALL_SYMBOLS.length);
        setDisplayedSymbol(ALL_SYMBOLS[randomIndex]);
      }, 75);
    } else {
      setDisplayedSymbol(finalSymbol);
      setBounce(true);
      const timer = setTimeout(() => setBounce(false), 350);
      return () => clearTimeout(timer);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSpinning, finalSymbol]);

  const symbolConfig = SYMBOLS_DATA[displayedSymbol] || SYMBOLS_DATA.CHERRY;

  return (
    <div className="relative flex flex-col items-center justify-center w-28 md:w-36 h-40 md:h-48 rounded-xl bg-gradient-to-b from-gray-900 via-gray-950 to-gray-900 border-2 border-amber-500/40 shadow-inner overflow-hidden select-none">
      {/* Luz ambiental del rodillo */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-transparent to-black/80 pointer-events-none z-10" />

      {/* Indicador de línea de pago central */}
      <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-20 md:h-24 bg-amber-500/5 border-y border-amber-500/30 pointer-events-none z-10" />

      {/* Símbolo central */}
      <div
        className={`flex flex-col items-center justify-center transition-all duration-150 ${
          isSpinning ? "blur-[2px] scale-95 opacity-80" : "blur-0 scale-100 opacity-100"
        } ${bounce ? "animate-bounceShort" : ""}`}
      >
        <span className="text-5xl md:text-6xl drop-shadow-[0_0_12px_rgba(234,179,8,0.5)]">
          {symbolConfig.icon}
        </span>
        <span
          className={`mt-2 text-[10px] md:text-xs font-black tracking-widest uppercase ${symbolConfig.color}`}
        >
          {symbolConfig.name}
        </span>
      </div>

      {/* Reflejo metálico superior */}
      <div className="absolute top-0 inset-x-0 h-4 bg-gradient-to-b from-white/10 to-transparent pointer-events-none z-20" />
      {/* Sombra inferior */}
      <div className="absolute bottom-0 inset-x-0 h-4 bg-gradient-to-t from-black/60 to-transparent pointer-events-none z-20" />

      {/* Badge del índice del rodillo */}
      <div className="absolute top-1.5 right-2 text-[9px] text-gray-500 font-mono z-20">
        R{reelIndex + 1}
      </div>
    </div>
  );
};
