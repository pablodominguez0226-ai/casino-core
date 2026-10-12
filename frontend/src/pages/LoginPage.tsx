import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Lock, Mail, Building, AlertCircle, ArrowRight, Sparkles } from "lucide-react";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState<string>("player@casino.com");
  const [password, setPassword] = useState<string>("Password123!");
  const [operatorSlug, setOperatorSlug] = useState<string>("casino-royal");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/play";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login({
        email,
        password,
        operator_slug: operatorSlug,
      });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error de credenciales o de operador tenant";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillDemoPlayer = () => {
    setEmail("player@casino.com");
    setPassword("Password123!");
    setOperatorSlug("casino-royal");
  };

  const fillDemoAdmin = () => {
    setEmail("admin@casino.com");
    setPassword("AdminPassword123!");
    setOperatorSlug("casino-royal");
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Luces de fondo decorativas */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-72 h-72 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />

      {/* Banner Superior Educativo */}
      <div className="mb-6 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
        <span>Entorno Educativo / Simulación — Sin Apuestas Reales</span>
      </div>

      <div className="w-full max-w-md bg-gray-900/90 border border-amber-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative z-10">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-600 to-yellow-400 flex items-center justify-center shadow-lg shadow-amber-500/25 mb-3">
            <span className="text-black font-black text-2xl">C</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Acceso a Casino<span className="text-amber-400">Core</span>
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Plataforma B2B Multi-tenant con Billetera Virtual Transaccional
          </p>
        </div>

        {/* Carga rápida de credenciales de prueba */}
        <div className="mb-6 p-3 rounded-2xl bg-black/60 border border-gray-800 flex flex-col gap-2">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider text-center">
            Perfiles de Prueba Rápida
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={fillDemoPlayer}
              className="py-1.5 px-3 rounded-xl bg-gray-800/80 hover:bg-gray-700 text-amber-400 text-xs font-semibold border border-amber-500/20 transition"
            >
              Jugador Demo
            </button>
            <button
              type="button"
              onClick={fillDemoAdmin}
              className="py-1.5 px-3 rounded-xl bg-gray-800/80 hover:bg-gray-700 text-emerald-400 text-xs font-semibold border border-emerald-500/20 transition"
            >
              Auditor / Admin
            </button>
          </div>
        </div>

        {errorMessage && (
          <div className="mb-5 p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Slug del Operador Tenant
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500">
                <Building className="w-4 h-4" />
              </div>
              <input
                type="text"
                required
                value={operatorSlug}
                onChange={(e) => setOperatorSlug(e.target.value)}
                placeholder="ej. casino-royal"
                className="w-full pl-10 pr-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Correo Electrónico
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nombre@ejemplo.com"
                className="w-full pl-10 pr-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Contraseña
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500 text-black font-black uppercase text-sm tracking-wider flex items-center justify-center gap-2 hover:from-amber-400 hover:to-yellow-300 transition shadow-lg shadow-amber-500/25 disabled:opacity-50 active:scale-[0.98]"
            >
              {isSubmitting ? (
                <span>Autenticando...</span>
              ) : (
                <>
                  <span>Ingresar a la Plataforma</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center text-xs text-gray-400">
          ¿No tienes una cuenta aún?{" "}
          <Link to="/register" className="text-amber-400 font-bold hover:underline">
            Registrar Jugador
          </Link>
        </div>
      </div>
    </div>
  );
};
