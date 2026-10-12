"""Gaming domain enumerations.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from enum import Enum


class GameType(str, Enum):
    """Supported casino game types."""

    SLOT = "SLOT"
    ROULETTE = "ROULETTE"
    BLACKJACK = "BLACKJACK"


class GameSessionStatus(str, Enum):
    """Lifecycle statuses for a game session."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SlotSymbol(str, Enum):
    """Available symbols on slot simulator reels."""

    CHERRY = "CHERRY"
    LEMON = "LEMON"
    ORANGE = "ORANGE"
    BELL = "BELL"
    SEVEN = "SEVEN"


class RouletteBetType(str, Enum):
    """European roulette bet types."""

    STRAIGHT_UP = "STRAIGHT_UP"
    SPLIT = "SPLIT"
    STREET = "STREET"
    CORNER = "CORNER"
    SIX_LINE = "SIX_LINE"
    COLUMN = "COLUMN"
    DOZEN = "DOZEN"
    RED = "RED"
    BLACK = "BLACK"
    EVEN = "EVEN"
    ODD = "ODD"
    LOW = "LOW"
    HIGH = "HIGH"


class BlackjackAction(str, Enum):
    """Available player decisions in Blackjack."""

    HIT = "HIT"
    STAND = "STAND"
    DOUBLE_DOWN = "DOUBLE_DOWN"


class BlackjackStatus(str, Enum):
    """Lifecycle statuses and terminal outcomes for a Blackjack round."""

    IN_PROGRESS = "IN_PROGRESS"
    PLAYER_BUSTED = "PLAYER_BUSTED"
    DEALER_BUSTED = "DEALER_BUSTED"
    PLAYER_WON = "PLAYER_WON"
    DEALER_WON = "DEALER_WON"
    PUSH = "PUSH"
    BLACKJACK = "BLACKJACK"
