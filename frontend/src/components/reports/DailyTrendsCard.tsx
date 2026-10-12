import React from "react";
import { DailyTrendsResponse } from "../../types/reports";
import { Activity, Calendar } from "lucide-react";

interface DailyTrendsCardProps {
  data: DailyTrendsResponse | null;
  isLoading?: boolean;
}

export const DailyTrendsCard: React.FC<DailyTrendsCardProps> = ({
  data,
  isLoading = false,
}) => {
  if (isLoading || !data) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col justify-center items-center min-h-[260px]">
        <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-gray-500">Cargando serie temporal de actividad...</p>
      </div>
    );
  }

  const { trends } = data;
  const maxTurnover = Math.max(...trends.map((t) => t.turnover), 1);

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col gap-6">
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-black text-white">
              Tendencia Histórica Diaria
            </h3>
            <p className="text-xs text-gray-400">
              Evolución de actividad, rondas simuladas y volumen apostado por jornada.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Calendar className="w-4 h-4 text-amber-400" />
          <span>Últimos {trends.length} días activos</span>
        </div>
      </div>

      {trends.length === 0 ? (
        <div className="py-12 text-center text-xs text-gray-500">
          No hay datos históricos registrados en la serie temporal seleccionada.
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Gráfico de Barras Relativo */}
          <div className="flex items-end gap-2 h-44 pt-6 pb-2 px-2 border-b border-gray-800/80 overflow-x-auto">
            {trends.map((point) => {
              const heightPct = Math.max(Math.round((point.turnover / maxTurnover) * 100), 6);
              return (
                <div
                  key={point.date}
                  className="flex-1 min-w-[42px] flex flex-col items-center gap-2 group relative"
                >
                  {/* Tooltip Hover */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-12 z-20 pointer-events-none bg-gray-950 border border-amber-500/40 rounded-lg p-1.5 text-[10px] text-white shadow-xl whitespace-nowrap flex flex-col items-center">
                    <span className="font-bold text-amber-400">{point.date}</span>
                    <span>{point.turnover.toLocaleString()} CR ({point.rounds} rondas)</span>
                  </div>

                  {/* Barra */}
                  <div className="w-full flex items-end justify-center h-32">
                    <div
                      style={{ height: `${heightPct}%` }}
                      className="w-full max-w-[28px] rounded-t-md bg-gradient-to-t from-amber-600 to-yellow-400 group-hover:from-amber-500 group-hover:to-yellow-300 transition-all shadow-sm"
                    />
                  </div>

                  {/* Fecha */}
                  <span className="text-[10px] font-mono text-gray-400 group-hover:text-white truncate max-w-[40px]">
                    {point.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Tabla / Lista compacta de desglose */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-center">
            <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
              <span className="text-[10px] uppercase font-bold text-gray-400">Total Rondas</span>
              <p className="text-lg font-black text-white mt-1">
                {trends.reduce((acc, t) => acc + t.rounds, 0).toLocaleString()}
              </p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
              <span className="text-[10px] uppercase font-bold text-gray-400">Total Turnover</span>
              <p className="text-lg font-black text-amber-400 mt-1">
                {trends.reduce((acc, t) => acc + t.turnover, 0).toLocaleString()} CR
              </p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
              <span className="text-[10px] uppercase font-bold text-gray-400">Total Premios</span>
              <p className="text-lg font-black text-emerald-400 mt-1">
                {trends.reduce((acc, t) => acc + t.payout, 0).toLocaleString()} CR
              </p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
              <span className="text-[10px] uppercase font-bold text-gray-400">Pico Jugadores Activos</span>
              <p className="text-lg font-black text-cyan-400 mt-1">
                {Math.max(...trends.map((t) => t.active_users), 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
