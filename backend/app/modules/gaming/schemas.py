"""Gaming Pydantic schemas.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.gaming.enums import (
    BlackjackAction,
    BlackjackStatus,
    GameSessionStatus,
    GameType,
    RouletteBetType,
)
from app.modules.gaming.engines.blackjack import BLACKJACK_DISCLAIMER


class GameResponse(BaseModel):
    """Schema representing game entity details.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    id: uuid.UUID
    code: str
    name: str
    game_type: GameType
    min_bet: int
    max_bet: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class GameSessionCreateRequest(BaseModel):
    """Schema requesting game session creation.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    game_id: uuid.UUID


class GameSessionResponse(BaseModel):
    """Schema representing game session response.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    id: uuid.UUID
    game_id: uuid.UUID
    user_id: uuid.UUID
    status: GameSessionStatus
    started_at: datetime
    ended_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SpinRequest(BaseModel):
    """Schema requesting slot spin execution.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    bet_amount: int = Field(gt=0, description="Bet amount in virtual CREDITS (Simulación educativa. RNG no apto ni certificado para juego con dinero real.)")


class SpinResponse(BaseModel):
    """Schema representing resolved slot spin outcome.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    round_id: uuid.UUID
    symbols: list[str]
    bet_amount: int
    payout_amount: int
    is_win: bool
    current_balance: int

    model_config = ConfigDict(from_attributes=True)


class GameRoundResponse(BaseModel):
    """Schema representing historical game round details.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    id: uuid.UUID
    session_id: uuid.UUID
    bet_amount: int
    payout_amount: int
    round_data: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouletteBetRequest(BaseModel):
    """Schema representing an individual roulette bet.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    bet_type: RouletteBetType
    numbers: list[int] = Field(default_factory=list, description="Target numbers for roulette bet")
    amount: int = Field(gt=0, description="Bet amount in virtual credits")


class RouletteSpinRequest(BaseModel):
    """Schema requesting European roulette spin execution with composite bets.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    bets: list[RouletteBetRequest] = Field(
        min_length=1,
        max_length=50,
        description="Composite list of bets to evaluate on the spin",
    )


class BetResolutionResponse(BaseModel):
    """Schema representing evaluation outcome for an individual roulette bet.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    bet_type: str
    numbers: list[int]
    amount: int
    won: bool
    payout: int

    model_config = ConfigDict(from_attributes=True)


class RouletteSpinResponse(BaseModel):
    """Schema representing European roulette spin outcome and ledger settlement.

    Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
    """

    round_id: uuid.UUID
    winning_number: int
    color: str
    total_bet: int
    total_payout: int
    current_balance: int
    resolutions: list[BetResolutionResponse]

    model_config = ConfigDict(from_attributes=True)


class BlackjackCardSchema(BaseModel):
    """Schema representing an individual playing card in Blackjack.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    suit: str
    rank: str
    value: int
    hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class BlackjackDealRequest(BaseModel):
    """Schema requesting initiation of a new Blackjack round.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    bet_amount: int = Field(gt=0, description="Bet amount in virtual credits")


class BlackjackActionRequest(BaseModel):
    """Schema requesting player action on an active Blackjack round.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    action: BlackjackAction


class BlackjackGameStateResponse(BaseModel):
    """Schema representing the current state and settlement of a Blackjack round.

    Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
    """

    round_id: uuid.UUID
    status: BlackjackStatus
    player_cards: list[BlackjackCardSchema]
    player_score: int
    dealer_cards: list[BlackjackCardSchema]
    dealer_score: int | None = None
    initial_bet: int
    total_bet: int
    payout_amount: int
    can_double: bool
    is_settled: bool
    current_balance: int
    disclaimer: str = BLACKJACK_DISCLAIMER

    model_config = ConfigDict(from_attributes=True)

