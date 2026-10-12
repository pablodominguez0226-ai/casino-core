import React from "react";
import { LedgerEntry, LedgerEntryType } from "../../types/wallet";
import { ArrowDownRight, ArrowUpRight, History, RefreshCw } from "lucide-react";

interface LedgerTableProps {
  entries: LedgerEntry[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const LedgerTable: React.FC<LedgerTableProps> = ({
  entries,
  isLoading = false,
  onRefresh,
}) => {
  const getBadgeStyle = (type: LedgerEntryType) => {
    switch (type) {
      case "CREDIT":
      case "WIN_SIMULATION":
        return {
          bg: "bg-emerald-950/70 border-emerald-700/60 text-emerald-400",
          icon: <ArrowUpRight className="w-3.5 h-3.5" />,
          isPositive: true,
        };
      case "DEBIT":
      case "BET_SIMULATION":
        return {
          bg: "bg-rose-950/70 border-rose-700/60 text-rose-400",
          icon: <ArrowDownRight className="w-3.5 h-3.5" />,
          isPositive: false,
        };
      default:
        return {
          bg: "bg-purple-950/70 border-purple-700/60 text-purple-400",
          icon: <History className="w-3.5 h-3.5" />,
          isPositive: true,
        };
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="w-full bg-gray-900/80 border border-gray-800 rounded-2xl p-4 md:p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-amber-400" />
          <h3 className="text-base font-bold text-white">
            Historial de Transacciones (Ledger Inmutable)
          </h3>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition"
            title="Actualizar Ledger"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
          </button>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="py-8 text-center text-gray-500 text-sm">
          No hay movimientos registrados en el ledger.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider text-[10px]">
                <th className="pb-3 px-3">Hora</th>
                <th className="pb-3 px-3">Operación</th>
                <th className="pb-3 px-3 text-right">Monto</th>
                <th className="pb-3 px-3 text-right">Saldo Ant.</th>
                <th className="pb-3 px-3 text-right">Saldo Post.</th>
                <th className="pb-3 px-3">Concepto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono">
              {entries.map((entry) => {
                const badge = getBadgeStyle(entry.entry_type);
                return (
                  <tr key={entry.id} className="hover:bg-gray-800/40 transition">
                    <td className="py-3 px-3 text-gray-400 whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </td>

                    <td className="py-3 px-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${badge.bg}`}
                      >
                        {badge.icon}
                        {entry.entry_type}
                      </span>
                    </td>

                    <td
                      className={`py-3 px-3 text-right font-bold whitespace-nowrap ${
                        badge.isPositive ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {badge.isPositive ? "+" : "-"}
                      {entry.amount.toLocaleString()} CREDITS
                    </td>

                    <td className="py-3 px-3 text-right text-gray-400 whitespace-nowrap">
                      {entry.balance_before.toLocaleString()}
                    </td>

                    <td className="py-3 px-3 text-right text-amber-400 font-bold whitespace-nowrap">
                      {entry.balance_after.toLocaleString()}
                    </td>

                    <td className="py-3 px-3 text-gray-400 truncate max-w-[200px]" title={entry.description || ""}>
                      {entry.description || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
