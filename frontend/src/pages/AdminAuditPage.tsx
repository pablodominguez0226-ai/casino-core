import React, { useCallback, useEffect, useState } from "react";
import { Navbar } from "../components/layout/Navbar";
import { auditApi } from "../api/audit.api";
import { AuditLog, PaginatedAuditLogs } from "../types/audit";
import {
  FileSearch,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  AlertCircle,
  Clock,
  Terminal,
} from "lucide-react";

export const AdminAuditPage: React.FC = () => {
  const [auditData, setAuditData] = useState<PaginatedAuditLogs>({
    items: [],
    total: 0,
    page: 1,
    size: 15,
  });
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modal para ver los detalles JSON del log
  const [activeLogDetail, setActiveLogDetail] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(
    async (pageToLoad: number) => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await auditApi.getAuditLogs({
          action: selectedAction || undefined,
          start_date: startDate ? new Date(startDate).toISOString() : undefined,
          end_date: endDate ? new Date(endDate).toISOString() : undefined,
          page: pageToLoad,
          size: 15,
        });
        setAuditData(response);
        setCurrentPage(pageToLoad);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error al consultar los registros de auditoría";
        setErrorMessage(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [selectedAction, startDate, endDate]
  );

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs(1);
  };

  const handleClearFilters = () => {
    setSelectedAction("");
    setStartDate("");
    setEndDate("");
  };

  const totalPages = Math.ceil(auditData.total / auditData.size) || 1;

  const getActionBadgeColor = (action: string) => {
    const act = action.toUpperCase();
    if (act.includes("WIN") || act === "CREDIT") {
      return "bg-emerald-950/80 border-emerald-600/50 text-emerald-400";
    }
    if (act.includes("BET") || act === "DEBIT") {
      return "bg-amber-950/80 border-amber-600/50 text-amber-400";
    }
    if (act.includes("AUTH") || act.includes("LOGIN")) {
      return "bg-cyan-950/80 border-cyan-600/50 text-cyan-400";
    }
    return "bg-purple-950/80 border-purple-600/50 text-purple-400";
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col text-gray-100">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-6">
        {/* Cabecera del Módulo Forense */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400">
              <FileSearch className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-white tracking-tight">
                Auditoría Forense & Cumplimiento
              </h1>
              <p className="text-xs text-gray-400">
                Pista de auditoría inmutable de operaciones financieras y eventos de juego
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchLogs(currentPage)}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold border border-gray-700 transition"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
              <span>Actualizar Registros</span>
            </button>
          </div>
        </div>

        {/* Barra de Filtros */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-xl">
          <form onSubmit={handleFilterSubmit} className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                Acción / Operación
              </label>
              <select
                value={selectedAction}
                onChange={(e) => setSelectedAction(e.target.value)}
                className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-xl text-xs text-white focus:outline-none focus:border-amber-500"
              >
                <option value="">Todas las acciones</option>
                <option value="CREDIT">CREDIT (Recarga / Faucet)</option>
                <option value="DEBIT">DEBIT (Retiro / Débito)</option>
                <option value="BET_SIMULATION">BET_SIMULATION (Apuesta)</option>
                <option value="WIN_SIMULATION">WIN_SIMULATION (Premio)</option>
                <option value="BONUS">BONUS</option>
                <option value="ADJUSTMENT">ADJUSTMENT</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                Fecha Desde
              </label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-xl text-xs text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                Fecha Hasta
              </label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-xl text-xs text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-black uppercase tracking-wider transition flex items-center justify-center gap-1.5 shadow-md shadow-amber-500/20"
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Filtrar</span>
              </button>
              {(selectedAction || startDate || endDate) && (
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="px-3 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white text-xs border border-gray-700"
                >
                  Limpiar
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Mensaje de Error */}
        {errorMessage && (
          <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-300 rounded-xl text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Tabla de Registros Forenses */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-2xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-gray-800 flex items-center justify-between">
            <span className="text-xs font-bold text-gray-300">
              Mostrando {auditData.items.length} de {auditData.total} registros forenses
            </span>
            <span className="text-xs text-gray-500 font-mono">
              Página {currentPage} de {totalPages}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider text-[10px] bg-gray-950/60 font-sans">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Acción</th>
                  <th className="py-3 px-4">Recurso</th>
                  <th className="py-3 px-4">Usuario / Operador</th>
                  <th className="py-3 px-4">IP Origen</th>
                  <th className="py-3 px-4 text-right">Detalle Forense</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {auditData.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-gray-500 font-sans">
                      {isLoading ? "Cargando registros forenses..." : "No se encontraron logs con los criterios seleccionados."}
                    </td>
                  </tr>
                ) : (
                  auditData.items.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-800/40 transition">
                      <td className="py-3.5 px-4 text-gray-400 whitespace-nowrap">
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-gray-500" />
                          {new Date(log.created_at).toISOString().replace("T", " ").substring(0, 19)}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap font-sans">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold border ${getActionBadgeColor(
                            log.action
                          )}`}
                        >
                          {log.action}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-gray-300 whitespace-nowrap">
                        {log.resource_type}
                      </td>

                      <td className="py-3.5 px-4 text-gray-400 whitespace-nowrap">
                        <div className="flex flex-col text-[11px]">
                          <span>U: {log.user_id ? log.user_id.substring(0, 8) + "..." : "SYSTEM"}</span>
                          <span className="text-[10px] text-gray-500">
                            Op: {log.operator_id ? log.operator_id.substring(0, 8) + "..." : "—"}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-gray-400 whitespace-nowrap">
                        {log.ip_address || "127.0.0.1"}
                      </td>

                      <td className="py-3.5 px-4 text-right whitespace-nowrap font-sans">
                        <button
                          type="button"
                          onClick={() => setActiveLogDetail(log)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-amber-400 text-xs font-semibold border border-gray-700 transition"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Inspeccionar</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Paginador */}
          <div className="p-4 border-t border-gray-800 flex items-center justify-between">
            <button
              onClick={() => fetchLogs(currentPage - 1)}
              disabled={currentPage <= 1 || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition border border-gray-700"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Anterior</span>
            </button>

            <span className="text-xs text-gray-400">
              Página {currentPage} de {totalPages}
            </span>

            <button
              onClick={() => fetchLogs(currentPage + 1)}
              disabled={currentPage >= totalPages || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition border border-gray-700"
            >
              <span>Siguiente</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>

      {/* Modal de Detalle Forense JSON */}
      {activeLogDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-2xl bg-gray-900 border border-amber-500/40 rounded-3xl p-6 shadow-2xl relative">
            <button
              onClick={() => setActiveLogDetail(null)}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white rounded-full bg-gray-800"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 bg-amber-500/15 rounded-xl text-amber-400">
                <Terminal className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Inspección Forense de Evento</h3>
                <span className="text-xs text-gray-400 font-mono">ID: {activeLogDetail.id}</span>
              </div>
            </div>

            <div className="bg-black/90 p-4 rounded-2xl border border-gray-800 font-mono text-xs overflow-x-auto max-h-[400px]">
              <pre className="text-amber-300">
                {JSON.stringify(activeLogDetail, null, 2)}
              </pre>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setActiveLogDetail(null)}
                className="px-5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-xs font-bold"
              >
                Cerrar Detalle
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
