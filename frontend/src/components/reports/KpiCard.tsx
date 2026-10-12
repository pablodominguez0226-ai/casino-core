import React from "react";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  clarification?: string;
  colorScheme?: "amber" | "emerald" | "blue" | "purple" | "rose" | "cyan";
  badge?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  icon,
  subtitle,
  clarification = "Créditos Simulados",
  colorScheme = "amber",
  badge,
}) => {
  const colorMap = {
    amber: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      glow: "shadow-amber-500/5",
    },
    emerald: {
      border: "border-emerald-500/30",
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      glow: "shadow-emerald-500/5",
    },
    blue: {
      border: "border-blue-500/30",
      bg: "bg-blue-500/10",
      text: "text-blue-400",
      glow: "shadow-blue-500/5",
    },
    purple: {
      border: "border-purple-500/30",
      bg: "bg-purple-500/10",
      text: "text-purple-400",
      glow: "shadow-purple-500/5",
    },
    rose: {
      border: "border-rose-500/30",
      bg: "bg-rose-500/10",
      text: "text-rose-400",
      glow: "shadow-rose-500/5",
    },
    cyan: {
      border: "border-cyan-500/30",
      bg: "bg-cyan-500/10",
      text: "text-cyan-400",
      glow: "shadow-cyan-500/5",
    },
  };

  const colors = colorMap[colorScheme];

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-[#111827] border ${colors.border} p-5 flex flex-col justify-between shadow-lg ${colors.glow} transition-all hover:scale-[1.01] hover:border-opacity-60`}
    >
      {/* Cabecera de la Tarjeta */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-col">
          <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
            {title}
          </span>
          {subtitle && (
            <span className="text-[11px] text-gray-400 mt-0.5">{subtitle}</span>
          )}
        </div>
        <div className={`p-2.5 rounded-xl ${colors.bg} ${colors.text} shrink-0`}>
          {icon}
        </div>
      </div>

      {/* Valor Principal */}
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-2xl sm:text-3xl font-black tracking-tight text-white">
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {badge && (
          <span
            className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded ${colors.bg} ${colors.text} border ${colors.border}`}
          >
            {badge}
          </span>
        )}
      </div>

      {/* Etiqueta Aclaratoria de Simulación */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-800/80 text-[10px] font-semibold text-gray-400">
        <span className="inline-flex items-center gap-1 text-amber-500/80 font-mono tracking-tight">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          {clarification}
        </span>
      </div>
    </div>
  );
};
