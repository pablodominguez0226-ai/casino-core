import React from "react";
import { Navbar } from "../components/layout/Navbar";
import { BalanceWidget } from "../components/wallet/BalanceWidget";
import { SlotMachine } from "../components/slot/SlotMachine";
import { LedgerTable } from "../components/wallet/LedgerTable";
import { useWallet } from "../context/WalletContext";

export const SlotGamePage: React.FC = () => {
  const { recentLedger, isLoading, fetchLedger } = useWallet();

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col text-gray-100">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">
        {/* Widget Superior de Balance y Faucet */}
        <section aria-label="Billetera y Créditos">
          <BalanceWidget />
        </section>

        {/* Tragamonedas Principal */}
        <section aria-label="Máquina Tragamonedas" className="my-2">
          <SlotMachine />
        </section>

        {/* Historial de Transacciones (Ledger Inmutable) */}
        <section aria-label="Historial Ledger">
          <LedgerTable
            entries={recentLedger}
            isLoading={isLoading}
            onRefresh={() => fetchLedger(20)}
          />
        </section>
      </main>

      <footer className="w-full py-6 border-t border-gray-800 text-center text-xs text-gray-500">
        CasinoCore Gaming Engine — Simulación Educativa con Cero Valor Monetario Real.
      </footer>
    </div>
  );
};
