"""Unit tests for SlotEngine simulator.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import pytest

from app.modules.gaming.engines.rng import DeterministicRNGProvider
from app.modules.gaming.engines.slot import SlotEngine
from app.modules.gaming.enums import SlotSymbol


def test_slot_engine_jackpot_three_sevens() -> None:
    """Validate jackpot payout (100x) when 3 SEVEN symbols are hit."""
    # Index 4 corresponds to SEVEN in REEL_1, REEL_2, REEL_3
    rng = DeterministicRNGProvider([4, 4, 4])
    bet_amount = 50

    symbols, stops, payout = SlotEngine.spin(rng, bet_amount)

    assert stops == [4, 4, 4]
    assert symbols == [SlotSymbol.SEVEN, SlotSymbol.SEVEN, SlotSymbol.SEVEN]
    assert payout == bet_amount * 100
    assert payout == 5000


def test_slot_engine_losing_spin_zero_payout() -> None:
    """Validate that non-matching symbols yield zero payout."""
    # Stops: 0 (CHERRY), 1 (LEMON), 2 (ORANGE)
    rng = DeterministicRNGProvider([0, 1, 2])
    bet_amount = 100

    symbols, stops, payout = SlotEngine.spin(rng, bet_amount)

    assert stops == [0, 1, 2]
    assert symbols == [SlotSymbol.CHERRY, SlotSymbol.LEMON, SlotSymbol.ORANGE]
    assert payout == 0


@pytest.mark.parametrize(
    ("stop_index", "expected_symbol", "expected_multiplier"),
    [
        (0, SlotSymbol.CHERRY, 2),
        (1, SlotSymbol.LEMON, 5),
        (2, SlotSymbol.ORANGE, 10),
        (3, SlotSymbol.BELL, 25),
        (4, SlotSymbol.SEVEN, 100),
    ],
)
def test_slot_engine_all_winning_combinations(
    stop_index: int,
    expected_symbol: SlotSymbol,
    expected_multiplier: int,
) -> None:
    """Validate all defined paytable multipliers for three matching symbols."""
    rng = DeterministicRNGProvider([stop_index, stop_index, stop_index])
    bet_amount = 20

    symbols, stops, payout = SlotEngine.spin(rng, bet_amount)

    assert symbols == [expected_symbol, expected_symbol, expected_symbol]
    assert payout == bet_amount * expected_multiplier


def test_slot_engine_instance_execution() -> None:
    """Validate that engine instance spin execution behaves identically."""
    engine = SlotEngine()
    rng = DeterministicRNGProvider([3, 3, 3])  # 3 BELLs -> 25x
    bet = 10

    symbols, stops, payout = engine.spin(rng, bet)
    assert symbols == [SlotSymbol.BELL, SlotSymbol.BELL, SlotSymbol.BELL]
    assert payout == 250


def test_slot_engine_invalid_bet_raises_error() -> None:
    """Validate that non-positive bet amount raises ValueError."""
    rng = DeterministicRNGProvider([0, 0, 0])
    with pytest.raises(ValueError):
        SlotEngine.spin(rng, 0)
    with pytest.raises(ValueError):
        SlotEngine.spin(rng, -10)
