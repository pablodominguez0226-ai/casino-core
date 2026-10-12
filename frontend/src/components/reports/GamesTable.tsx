import React from "react";
import { GamePerformanceItem } from "../../types/reports";
import { Gamepad2, Info, TrendingUp, TrendingDown } from "lucide-react";

interface GamesTableProps {
  items: GamePerformanceItem[];
  isLoading?: boolean;
}

export const GamesTable: React.FC<GamesTableProps> = ({ items, isLoading = false }) => {
  const getRtpBadge = (rtp: number, rounds: number) => {
    if (rounds === 0) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-gray-800 text-gray-400 border border-gray-700">
          0.00% (Sin Rondas)
        </span>
      );
    }

    // Slots teóricos suelen rondar 92% - 97%
    if (rtp >= 92 && rtp <= 97) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-black bg-emerald-950/80 text-emerald-400 border border-emerald-600/50">
          <TrendingUp className="w-3 h-3" />
          {rtp.toFixed(2)}% (En Rango)
        </span>
      );
    }

    if ((rtp >= 85 && rtp < 92) || (rtp > 97 && rtp <= 105)) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-black bg-yellow-950/80 text-yellow-400 border border-yellow-600/50">
          {rtp.toFixed(2)}% (Desvío Moderado)
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-black bg-rose-950/80 text-rose-400 border border-rose-600/50">
        <TrendingDown className="w-3 h-3" />
        {rtp.toFixed(2)}% (Desvío Alto)
      </span>
    );
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
      <div className="p-5 border-b border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Gamepad2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-black text-white">
              Rendimiento por Juego del Catálogo
            </h3>
            <p className="text-xs text-gray-400">
              Desglose de apuestas simuladas, retorno observado y margen de retención (Hold).
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 bg-gray-900/80 px-3 py-1.5 rounded-xl border border-gray-800">
          <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>RTP converge al valor teórico con el incremento de rondas jugadas</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-900/60 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
            <tr>
              <th scope="col" className="px-5 py-3.5 font-bold">Juego</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-center">Rondas Jugadas</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-right">Volumen Apostado</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-right">Premios Pagados</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-right">GGR Simulado</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-center">RTP Observado</th>
              <th scope="col" className="px-5 py-3.5 font-bold text-right">Hold (%)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-gray-500">
                  <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  Cargando estadísticas de juegos...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-gray-500">
                  No se registraron juegos o rondas en el período seleccionado.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.game_id}
                  className="hover:bg-gray-800/30 transition-colors duration-150"
                >
                  <td className="px-5 py-4">
                    <div className="flex flex-col">
                      <span className="font-bold text-white text-sm">
                        {item.game_name}
                      </span>
                      <span className="text-[10px] font-mono text-gray-400 tracking-wider">
                        {item.game_code}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-center font-mono font-semibold text-gray-200">
                    {item.rounds_played.toLocaleString()}
                  </td>
                  <td className="px-5 py-4 text-right font-mono font-bold text-amber-400">
                    {item.total_bet.toLocaleString()}{" "}
                    <span className="text-[10px] text-amber-500/70">CR</span>
                  </td>
                  <td className="px-5 py-4 text-right font-mono font-bold text-emerald-400">
                    {item.total_won.toLocaleString()}{" "}
                    <span className="text-[10px] text-emerald-500/70">CR</span>
                  </td>
                  <td className="px-5 py-4 text-right font-mono font-bold">
                    <span
                      className={
                        item.simulated_ggr >= 0 ? "text-cyan-400" : "text-rose-400"
                      }
                    >
                      {item.simulated_ggr.toLocaleString()}{" "}
                      <span className="text-[10px] opacity-70">CR</span>
                    </span>
                  </td>
                  <td className="px-5 py-4 text-center">
                    {getRtpBadge(item.observed_rtp, item.rounds_played)}
                  </td>
                  <td className="px-5 py-4 text-right font-mono font-bold text-gray-300">
                    {item.hold_percentage.toFixed(2)}%
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
