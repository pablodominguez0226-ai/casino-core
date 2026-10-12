import React from "react";
import { WalletFlowReportResponse } from "../../types/reports";
import { ArrowDownRight, ArrowUpRight, Coins, Scale } from "lucide-react";

interface WalletFlowCardProps {
  data: WalletFlowReportResponse | null;
  isLoading?: boolean;
}

export const WalletFlowCard: React.FC<WalletFlowCardProps> = ({
  data,
  isLoading = false,
}) => {
  if (isLoading || !data) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col justify-center items-center min-h-[260px]">
        <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-gray-500">Cargando flujos de wallets...</p>
      </div>
    );
  }

  const { flows, total_minted, total_burned_or_lost } = data;
  const netDelta = total_minted - total_burned_or_lost;
  const totalVolumeAll = flows.reduce((acc, f) => acc + f.total_volume, 0) || 1;

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "CREDIT":
        return { label: "Depósitos / Faucets", color: "bg-emerald-500", text: "text-emerald-400" };
      case "BONUS":
        return { label: "Bonificaciones / Promociones", color: "bg-purple-500", text: "text-purple-400" };
      case "BET_SIMULATION":
        return { label: "Apuestas Simuladas", color: "bg-amber-500", text: "text-amber-400" };
      case "WIN_SIMULATION":
        return { label: "Premios Pagados", color: "bg-cyan-500", text: "text-cyan-400" };
      case "DEBIT":
        return { label: "Retiros / Débitos", color: "bg-rose-500", text: "text-rose-400" };
      case "ADJUSTMENT":
        return { label: "Ajustes Manuales", color: "bg-blue-500", text: "text-blue-400" };
      case "REVERSAL":
        return { label: "Reversiones", color: "bg-gray-500", text: "text-gray-400" };
      default:
        return { label: type, color: "bg-gray-600", text: "text-gray-300" };
    }
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col gap-6">
      {/* Encabezado */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Coins className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-black text-white">
              Flujo Virtual del Ledger
            </h3>
            <p className="text-xs text-gray-400">
              Emisión de créditos simulados vs. absorción por juego o débitos.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-gray-900 border border-gray-800 text-xs font-mono font-bold text-gray-300">
          <Scale className="w-3.5 h-3.5 text-amber-400" />
          <span>
            Neto:{" "}
            <span className={netDelta >= 0 ? "text-emerald-400" : "text-rose-400"}>
              {netDelta > 0 ? `+${netDelta.toLocaleString()}` : netDelta.toLocaleString()} CR
            </span>
          </span>
        </div>
      </div>

      {/* Resumen de Emisión vs Absorción */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Total Emitido */}
        <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-900/50 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              Total Emitido (Minted)
            </span>
            <span className="text-2xl font-black text-emerald-300 mt-1">
              {total_minted.toLocaleString()}{" "}
              <span className="text-xs font-bold text-emerald-500">CR</span>
            </span>
            <span className="text-[10px] text-gray-400 mt-0.5">
              Faucets y Bonificaciones
            </span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400">
            <ArrowUpRight className="w-6 h-6" />
          </div>
        </div>

        {/* Total Absorbido / Quemado */}
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-900/50 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-[11px] font-bold uppercase tracking-wider text-rose-400">
              Total Absorbido / Quemado
            </span>
            <span className="text-2xl font-black text-rose-300 mt-1">
              {total_burned_or_lost.toLocaleString()}{" "}
              <span className="text-xs font-bold text-rose-500">CR</span>
            </span>
            <span className="text-[10px] text-gray-400 mt-0.5">
              Débitos y Pérdidas netas en juego
            </span>
          </div>
          <div className="p-3 rounded-xl bg-rose-500/20 text-rose-400">
            <ArrowDownRight className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Desglose Gráfico por Entry Type */}
      <div className="flex flex-col gap-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400">
          Distribución por Categoría de Movimiento
        </h4>

        {flows.length === 0 ? (
          <p className="text-xs text-gray-500 py-4 text-center">
            No hay movimientos en el ledger para el período seleccionado.
          </p>
        ) : (
          <div className="space-y-3">
            {flows.map((flow) => {
              const meta = getTypeLabel(flow.entry_type);
              const percentage = Math.round((flow.total_volume / totalVolumeAll) * 100);

              return (
                <div key={flow.entry_type} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${meta.color}`} />
                      <span className="font-semibold text-gray-200">{meta.label}</span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        ({flow.count.toLocaleString()} ops)
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className={`font-mono font-bold ${meta.text}`}>
                        {flow.total_volume.toLocaleString()} CR
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono w-9 text-right">
                        {percentage}%
                      </span>
                    </div>
                  </div>

                  {/* Barra de Progreso */}
                  <div className="w-full h-2 bg-gray-900 rounded-full overflow-hidden border border-gray-800">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${meta.color}`}
                      style={{ width: `${Math.max(percentage, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
