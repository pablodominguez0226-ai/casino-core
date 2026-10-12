import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useWallet } from "../../context/WalletContext";
import {
  Gamepad2,
  FileSearch,
  BarChart3,
  LogOut,
  Coins,
  AlertTriangle,
  User as UserIcon,
} from "lucide-react";

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, logout, hasAnyRole } = useAuth();
  const { balance, currency } = useWallet();
  const location = useLocation();

  const canAccessAudit = hasAnyRole(["SUPER_ADMIN", "COMPLIANCE"]);
  const canAccessReports = hasAnyRole([
    "SUPER_ADMIN",
    "OPERATOR_ADMIN",
    "FINANCE",
    "GAME_MANAGER",
  ]);

  return (
    <header className="sticky top-0 z-40 w-full flex flex-col border-b border-gray-800 bg-[#0B0F17]/95 backdrop-blur-md">
      {/* 2. Banner Persistente de Moneda Virtual y Simulación Educativa */}
      <div className="w-full bg-gradient-to-r from-amber-600 via-yellow-600 to-amber-600 text-black py-1 px-4 text-center text-[11px] font-black tracking-wider uppercase flex items-center justify-center gap-2 select-none shadow-sm">
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span>Entorno Educativo / Simulación — Sin Apuestas Reales — Toda cifra en VIRTUAL CREDITS</span>
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
      </div>

      {/* Barra de Navegación Principal */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Marca / Logo */}
        <div className="flex items-center gap-8">
          <Link to="/play" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-600 to-yellow-400 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:scale-105 transition">
              <span className="text-black font-black text-lg">C</span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-black tracking-tight text-white group-hover:text-amber-400 transition">
                Casino<span className="text-amber-400">Core</span>
              </span>
              <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest -mt-1">
                B2B Modular
              </span>
            </div>
          </Link>

          {/* Links de Navegación */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center gap-1">
              <Link
                to="/play"
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition ${
                  location.pathname === "/play"
                    ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                <Gamepad2 className="w-4 h-4" />
                <span>Slot Lobby</span>
              </Link>

              {canAccessReports && (
                <Link
                  to="/admin/reports"
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition ${
                    location.pathname === "/admin/reports"
                      ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Reportes & Analíticas</span>
                </Link>
              )}

              {canAccessAudit && (
                <Link
                  to="/admin/audit"
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition ${
                    location.pathname === "/admin/audit"
                      ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                  }`}
                >
                  <FileSearch className="w-4 h-4" />
                  <span>Auditoría Forense</span>
                </Link>
              )}
            </nav>
          )}
        </div>

        {/* Acciones de Usuario y Balance */}
        {isAuthenticated && user ? (
          <div className="flex items-center gap-4">
            {/* Widget Rápido de Saldo */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gray-900 border border-amber-500/40">
              <Coins className="w-4 h-4 text-amber-400" />
              <div className="flex items-baseline gap-1">
                <span className="text-sm font-black text-amber-400">
                  {balance.toLocaleString()}
                </span>
                <span className="text-[10px] font-bold text-amber-500/80">
                  {currency}
                </span>
              </div>
            </div>

            {/* Perfil & Roles */}
            <div className="flex items-center gap-3">
              <div className="hidden lg:flex flex-col text-right">
                <span className="text-xs font-semibold text-gray-200 truncate max-w-[150px]">
                  {user.email}
                </span>
                <div className="flex items-center gap-1 justify-end mt-0.5">
                  {user.roles.map((role) => (
                    <span
                      key={role}
                      className="text-[9px] px-1.5 py-0.2 rounded bg-gray-800 text-amber-300 font-mono"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-2 rounded-xl bg-gray-800/80 border border-gray-700 text-gray-300">
                <UserIcon className="w-4 h-4" />
              </div>

              {/* Botón Salir */}
              <button
                type="button"
                onClick={logout}
                className="p-2 rounded-xl bg-gray-800/80 hover:bg-rose-950/80 hover:text-rose-400 border border-gray-700 hover:border-rose-700/60 text-gray-300 transition"
                title="Cerrar Sesión"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 text-xs font-bold text-gray-300 hover:text-white transition"
            >
              Iniciar Sesión
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition shadow-md shadow-amber-500/20"
            >
              Registrarse
            </Link>
          </div>
        )}
      </div>
    </header>
  );
};
