import React, { useCallback, useEffect, useState } from "react";
import { Navbar } from "../components/layout/Navbar";
import { reportsApi } from "../api/reports.api";
import {
  DailyTrendsResponse,
  GamePerformanceReportResponse,
  OverviewMetrics,
  WalletFlowReportResponse,
} from "../types/reports";
import { KpiCard } from "../components/reports/KpiCard";
import { GamesTable } from "../components/reports/GamesTable";
import { WalletFlowCard } from "../components/reports/WalletFlowCard";
import { DailyTrendsCard } from "../components/reports/DailyTrendsCard";
import {
  AlertTriangle,
  BarChart3,
  Calendar,
  Percent,
  RefreshCw,
  TrendingUp,
  Users,
  Wallet,
  Zap,
} from "lucide-react";

export const AdminReportsPage: React.FC = () => {
  const [fromDate, setFromDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [toDate, setToDate] = useState<string>(() => {
    return new Date().toISOString().split("T")[0];
  });

  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [gameReport, setGameReport] = useState<GamePerformanceReportResponse | null>(null);
  const [walletFlow, setWalletFlow] = useState<WalletFlowReportResponse | null>(null);
  const [dailyTrends, setDailyTrends] = useState<DailyTrendsResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const fromIso = fromDate ? new Date(`${fromDate}T00:00:00Z`).toISOString() : undefined;
    const toIso = toDate ? new Date(`${toDate}T23:59:59Z`).toISOString() : undefined;

    try {
      const [overviewData, gamesData, flowData, trendsData] = await Promise.all([
        reportsApi.getOverview({ from_date: fromIso, to_date: toIso }),
        reportsApi.getGamePerformance({ from_date: fromIso, to_date: toIso }),
        reportsApi.getWalletFlow({ from_date: fromIso, to_date: toIso }),
        reportsApi.getDailyTrends(14),
      ]);

      setOverview(overviewData);
      setGameReport(gamesData);
      setWalletFlow(flowData);
      setDailyTrends(trendsData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar las analíticas operativas";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handlePreset = (days: number) => {
    const now = new Date();
    const past = new Date();
    past.setDate(past.getDate() - days);

    setFromDate(past.toISOString().split("T")[0]);
    setToDate(now.toISOString().split("T")[0]);
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col text-gray-100">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">
        {/* Encabezado y Selector Temporal */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 border-b border-gray-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400 shrink-0">
              <BarChart3 className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-white tracking-tight">
                  Reportes & Analíticas Operativas
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  Sprint 7
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Motor analítico B2B: balance monetario simulado, volumen de juego y convergencia de RTP.
              </p>
            </div>
          </div>

          {/* Filtros de Rango Temporal */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 text-xs">
              <button
                type="button"
                onClick={() => handlePreset(7)}
                className="px-2.5 py-1.5 rounded-lg hover:bg-gray-800 text-gray-300 font-bold transition"
              >
                7D
              </button>
              <button
                type="button"
                onClick={() => handlePreset(14)}
                className="px-2.5 py-1.5 rounded-lg hover:bg-gray-800 text-gray-300 font-bold transition"
              >
                14D
              </button>
              <button
                type="button"
                onClick={() => handlePreset(30)}
                className="px-2.5 py-1.5 rounded-lg hover:bg-gray-800 text-gray-300 font-bold transition"
              >
                30D
              </button>
            </div>

            <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-xl text-xs">
              <Calendar className="w-3.5 h-3.5 text-gray-400" />
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="bg-transparent text-gray-200 outline-none text-xs"
              />
              <span className="text-gray-500">→</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="bg-transparent text-gray-200 outline-none text-xs"
              />
            </div>

            <button
              type="button"
              onClick={fetchReports}
              disabled={isLoading}
              className="p-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-bold transition flex items-center justify-center disabled:opacity-50 shadow-md shadow-amber-500/20"
              title="Refrescar métricas"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Advertencia Mandatoria del Entorno Educativo */}
        <div className="bg-amber-950/25 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-200/90 leading-relaxed">
            <span className="font-bold text-amber-400">Aviso de Entorno Educativo y Moneda Virtual:</span>{" "}
            Todas las cifras mostradas en este panel corresponden estrictamente a créditos simulados (
            <span className="font-mono font-bold text-amber-300">VIRTUAL CREDITS</span>). No existe dinero
            real, conversión fiduciaria ni intermediación financiera.
          </div>
        </div>

        {/* Mensaje de Error si falla la API */}
        {errorMessage && (
          <div className="bg-rose-950/40 border border-rose-800/80 rounded-2xl p-4 text-xs text-rose-300">
            {errorMessage}
          </div>
        )}

        {/* Grilla de KPIs Principales */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <KpiCard
            title="Usuarios Activos (DAU)"
            value={overview?.daily_active_users ?? 0}
            icon={<Users className="w-5 h-5" />}
            subtitle="Actividad en últimas 24h"
            colorScheme="cyan"
            clarification="Jugadores únicos"
          />

          <KpiCard
            title="Turnover en Créditos"
            value={overview?.total_turnover_credits ?? 0}
            icon={<Zap className="w-5 h-5" />}
            subtitle="Volumen total de apuestas"
            colorScheme="amber"
            badge="Simulado"
          />

          <KpiCard
            title="GGR Simulado"
            value={overview?.simulated_ggr_credits ?? 0}
            icon={<TrendingUp className="w-5 h-5" />}
            subtitle="Turnover - Premios"
            colorScheme="emerald"
            badge="Margen"
          />

          <KpiCard
            title="RTP Promedio"
            value={`${overview?.overall_observed_rtp?.toFixed(2) ?? "0.00"}%`}
            icon={<Percent className="w-5 h-5" />}
            subtitle="Retorno Observado Global"
            colorScheme="purple"
            clarification="Convergencia Teórica"
          />

          <KpiCard
            title="Créditos Circulantes"
            value={overview?.circulating_virtual_credits ?? 0}
            icon={<Wallet className="w-5 h-5" />}
            subtitle="Suma total de wallets"
            colorScheme="blue"
            clarification="Pool de Créditos"
          />
        </div>

        {/* Métricas Secundarias de Operación */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-[#111827] border border-gray-800 flex items-center justify-between">
            <span className="text-xs text-gray-400 font-semibold">Total Jugadores Registrados</span>
            <span className="text-lg font-black text-white font-mono">
              {overview?.total_players.toLocaleString() ?? 0}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#111827] border border-gray-800 flex items-center justify-between">
            <span className="text-xs text-gray-400 font-semibold">Sesiones de Juego Iniciadas</span>
            <span className="text-lg font-black text-white font-mono">
              {overview?.total_sessions.toLocaleString() ?? 0}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#111827] border border-gray-800 flex items-center justify-between">
            <span className="text-xs text-gray-400 font-semibold">Total Rondas Ejecutadas</span>
            <span className="text-lg font-black text-white font-mono">
              {overview?.total_game_rounds.toLocaleString() ?? 0}
            </span>
          </div>
        </div>

        {/* Sección de Rendimiento de Catálogo de Juegos */}
        <GamesTable
          items={gameReport?.items ?? []}
          isLoading={isLoading}
        />

        {/* Sección de Flujo de Ledger y Tendencias Diarias */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <WalletFlowCard
            data={walletFlow}
            isLoading={isLoading}
          />

          <DailyTrendsCard
            data={dailyTrends}
            isLoading={isLoading}
          />
        </div>
      </main>
    </div>
  );
};
