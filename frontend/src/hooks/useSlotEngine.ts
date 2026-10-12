import { useCallback, useEffect, useState } from "react";
import { gamesApi } from "../api/games.api";
import { Game, GameSession, SpinResponse } from "../types/gaming";
import { soundManager } from "../utils/audio";
import { useWallet } from "../context/WalletContext";

export function useSlotEngine() {
  const { balance, updateBalanceLocally } = useWallet();

  const [game, setGame] = useState<Game | null>(null);
  const [session, setSession] = useState<GameSession | null>(null);
  const [reels, setReels] = useState<string[]>(["SEVEN", "BELL", "CHERRY"]);
  const [isSpinning, setIsSpinning] = useState<boolean>(false);
  const [spinningReels, setSpinningReels] = useState<boolean[]>([false, false, false]);
  const [betAmount, setBetAmount] = useState<number>(10);
  const [lastPayout, setLastPayout] = useState<number>(0);
  const [lastWin, setLastWin] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState<boolean>(true);

  // Inicializar juego y sesión activa
  const initGame = useCallback(async () => {
    setIsLoadingCatalog(true);
    setErrorMessage(null);
    try {
      const catalog = await gamesApi.listGames();
      const classicSlot = catalog.find((g) => g.code === "CLASSIC_FRUIT_SLOT" && g.is_active) || catalog[0];

      if (!classicSlot) {
        setErrorMessage("No hay juegos activos disponibles en el operador.");
        return;
      }

      setGame(classicSlot);
      setBetAmount(classicSlot.min_bet);

      const newSession = await gamesApi.createSession(classicSlot.id);
      setSession(newSession);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al iniciar la sesión de juego";
      setErrorMessage(msg);
    } finally {
      setIsLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    initGame();
  }, [initGame]);

  const spin = async (): Promise<SpinResponse | null> => {
    if (isSpinning) return null;

    if (!game || !session) {
      setErrorMessage("Sesión de juego no activa. Reiniciando...");
      await initGame();
      return null;
    }

    if (balance < betAmount) {
      setErrorMessage("Saldo insuficiente en VIRTUAL CREDITS. Utiliza el Faucet educativo para recargar.");
      return null;
    }

    if (betAmount < game.min_bet || betAmount > game.max_bet) {
      setErrorMessage(`La apuesta debe estar entre ${game.min_bet} y ${game.max_bet} CREDITS.`);
      return null;
    }

    setErrorMessage(null);
    setIsSpinning(true);
    setSpinningReels([true, true, true]);
    setLastWin(false);
    setLastPayout(0);

    soundManager.playSpin();
    const startTime = Date.now();

    try {
      const response = await gamesApi.executeSpin(session.id, { bet_amount: betAmount });

      // Garantizar un mínimo de 1.2 segundos de animación fluida
      const elapsed = Date.now() - startTime;
      const minDuration = 1200;
      if (elapsed < minDuration) {
        await new Promise((resolve) => setTimeout(resolve, minDuration - elapsed));
      }

      // Detener primer rodillo
      setReels((prev) => [response.symbols[0], prev[1], prev[2]]);
      setSpinningReels([false, true, true]);
      soundManager.playReelStop(0);

      // Detener segundo rodillo tras 220ms
      await new Promise((resolve) => setTimeout(resolve, 220));
      setReels((prev) => [prev[0], response.symbols[1], prev[2]]);
      setSpinningReels([false, false, true]);
      soundManager.playReelStop(1);

      // Detener tercer rodillo tras 220ms
      await new Promise((resolve) => setTimeout(resolve, 220));
      setReels([response.symbols[0], response.symbols[1], response.symbols[2]]);
      setSpinningReels([false, false, false]);
      soundManager.playReelStop(2);

      // Notificar resultados del servidor
      setLastPayout(response.payout_amount);
      setLastWin(response.is_win);

      // Actualizar balance con la cifra exacta provista por el servidor
      updateBalanceLocally(response.current_balance);

      if (response.is_win) {
        if (response.payout_amount >= betAmount * 25) {
          soundManager.playJackpot();
        } else {
          soundManager.playWin();
        }
      }

      return response;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al procesar el giro en el servidor.";
      setErrorMessage(msg);
      setSpinningReels([false, false, false]);
      return null;
    } finally {
      setIsSpinning(false);
    }
  };

  return {
    game,
    session,
    reels,
    isSpinning,
    spinningReels,
    betAmount,
    setBetAmount,
    lastPayout,
    lastWin,
    errorMessage,
    isLoadingCatalog,
    spin,
    initGame,
  };
}
