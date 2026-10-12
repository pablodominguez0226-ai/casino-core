import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Role } from "../../types/auth";
import { ShieldAlert } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: Role[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles,
}) => {
  const { isAuthenticated, isLoading, hasAnyRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0F17] flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Verificando sesión criptográfica...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRoles && requiredRoles.length > 0 && !hasAnyRole(requiredRoles)) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <div className="p-4 bg-rose-950/60 border border-rose-800 rounded-3xl text-rose-400 mb-4 shadow-xl">
          <ShieldAlert className="w-12 h-12" />
        </div>
        <h2 className="text-xl font-black text-white mb-2">Acceso Restringido</h2>
        <p className="text-sm text-gray-400 max-w-md mb-6">
          Tu cuenta no posee los permisos requeridos ({requiredRoles.join(", ")}) para acceder a este módulo forense.
        </p>
        <a
          href="/play"
          className="px-5 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-amber-400 text-xs font-bold border border-gray-700 transition"
        >
          Volver al Slot Lobby
        </a>
      </div>
    );
  }

  return <>{children}</>;
};
