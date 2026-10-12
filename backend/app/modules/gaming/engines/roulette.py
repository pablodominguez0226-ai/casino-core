"""European Roulette Simulator Engine (Single Zero, pockets 0 to 36).

Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
"""
from dataclasses import dataclass, field

from app.modules.gaming.engines.rng import IRNGProvider
from app.modules.gaming.enums import RouletteBetType

RED_NUMBERS: set[int] = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS: set[int] = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

COLUMN_1: set[int] = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}
COLUMN_2: set[int] = {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}
COLUMN_3: set[int] = {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}

DOZEN_1: set[int] = set(range(1, 13))
DOZEN_2: set[int] = set(range(13, 25))
DOZEN_3: set[int] = set(range(25, 37))

ROULETTE_DISCLAIMER: str = (
    "Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales."
)


@dataclass
class RouletteBet:
    """Roulette bet representation.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    bet_type: RouletteBetType
    numbers: list[int] = field(default_factory=list)
    amount: int = 0

    def __init__(
        self,
        bet_type: RouletteBetType,
        numbers: list[int] | None = None,
        amount: int = 0,
    ) -> None:
        self.bet_type = bet_type
        self.numbers = list(numbers) if numbers is not None else []
        self.amount = amount


@dataclass
class BetResolution:
    """Outcome resolution for an individual roulette bet.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    bet: RouletteBet
    won: bool
    payout_amount: int


@dataclass
class RouletteOutcome:
    """Outcome of a European roulette spin with composite bet resolutions.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    winning_number: int
    color: str
    is_even: bool | None
    total_bet: int
    total_payout: int
    resolutions: list[BetResolution]


class RouletteEngine:
    """European Roulette Engine with standard single-zero rules.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    RED_NUMBERS = RED_NUMBERS
    BLACK_NUMBERS = BLACK_NUMBERS
    COLUMN_1 = COLUMN_1
    COLUMN_2 = COLUMN_2
    COLUMN_3 = COLUMN_3
    DOZEN_1 = DOZEN_1
    DOZEN_2 = DOZEN_2
    DOZEN_3 = DOZEN_3

    # Gross payout multipliers: (e.g. STRAIGHT_UP pays 35 to 1 + bet return = 36x gross)
    PAYOUT_MULTIPLIERS: dict[RouletteBetType, int] = {
        RouletteBetType.STRAIGHT_UP: 36,
        RouletteBetType.SPLIT: 18,
        RouletteBetType.STREET: 12,
        RouletteBetType.CORNER: 9,
        RouletteBetType.SIX_LINE: 6,
        RouletteBetType.COLUMN: 3,
        RouletteBetType.DOZEN: 3,
        RouletteBetType.RED: 2,
        RouletteBetType.BLACK: 2,
        RouletteBetType.EVEN: 2,
        RouletteBetType.ODD: 2,
        RouletteBetType.LOW: 2,
        RouletteBetType.HIGH: 2,
    }

    @classmethod
    def validate_bet(cls, bet: RouletteBet) -> None:
        """Validate bet integrity, numbers boundaries, and correctness according to bet type.

        Args:
            bet: RouletteBet instance to validate.

        Raises:
            ValueError: If numbers or bet properties do not conform to European roulette rules.
        """
        if not isinstance(bet.amount, int) or bet.amount <= 0:
            raise ValueError(f"Bet amount must be a positive integer, got {bet.amount}")

        # Check all provided numbers are in range [0, 36]
        for n in bet.numbers:
            if not isinstance(n, int) or n < 0 or n > 36:
                raise ValueError(f"Invalid roulette number: {n}. Must be between 0 and 36.")

        bt = bet.bet_type
        if bt == RouletteBetType.STRAIGHT_UP:
            if len(bet.numbers) != 1:
                raise ValueError("STRAIGHT_UP bet requires exactly 1 number (0-36).")
        elif bt == RouletteBetType.SPLIT:
            if len(bet.numbers) != 2 or len(set(bet.numbers)) != 2:
                raise ValueError("SPLIT bet requires exactly 2 distinct numbers (0-36).")
        elif bt == RouletteBetType.STREET:
            if len(bet.numbers) != 3 or len(set(bet.numbers)) != 3:
                raise ValueError("STREET bet requires exactly 3 distinct numbers (0-36).")
        elif bt == RouletteBetType.CORNER:
            if len(bet.numbers) != 4 or len(set(bet.numbers)) != 4:
                raise ValueError("CORNER bet requires exactly 4 distinct numbers (0-36).")
        elif bt == RouletteBetType.SIX_LINE:
            if len(bet.numbers) != 6 or len(set(bet.numbers)) != 6:
                raise ValueError("SIX_LINE bet requires exactly 6 distinct numbers (0-36).")
        elif bt == RouletteBetType.COLUMN:
            if len(bet.numbers) == 1:
                if bet.numbers[0] not in (1, 2, 3):
                    raise ValueError("COLUMN bet index must be 1, 2, or 3.")
            elif len(bet.numbers) == 12:
                if len(set(bet.numbers)) != 12 or any(n == 0 for n in bet.numbers):
                    raise ValueError("COLUMN bet requires 12 distinct numbers between 1 and 36.")
                if set(bet.numbers) not in (cls.COLUMN_1, cls.COLUMN_2, cls.COLUMN_3):
                    raise ValueError("COLUMN bet numbers must match column 1, 2, or 3.")
            else:
                raise ValueError("COLUMN bet requires column index [1, 2, or 3] or exactly 12 column numbers.")
        elif bt == RouletteBetType.DOZEN:
            if len(bet.numbers) == 1:
                if bet.numbers[0] not in (1, 2, 3):
                    raise ValueError("DOZEN bet index must be 1, 2, or 3.")
            elif len(bet.numbers) == 12:
                if len(set(bet.numbers)) != 12 or any(n == 0 for n in bet.numbers):
                    raise ValueError("DOZEN bet requires 12 distinct numbers between 1 and 36.")
                if set(bet.numbers) not in (cls.DOZEN_1, cls.DOZEN_2, cls.DOZEN_3):
                    raise ValueError("DOZEN bet numbers must match dozen 1, 2, or 3.")
            else:
                raise ValueError("DOZEN bet requires dozen index [1, 2, or 3] or exactly 12 dozen numbers.")
        elif bt in (
            RouletteBetType.RED,
            RouletteBetType.BLACK,
            RouletteBetType.EVEN,
            RouletteBetType.ODD,
            RouletteBetType.LOW,
            RouletteBetType.HIGH,
        ):
            if len(bet.numbers) > 0:
                raise ValueError(f"{bt.value} bet does not accept numbers; expected empty list.")
        else:
            raise ValueError(f"Unknown bet type: {bt}")

    @classmethod
    def evaluate_bet(cls, winning_number: int, bet: RouletteBet) -> tuple[bool, int]:
        """Evaluate a single bet against the winning roulette number.

        Args:
            winning_number: Outcome number between 0 and 36.
            bet: RouletteBet instance.

        Returns:
            Tuple of (won, payout_amount).
        """
        multiplier = cls.PAYOUT_MULTIPLIERS[bet.bet_type]
        bt = bet.bet_type

        # Case 0: Green. All outside bets lose. Only inside bets containing 0 can win.
        if winning_number == 0:
            if bt == RouletteBetType.STRAIGHT_UP and bet.numbers[0] == 0:
                return True, bet.amount * multiplier
            if bt in (
                RouletteBetType.SPLIT,
                RouletteBetType.STREET,
                RouletteBetType.CORNER,
                RouletteBetType.SIX_LINE,
            ) and 0 in bet.numbers:
                return True, bet.amount * multiplier
            return False, 0

        won = False
        if bt == RouletteBetType.STRAIGHT_UP:
            won = (winning_number == bet.numbers[0])
        elif bt in (
            RouletteBetType.SPLIT,
            RouletteBetType.STREET,
            RouletteBetType.CORNER,
            RouletteBetType.SIX_LINE,
        ):
            won = (winning_number in bet.numbers)
        elif bt == RouletteBetType.COLUMN:
            if len(bet.numbers) == 1:
                idx = bet.numbers[0]
                if idx == 1:
                    won = (winning_number in cls.COLUMN_1)
                elif idx == 2:
                    won = (winning_number in cls.COLUMN_2)
                elif idx == 3:
                    won = (winning_number in cls.COLUMN_3)
            else:
                won = (winning_number in bet.numbers)
        elif bt == RouletteBetType.DOZEN:
            if len(bet.numbers) == 1:
                idx = bet.numbers[0]
                if idx == 1:
                    won = (winning_number in cls.DOZEN_1)
                elif idx == 2:
                    won = (winning_number in cls.DOZEN_2)
                elif idx == 3:
                    won = (winning_number in cls.DOZEN_3)
            else:
                won = (winning_number in bet.numbers)
        elif bt == RouletteBetType.RED:
            won = (winning_number in cls.RED_NUMBERS)
        elif bt == RouletteBetType.BLACK:
            won = (winning_number in cls.BLACK_NUMBERS)
        elif bt == RouletteBetType.EVEN:
            won = (winning_number % 2 == 0)
        elif bt == RouletteBetType.ODD:
            won = (winning_number % 2 == 1)
        elif bt == RouletteBetType.LOW:
            won = (1 <= winning_number <= 18)
        elif bt == RouletteBetType.HIGH:
            won = (19 <= winning_number <= 36)

        payout = (bet.amount * multiplier) if won else 0
        return won, payout

    @classmethod
    def spin(cls, rng: IRNGProvider, bets: list[RouletteBet]) -> RouletteOutcome:
        """Simulate a roulette wheel spin and settle all provided bets.

        Args:
            rng: Random number provider yielding 0 to 36 inclusive.
            bets: List of bets to evaluate.

        Returns:
            RouletteOutcome with winning number, color, is_even, and all bet resolutions.
        """
        if not bets:
            raise ValueError("At least one bet is required")

        winning_number = rng.generate_int(0, 36)
        if winning_number == 0:
            color = "GREEN"
            is_even = None
        elif winning_number in cls.RED_NUMBERS:
            color = "RED"
            is_even = (winning_number % 2 == 0)
        else:
            color = "BLACK"
            is_even = (winning_number % 2 == 0)

        total_bet = 0
        total_payout = 0
        resolutions: list[BetResolution] = []

        for bet in bets:
            cls.validate_bet(bet)
            won, payout_amount = cls.evaluate_bet(winning_number, bet)
            resolutions.append(BetResolution(bet=bet, won=won, payout_amount=payout_amount))
            total_bet += bet.amount
            total_payout += payout_amount

        return RouletteOutcome(
            winning_number=winning_number,
            color=color,
            is_even=is_even,
            total_bet=total_bet,
            total_payout=total_payout,
            resolutions=resolutions,
        )
