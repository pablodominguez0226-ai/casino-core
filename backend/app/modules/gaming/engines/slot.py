"""3-Reel Slot Simulator Engine.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from typing import Any

from app.modules.gaming.engines.rng import IRNGProvider
from app.modules.gaming.enums import SlotSymbol


class _SpinCallable:
    """Descriptor enabling spin() invocation on either class or instance."""

    def __init__(self, func: Any) -> None:
        self.func = func

    def __get__(self, instance: Any, owner: Any) -> Any:
        if instance is None:
            def class_spin(
                rng: IRNGProvider,
                bet_amount: int,
                reels: tuple[list[SlotSymbol], list[SlotSymbol], list[SlotSymbol]] | None = None,
                paytable: dict[SlotSymbol, int] | None = None,
            ) -> tuple[list[SlotSymbol], list[int], int]:
                active_reels = reels or (owner.REEL_1, owner.REEL_2, owner.REEL_3)
                active_paytable = paytable or owner.PAYTABLE
                return owner._execute_spin(rng, bet_amount, active_reels, active_paytable)

            return class_spin
        else:
            def instance_spin(
                rng: IRNGProvider,
                bet_amount: int,
                reels: tuple[list[SlotSymbol], list[SlotSymbol], list[SlotSymbol]] | None = None,
                paytable: dict[SlotSymbol, int] | None = None,
            ) -> tuple[list[SlotSymbol], list[int], int]:
                active_reels = reels or instance.reels
                active_paytable = paytable or instance.paytable
                return owner._execute_spin(rng, bet_amount, active_reels, active_paytable)

            return instance_spin


class SlotEngine:
    """Educational 3-reel classic slot simulator engine.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    # Default reel strips composed of SlotSymbol elements
    REEL_1: list[SlotSymbol] = [
        SlotSymbol.CHERRY,
        SlotSymbol.LEMON,
        SlotSymbol.ORANGE,
        SlotSymbol.BELL,
        SlotSymbol.SEVEN,
    ]
    REEL_2: list[SlotSymbol] = [
        SlotSymbol.CHERRY,
        SlotSymbol.LEMON,
        SlotSymbol.ORANGE,
        SlotSymbol.BELL,
        SlotSymbol.SEVEN,
    ]
    REEL_3: list[SlotSymbol] = [
        SlotSymbol.CHERRY,
        SlotSymbol.LEMON,
        SlotSymbol.ORANGE,
        SlotSymbol.BELL,
        SlotSymbol.SEVEN,
    ]

    # Paytable with multipliers for 3 matching symbols
    PAYTABLE: dict[SlotSymbol, int] = {
        SlotSymbol.SEVEN: 100,
        SlotSymbol.BELL: 25,
        SlotSymbol.ORANGE: 10,
        SlotSymbol.LEMON: 5,
        SlotSymbol.CHERRY: 2,
    }

    def __init__(
        self,
        reels: tuple[list[SlotSymbol], list[SlotSymbol], list[SlotSymbol]] | None = None,
        paytable: dict[SlotSymbol, int] | None = None,
    ) -> None:
        self.reels = reels or (list(self.REEL_1), list(self.REEL_2), list(self.REEL_3))
        self.paytable = paytable or dict(self.PAYTABLE)

    @classmethod
    def _execute_spin(
        cls,
        rng: IRNGProvider,
        bet_amount: int,
        reels: tuple[list[SlotSymbol], list[SlotSymbol], list[SlotSymbol]],
        paytable: dict[SlotSymbol, int],
    ) -> tuple[list[SlotSymbol], list[int], int]:
        """Perform spin resolution with stops, visible central line symbols, and payout."""
        if bet_amount <= 0:
            raise ValueError(f"bet_amount must be positive, got {bet_amount}")

        stops = [
            rng.generate_int(0, len(reels[i]) - 1)
            for i in range(3)
        ]
        symbols = [reels[i][stops[i]] for i in range(3)]

        multiplier = 0
        if symbols[0] == symbols[1] == symbols[2]:
            multiplier = paytable.get(symbols[0], 0)

        payout_amount = bet_amount * multiplier
        return symbols, stops, payout_amount

    @_SpinCallable
    def spin(
        self,
        rng: IRNGProvider,
        bet_amount: int,
        reels: tuple[list[SlotSymbol], list[SlotSymbol], list[SlotSymbol]] | None = None,
        paytable: dict[SlotSymbol, int] | None = None,
    ) -> tuple[list[SlotSymbol], list[int], int]:
        """Generate 3 stops with rng, evaluate matching symbols, and return (symbols, stops, payout_amount)."""
        pass
