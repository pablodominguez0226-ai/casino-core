"""Classic Blackjack Multi-Turn Engine (6-Deck Shoe, Dealer stands on all 17s).

Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.modules.gaming.engines.rng import IRNGProvider, StandardRNGProvider

BLACKJACK_DISCLAIMER: str = (
    "Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real."
)


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


class _CardValue(int):
    """Integer that can also be invoked as a nullary callable for API ergonomics."""

    def __call__(self) -> int:
        return int(self)


class _CardValueDescriptor:
    """Descriptor enabling card.value access both as attribute and as card.value()."""

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        if instance is None:
            return lambda obj: obj._compute_value()
        return _CardValue(instance._compute_value())


@dataclass(frozen=True)
class Card:
    """Card representation in the Blackjack shoe.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    suit: str
    rank: str

    def _compute_value(self) -> int:
        if self.rank in ("J", "Q", "K"):
            return 10
        if self.rank == "A":
            return 11
        return int(self.rank)

    value = _CardValueDescriptor()


@dataclass
class Hand:
    """Hand representation tracking cards, dynamic totals, and special states.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    cards: list[Card] = field(default_factory=list)

    def calculate_total(self) -> int:
        """Compute hand total score with dynamic Ace valuation (11 unless busting, then 1)."""
        total = 0
        aces = 0
        for card in self.cards:
            if card.rank == "A":
                aces += 1
                total += 11
            elif card.rank in ("J", "Q", "K"):
                total += 10
            else:
                total += int(card.rank)

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def is_soft(self) -> bool:
        """Return True if an Ace is currently counted as 11 without exceeding 21."""
        base_total = 0
        has_ace = False
        for card in self.cards:
            if card.rank == "A":
                has_ace = True
                base_total += 1
            elif card.rank in ("J", "Q", "K"):
                base_total += 10
            else:
                base_total += int(card.rank)

        return has_ace and (base_total + 10 <= 21)

    def is_blackjack(self) -> bool:
        """Natural Blackjack: exactly 2 initial cards totaling 21."""
        return len(self.cards) == 2 and self.calculate_total() == 21

    def is_busted(self) -> bool:
        """Return True if the hand score strictly exceeds 21."""
        return self.calculate_total() > 21


class BlackjackEngine:
    """Classic Blackjack engine managing shoe generation, dealing, dealer logic, and settlements.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    SUITS: list[str] = ["HEARTS", "DIAMONDS", "CLUBS", "SPADES"]
    RANKS: list[str] = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

    @classmethod
    def generate_shoe(cls, num_decks: int = 6) -> list[Card]:
        """Generate a standard shoe containing num_decks complete 52-card decks."""
        shoe: list[Card] = []
        for _ in range(num_decks):
            for suit in cls.SUITS:
                for rank in cls.RANKS:
                    shoe.append(Card(suit=suit, rank=rank))
        return shoe

    @classmethod
    def _draw_card(
        cls,
        shoe: list[Card],
        rng: IRNGProvider | None = None,
    ) -> tuple[Card, list[Card]]:
        """Draw a card pseudo-randomly from shoe using IRNGProvider, returning drawn card and remaining shoe."""
        if not shoe:
            raise ValueError("Shoe is empty")
        rng_provider = rng or StandardRNGProvider()
        idx = rng_provider.generate_int(0, len(shoe) - 1)
        remaining = list(shoe)
        card = remaining.pop(idx)
        return card, remaining

    @classmethod
    def deal_initial(
        cls,
        shoe: list[Card],
        rng: IRNGProvider | None = None,
    ) -> tuple[Hand, Hand, list[Card]]:
        """Deal 2 cards to player and 2 cards to dealer (face-up and hole card).

        Returns:
            tuple[Hand, Hand, list[Card]]: (player_hand, dealer_hand, remaining_shoe).
        """
        if len(shoe) < 4:
            raise ValueError("Insufficient cards in shoe to deal initial hands")

        rng_provider = rng or StandardRNGProvider()
        remaining = list(shoe)

        player_c1, remaining = cls._draw_card(remaining, rng_provider)
        dealer_c1, remaining = cls._draw_card(remaining, rng_provider)
        player_c2, remaining = cls._draw_card(remaining, rng_provider)
        dealer_c2, remaining = cls._draw_card(remaining, rng_provider)

        player_hand = Hand([player_c1, player_c2])
        dealer_hand = Hand([dealer_c1, dealer_c2])

        return player_hand, dealer_hand, remaining

    @classmethod
    def apply_hit(
        cls,
        hand: Hand,
        shoe: list[Card],
        rng: IRNGProvider | None = None,
    ) -> tuple[Hand, list[Card], bool]:
        """Add one card from shoe to hand and evaluate whether the hand busted.

        Returns:
            tuple[Hand, list[Card], bool]: (updated_hand, remaining_shoe, is_busted).
        """
        card, remaining = cls._draw_card(shoe, rng)
        updated_hand = Hand([*hand.cards, card])
        return updated_hand, remaining, updated_hand.is_busted()

    @classmethod
    def play_dealer_turn(
        cls,
        dealer_hand: Hand,
        shoe: list[Card],
        rng: IRNGProvider | None = None,
    ) -> tuple[Hand, list[Card]]:
        """Execute dealer deterministic rule: dealer hits while score < 17 and stands on all 17s."""
        current_hand = Hand(list(dealer_hand.cards))
        remaining = list(shoe)
        rng_provider = rng or StandardRNGProvider()

        while current_hand.calculate_total() < 17:
            card, remaining = cls._draw_card(remaining, rng_provider)
            current_hand.cards.append(card)

        return current_hand, remaining

    @classmethod
    def evaluate_outcome(
        cls,
        player_hand: Hand,
        dealer_hand: Hand,
        total_bet: int,
    ) -> tuple[BlackjackStatus, int]:
        """Evaluate terminal round outcome and gross payout in virtual credits.

        Payout rules:
        - Player busted: PLAYER_BUSTED, 0 credits.
        - Natural Blackjack (vs non-BJ): BLACKJACK, 2.5x total_bet (3 to 2 net payout).
        - Natural Blackjack (vs BJ): PUSH, 1.0x total_bet.
        - Dealer natural BJ (vs non-BJ 21): DEALER_WON, 0 credits.
        - Dealer busted: DEALER_BUSTED, 2.0x total_bet.
        - Player score > dealer score: PLAYER_WON, 2.0x total_bet.
        - Player score < dealer score: DEALER_WON, 0 credits.
        - Equal scores: PUSH, 1.0x total_bet.
        """
        if player_hand.is_busted():
            return BlackjackStatus.PLAYER_BUSTED, 0

        if player_hand.is_blackjack():
            if dealer_hand.is_blackjack():
                return BlackjackStatus.PUSH, int(total_bet * 1.0)
            return BlackjackStatus.BLACKJACK, int(total_bet * 2.5)

        if dealer_hand.is_blackjack():
            return BlackjackStatus.DEALER_WON, 0

        if dealer_hand.is_busted():
            return BlackjackStatus.DEALER_BUSTED, int(total_bet * 2.0)

        player_score = player_hand.calculate_total()
        dealer_score = dealer_hand.calculate_total()

        if player_score > dealer_score:
            return BlackjackStatus.PLAYER_WON, int(total_bet * 2.0)
        elif player_score < dealer_score:
            return BlackjackStatus.DEALER_WON, 0
        else:
            return BlackjackStatus.PUSH, int(total_bet * 1.0)
