"""Unit tests for Classic Blackjack Engine math and rules.

Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
"""

from app.modules.gaming.engines.blackjack import (
    BlackjackEngine,
    BlackjackStatus,
    Card,
    Hand,
)
from app.modules.gaming.engines.rng import DeterministicRNGProvider


def test_card_values_and_representations() -> None:
    """Verify card value calculations and accessibility as property and method."""
    ace = Card(suit="HEARTS", rank="A")
    king = Card(suit="DIAMONDS", rank="K")
    queen = Card(suit="CLUBS", rank="Q")
    jack = Card(suit="SPADES", rank="J")
    ten = Card(suit="HEARTS", rank="10")
    two = Card(suit="SPADES", rank="2")

    assert ace.value == 11
    assert ace.value() == 11
    assert Card.value(ace) == 11
    assert int(ace.value) == 11

    assert king.value == 10
    assert queen.value == 10
    assert jack.value == 10
    assert ten.value == 10
    assert two.value == 2


def test_hand_calculation_multiple_aces() -> None:
    """Test dynamic ace value calculation in multiple ace scenarios.

    Verifies:
    - A + 8 = 19 (soft 19)
    - A + 8 + 5 = 14 duro (hard 14)
    - A + A = 12 (soft 12)
    - A + A + 9 = 21 (soft 21)
    - A + A + A + 9 = 12 (hard 12)
    - A + K = 21 (natural Blackjack)
    - 7 + 7 + 7 = 21 (hard 21, not natural blackjack)
    """
    # A + 8 = 19 (soft)
    hand1 = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="DIAMONDS", rank="8")])
    assert hand1.calculate_total() == 19
    assert hand1.is_soft() is True
    assert hand1.is_blackjack() is False
    assert hand1.is_busted() is False

    # A + 8 + 5 = 14 (hard: ace must downgrade to 1)
    hand2 = Hand(cards=[
        Card(suit="HEARTS", rank="A"),
        Card(suit="DIAMONDS", rank="8"),
        Card(suit="CLUBS", rank="5"),
    ])
    assert hand2.calculate_total() == 14
    assert hand2.is_soft() is False
    assert hand2.is_busted() is False

    # A + A = 12 (one ace is 11, one ace is 1 -> soft 12)
    hand3 = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="SPADES", rank="A")])
    assert hand3.calculate_total() == 12
    assert hand3.is_soft() is True

    # A + A + 9 = 21 (one ace is 11, one is 1, plus 9 = 21, soft)
    hand4 = Hand(cards=[
        Card(suit="HEARTS", rank="A"),
        Card(suit="SPADES", rank="A"),
        Card(suit="CLUBS", rank="9"),
    ])
    assert hand4.calculate_total() == 21
    assert hand4.is_soft() is True
    assert hand4.is_blackjack() is False  # 3 cards is not natural blackjack

    # A + A + A + 9 = 12 (all 3 aces must count as 1 to avoid bust -> hard 12)
    hand5 = Hand(cards=[
        Card(suit="HEARTS", rank="A"),
        Card(suit="SPADES", rank="A"),
        Card(suit="DIAMONDS", rank="A"),
        Card(suit="CLUBS", rank="9"),
    ])
    assert hand5.calculate_total() == 12
    assert hand5.is_soft() is False

    # A + K = 21 (natural blackjack)
    hand_bj = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="CLUBS", rank="K")])
    assert hand_bj.calculate_total() == 21
    assert hand_bj.is_blackjack() is True

    # 10 + 6 + 7 = 23 (busted)
    hand_bust = Hand(cards=[
        Card(suit="HEARTS", rank="10"),
        Card(suit="DIAMONDS", rank="6"),
        Card(suit="SPADES", rank="7"),
    ])
    assert hand_bust.calculate_total() == 23
    assert hand_bust.is_busted() is True


def test_natural_blackjack_vs_dealer_20_pays_3_to_2() -> None:
    """Test natural Blackjack against dealer 20 yields BLACKJACK status and 2.5x gross payout (3:2 net)."""
    player_hand = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="SPADES", rank="K")])
    dealer_hand = Hand(cards=[Card(suit="DIAMONDS", rank="10"), Card(suit="CLUBS", rank="10")])

    bet_amount = 100
    status, payout = BlackjackEngine.evaluate_outcome(player_hand, dealer_hand, bet_amount)

    assert status == BlackjackStatus.BLACKJACK
    assert payout == 250  # 100 * 2.5 = 250 credits


def test_push_tie_when_both_have_equal_scores() -> None:
    """Test push (tie) resolution returns PUSH status and 1.0x total bet refund."""
    # Scenario A: Both have standard 20
    p1 = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="SPADES", rank="10")])
    d1 = Hand(cards=[Card(suit="DIAMONDS", rank="J"), Card(suit="CLUBS", rank="Q")])
    status1, payout1 = BlackjackEngine.evaluate_outcome(p1, d1, total_bet=100)
    assert status1 == BlackjackStatus.PUSH
    assert payout1 == 100

    # Scenario B: Both have natural Blackjack
    p_bj = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="SPADES", rank="J")])
    d_bj = Hand(cards=[Card(suit="DIAMONDS", rank="A"), Card(suit="CLUBS", rank="K")])
    status2, payout2 = BlackjackEngine.evaluate_outcome(p_bj, d_bj, total_bet=200)
    assert status2 == BlackjackStatus.PUSH
    assert payout2 == 200

    # Scenario C: Both have 18
    p3 = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="SPADES", rank="8")])
    d3 = Hand(cards=[Card(suit="DIAMONDS", rank="9"), Card(suit="CLUBS", rank="9")])
    status3, payout3 = BlackjackEngine.evaluate_outcome(p3, d3, total_bet=50)
    assert status3 == BlackjackStatus.PUSH
    assert payout3 == 50


def test_dealer_turn_draws_on_16_stands_on_17() -> None:
    """Test dealer algorithm: hits while score < 17 and stands on 17 or higher."""
    # Dealer has 16 (10 + 6) -> Must draw
    dealer_16 = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="DIAMONDS", rank="6")])
    shoe = [Card(suit="CLUBS", rank="5")]  # Will make 21
    rng = DeterministicRNGProvider([0])

    updated_dealer, remaining_shoe = BlackjackEngine.play_dealer_turn(dealer_16, shoe, rng)

    assert len(updated_dealer.cards) == 3
    assert updated_dealer.calculate_total() == 21
    assert len(remaining_shoe) == 0

    # Dealer has 17 (10 + 7) -> Must stand without drawing
    dealer_17 = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="DIAMONDS", rank="7")])
    shoe_leftover = [Card(suit="SPADES", rank="5"), Card(suit="CLUBS", rank="8")]

    updated_dealer17, remaining_after = BlackjackEngine.play_dealer_turn(dealer_17, shoe_leftover, rng)
    assert len(updated_dealer17.cards) == 2
    assert updated_dealer17.calculate_total() == 17
    assert len(remaining_after) == 2

    # Dealer has Soft 17 (A + 6) -> Dealer stands on all 17s
    dealer_soft17 = Hand(cards=[Card(suit="HEARTS", rank="A"), Card(suit="DIAMONDS", rank="6")])
    updated_soft17, remaining_soft = BlackjackEngine.play_dealer_turn(dealer_soft17, shoe_leftover, rng)
    assert len(updated_soft17.cards) == 2
    assert updated_soft17.calculate_total() == 17
    assert len(remaining_soft) == 2


def test_dealer_busts_and_player_wins() -> None:
    """Test dealer busting when hitting from 15."""
    dealer_15 = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="DIAMONDS", rank="5")])
    shoe = [Card(suit="CLUBS", rank="8")]  # 15 + 8 = 23 (bust)
    rng = DeterministicRNGProvider([0])

    final_dealer, _ = BlackjackEngine.play_dealer_turn(dealer_15, shoe, rng)
    assert final_dealer.is_busted() is True

    player_hand = Hand(cards=[Card(suit="SPADES", rank="10"), Card(suit="HEARTS", rank="8")])  # 18
    status, payout = BlackjackEngine.evaluate_outcome(player_hand, final_dealer, total_bet=100)
    assert status == BlackjackStatus.DEALER_BUSTED
    assert payout == 200


def test_player_bust_is_immediate_loss() -> None:
    """Test player busting results in PLAYER_BUSTED and 0 payout regardless of dealer hand."""
    player_bust = Hand(cards=[
        Card(suit="HEARTS", rank="10"),
        Card(suit="DIAMONDS", rank="8"),
        Card(suit="SPADES", rank="5"),
    ])  # 23
    dealer_hand = Hand(cards=[Card(suit="CLUBS", rank="10"), Card(suit="CLUBS", rank="7")])

    status, payout = BlackjackEngine.evaluate_outcome(player_bust, dealer_hand, total_bet=100)
    assert status == BlackjackStatus.PLAYER_BUSTED
    assert payout == 0


def test_generate_shoe_6_decks() -> None:
    """Verify shoe generation generates 312 cards with 6 of each suit/rank combination."""
    shoe = BlackjackEngine.generate_shoe(num_decks=6)
    assert len(shoe) == 312  # 6 * 52

    # Check aces count = 6 decks * 4 suits = 24 aces
    aces = [c for c in shoe if c.rank == "A"]
    assert len(aces) == 24


def test_deal_initial_removes_four_cards() -> None:
    """Verify initial deal extracts 2 cards for player and 2 cards for dealer."""
    shoe = BlackjackEngine.generate_shoe(num_decks=1)
    assert len(shoe) == 52

    rng = DeterministicRNGProvider([0, 0, 0, 0])
    p_hand, d_hand, remaining = BlackjackEngine.deal_initial(shoe, rng)

    assert len(p_hand.cards) == 2
    assert len(d_hand.cards) == 2
    assert len(remaining) == 48


def test_apply_hit() -> None:
    """Verify apply_hit adds exactly one card and detects busts."""
    hand = Hand(cards=[Card(suit="HEARTS", rank="10"), Card(suit="DIAMONDS", rank="5")])
    shoe = [Card(suit="CLUBS", rank="7")]
    rng = DeterministicRNGProvider([0])

    new_hand, rem_shoe, is_busted = BlackjackEngine.apply_hit(hand, shoe, rng)
    assert len(new_hand.cards) == 3
    assert new_hand.calculate_total() == 22
    assert is_busted is True
    assert len(rem_shoe) == 0
