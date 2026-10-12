"""Unit tests for the European Roulette Engine.

Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
"""
import pytest

from app.modules.gaming.engines.rng import DeterministicRNGProvider
from app.modules.gaming.engines.roulette import (
    RouletteBet,
    RouletteBetType,
    RouletteEngine,
    RouletteOutcome,
)


def test_roulette_engine_deterministic_number_17_wins_and_losses() -> None:
    """Test with deterministic RNG forcing winning number 17 (Black, Odd, 2nd Dozen, Low, Col 2).

    Verifies:
    - STRAIGHT_UP (17) pays 36x gross.
    - BLACK pays 2x gross.
    - RED pays 0x gross.
    - ODD pays 2x gross.
    - EVEN pays 0x gross.
    - DOZEN (2) pays 3x gross.
    - DOZEN (1) pays 0x gross.
    - Outcome metadata: number=17, color='BLACK', is_even=False.
    """
    rng = DeterministicRNGProvider([17])
    bets = [
        RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[17], amount=10),
        RouletteBet(bet_type=RouletteBetType.BLACK, amount=20),
        RouletteBet(bet_type=RouletteBetType.RED, amount=30),
        RouletteBet(bet_type=RouletteBetType.ODD, amount=15),
        RouletteBet(bet_type=RouletteBetType.EVEN, amount=25),
        RouletteBet(bet_type=RouletteBetType.DOZEN, numbers=[2], amount=40),
        RouletteBet(bet_type=RouletteBetType.DOZEN, numbers=[1], amount=50),
        RouletteBet(bet_type=RouletteBetType.COLUMN, numbers=[2], amount=10),
    ]

    outcome: RouletteOutcome = RouletteEngine.spin(rng, bets)

    assert outcome.winning_number == 17
    assert outcome.color == "BLACK"
    assert outcome.is_even is False
    assert outcome.total_bet == 10 + 20 + 30 + 15 + 25 + 40 + 50 + 10

    # 1. STRAIGHT_UP 17 (paga 36x bruto = 360)
    res_straight = outcome.resolutions[0]
    assert res_straight.won is True
    assert res_straight.payout_amount == 360

    # 2. BLACK (paga 2x bruto = 40)
    res_black = outcome.resolutions[1]
    assert res_black.won is True
    assert res_black.payout_amount == 40

    # 3. RED (pierde = 0)
    res_red = outcome.resolutions[2]
    assert res_red.won is False
    assert res_red.payout_amount == 0

    # 4. ODD (paga 2x bruto = 30)
    res_odd = outcome.resolutions[3]
    assert res_odd.won is True
    assert res_odd.payout_amount == 30

    # 5. EVEN (pierde = 0)
    res_even = outcome.resolutions[4]
    assert res_even.won is False
    assert res_even.payout_amount == 0

    # 6. DOZEN 2 (13-24, paga 3x bruto = 120)
    res_doz2 = outcome.resolutions[5]
    assert res_doz2.won is True
    assert res_doz2.payout_amount == 120

    # 7. DOZEN 1 (1-12, pierde = 0)
    res_doz1 = outcome.resolutions[6]
    assert res_doz1.won is False
    assert res_doz1.payout_amount == 0

    # 8. COLUMN 2 (17 % 3 == 2, paga 3x bruto = 30)
    res_col2 = outcome.resolutions[7]
    assert res_col2.won is True
    assert res_col2.payout_amount == 30

    expected_total_payout = 360 + 40 + 0 + 30 + 0 + 120 + 0 + 30
    assert outcome.total_payout == expected_total_payout


def test_roulette_engine_deterministic_number_zero_green_outside_bets_lose() -> None:
    """Test with deterministic RNG forcing number 0 (Green).

    Verifies:
    - Outside bets (RED, BLACK, EVEN, ODD, LOW, HIGH, DOZEN, COLUMN) all lose.
    - Direct bet to STRAIGHT_UP (0) wins 36x gross.
    - Outcome metadata: number=0, color='GREEN', is_even=None.
    """
    rng = DeterministicRNGProvider([0])
    bets = [
        RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[0], amount=20),
        RouletteBet(bet_type=RouletteBetType.RED, amount=10),
        RouletteBet(bet_type=RouletteBetType.BLACK, amount=10),
        RouletteBet(bet_type=RouletteBetType.EVEN, amount=10),
        RouletteBet(bet_type=RouletteBetType.ODD, amount=10),
        RouletteBet(bet_type=RouletteBetType.LOW, amount=10),
        RouletteBet(bet_type=RouletteBetType.HIGH, amount=10),
        RouletteBet(bet_type=RouletteBetType.DOZEN, numbers=[1], amount=10),
        RouletteBet(bet_type=RouletteBetType.COLUMN, numbers=[1], amount=10),
    ]

    outcome = RouletteEngine.spin(rng, bets)

    assert outcome.winning_number == 0
    assert outcome.color == "GREEN"
    assert outcome.is_even is None

    # STRAIGHT_UP 0 wins 36x
    res_zero = outcome.resolutions[0]
    assert res_zero.won is True
    assert res_zero.payout_amount == 20 * 36

    # All outside bets lose
    for res in outcome.resolutions[1:]:
        assert res.won is False
        assert res.payout_amount == 0

    assert outcome.total_payout == 720


def test_roulette_engine_inside_bets_split_street_corner_sixline() -> None:
    """Test inside bets (SPLIT, STREET, CORNER, SIX_LINE) multipliers and evaluation."""
    # Force winning number 8 (Black, Even, 1st Dozen, Col 2)
    rng = DeterministicRNGProvider([8])
    bets = [
        RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[8, 9], amount=10),  # 18x
        RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[1, 2], amount=10),  # loses
        RouletteBet(bet_type=RouletteBetType.STREET, numbers=[7, 8, 9], amount=10),  # 12x
        RouletteBet(bet_type=RouletteBetType.CORNER, numbers=[4, 5, 7, 8], amount=10),  # 9x
        RouletteBet(bet_type=RouletteBetType.SIX_LINE, numbers=[7, 8, 9, 10, 11, 12], amount=10),  # 6x
        RouletteBet(bet_type=RouletteBetType.LOW, amount=10),  # 2x (8 is in 1-18)
        RouletteBet(bet_type=RouletteBetType.HIGH, amount=10),  # loses
    ]

    outcome = RouletteEngine.spin(rng, bets)
    assert outcome.winning_number == 8
    assert outcome.color == "BLACK"
    assert outcome.is_even is True

    assert outcome.resolutions[0].won is True
    assert outcome.resolutions[0].payout_amount == 180  # 18x

    assert outcome.resolutions[1].won is False
    assert outcome.resolutions[1].payout_amount == 0

    assert outcome.resolutions[2].won is True
    assert outcome.resolutions[2].payout_amount == 120  # 12x

    assert outcome.resolutions[3].won is True
    assert outcome.resolutions[3].payout_amount == 90  # 9x

    assert outcome.resolutions[4].won is True
    assert outcome.resolutions[4].payout_amount == 60  # 6x

    assert outcome.resolutions[5].won is True
    assert outcome.resolutions[5].payout_amount == 20  # 2x

    assert outcome.resolutions[6].won is False
    assert outcome.resolutions[6].payout_amount == 0


def test_roulette_engine_invalid_numbers_validation() -> None:
    """Validate that invalid numbers (< 0 or > 36) raise ValueError."""
    # Number > 36
    with pytest.raises(ValueError, match="Invalid roulette number"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[37], amount=10)
        )

    # Negative number
    with pytest.raises(ValueError, match="Invalid roulette number"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[-1], amount=10)
        )

    # Number > 36 in SPLIT
    with pytest.raises(ValueError, match="Invalid roulette number"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[10, 50], amount=10)
        )


def test_roulette_engine_invalid_bet_structures() -> None:
    """Validate bet type constraints, amounts, and length requirements."""
    # Amount <= 0
    with pytest.raises(ValueError, match="Bet amount must be a positive integer"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.RED, amount=0)
        )
    with pytest.raises(ValueError, match="Bet amount must be a positive integer"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.RED, amount=-10)
        )

    # STRAIGHT_UP without exactly 1 number
    with pytest.raises(ValueError, match="STRAIGHT_UP bet requires exactly 1 number"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[], amount=10)
        )
    with pytest.raises(ValueError, match="STRAIGHT_UP bet requires exactly 1 number"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[1, 2], amount=10)
        )

    # SPLIT without exactly 2 distinct numbers
    with pytest.raises(ValueError, match="SPLIT bet requires exactly 2 distinct numbers"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[1], amount=10)
        )
    with pytest.raises(ValueError, match="SPLIT bet requires exactly 2 distinct numbers"):
        RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[5, 5], amount=10)
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.SPLIT, numbers=[5, 5], amount=10)
        )

    # Outside bets with numbers should fail
    with pytest.raises(ValueError, match="RED bet does not accept numbers"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.RED, numbers=[7], amount=10)
        )
    with pytest.raises(ValueError, match="BLACK bet does not accept numbers"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.BLACK, numbers=[8], amount=10)
        )
    with pytest.raises(ValueError, match="EVEN bet does not accept numbers"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.EVEN, numbers=[2], amount=10)
        )

    # COLUMN with invalid index
    with pytest.raises(ValueError, match="COLUMN bet index must be 1, 2, or 3"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.COLUMN, numbers=[4], amount=10)
        )

    # DOZEN with invalid index
    with pytest.raises(ValueError, match="DOZEN bet index must be 1, 2, or 3"):
        RouletteEngine.validate_bet(
            RouletteBet(bet_type=RouletteBetType.DOZEN, numbers=[0], amount=10)
        )

    # Empty bets in spin
    with pytest.raises(ValueError, match="At least one bet is required"):
        RouletteEngine.spin(DeterministicRNGProvider([0]), [])


def test_roulette_engine_instance_execution() -> None:
    """Test engine instance method execution alongside classmethod."""
    engine = RouletteEngine()
    rng = DeterministicRNGProvider([32])  # 32 is Red
    bets = [RouletteBet(bet_type=RouletteBetType.RED, amount=50)]
    outcome = engine.spin(rng, bets)
    assert outcome.winning_number == 32
    assert outcome.color == "RED"
    assert outcome.total_payout == 100
