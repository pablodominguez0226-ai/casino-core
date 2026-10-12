"""Gaming API router.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import uuid

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User
from app.modules.gaming.schemas import (
    BlackjackActionRequest,
    BlackjackDealRequest,
    BlackjackGameStateResponse,
    GameRoundResponse,
    GameResponse,
    GameSessionCreateRequest,
    GameSessionResponse,
    RouletteSpinRequest,
    RouletteSpinResponse,
    SpinRequest,
    SpinResponse,
)
from app.modules.gaming.services import GamingService

router = APIRouter(prefix="/games", tags=["games"])


@router.get(
    "/",
    response_model=list[GameResponse],
    summary="List active games for operator",
)
@router.get(
    "",
    response_model=list[GameResponse],
    include_in_schema=False,
)
async def list_games(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[GameResponse]:
    """Retrieve catalog of active games available under the user's operator."""
    games = await GamingService.list_active_games(
        db=db,
        operator_id=current_user.operator_id,
    )
    return [GameResponse.model_validate(g) for g in games]


@router.post(
    "/sessions",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new game session",
)
async def create_session(
    data: GameSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GameSessionResponse:
    """Initialize and persist a new active gameplay session."""
    session = await GamingService.start_session(
        db=db,
        user_id=current_user.id,
        game_id=data.game_id,
    )
    return GameSessionResponse.model_validate(session)


@router.post(
    "/sessions/{session_id}/spin",
    response_model=SpinResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute slot spin round",
)
async def spin(
    session_id: uuid.UUID,
    data: SpinRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SpinResponse:
    """Execute a slot machine spin atomically with wallet balance debit and potential payout."""
    return await GamingService.execute_spin(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        bet_amount=data.bet_amount,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/sessions/{session_id}/roulette/spin",
    response_model=RouletteSpinResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute European roulette spin round",
)
async def roulette_spin(
    session_id: uuid.UUID,
    data: RouletteSpinRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RouletteSpinResponse:
    """Execute a European roulette spin with composite bets and atomic ledger settlement."""
    return await GamingService.execute_roulette_spin(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        bets=data.bets,
        idempotency_key=idempotency_key,
    )



@router.post(
    "/sessions/{session_id}/end",
    response_model=GameSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="End an active game session",
)
async def end_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GameSessionResponse:
    """Terminate an active game session and mark its lifecycle as completed."""
    session = await GamingService.end_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    return GameSessionResponse.model_validate(session)


@router.get(
    "/sessions/{session_id}/rounds",
    response_model=list[GameRoundResponse],
    summary="Get paginated session rounds history",
)
async def get_session_rounds(
    session_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[GameRoundResponse]:
    """Retrieve round history recorded for the authenticated user's game session."""
    rounds = await GamingService.get_session_rounds(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return [GameRoundResponse.model_validate(r) for r in rounds]


@router.post(
    "/sessions/{session_id}/blackjack/deal",
    response_model=BlackjackGameStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a new Blackjack round",
)
async def blackjack_deal(
    session_id: uuid.UUID,
    data: BlackjackDealRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BlackjackGameStateResponse:
    """Deal initial hands for a Blackjack round and settle natural blackjacks."""
    return await GamingService.start_blackjack_round(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        bet_amount=data.bet_amount,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/rounds/{round_id}/blackjack/action",
    response_model=BlackjackGameStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Blackjack player action",
)
async def blackjack_action(
    round_id: uuid.UUID,
    data: BlackjackActionRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BlackjackGameStateResponse:
    """Execute HIT, STAND, or DOUBLE_DOWN action on an active Blackjack round."""
    return await GamingService.process_blackjack_action(
        db=db,
        user_id=current_user.id,
        round_id=round_id,
        action=data.action,
        idempotency_key=idempotency_key,
    )


# Standalone router mounted at /api/v1 so /api/v1/rounds/{round_id}/blackjack/action is reachable
rounds_router = APIRouter(tags=["games"])


@rounds_router.post(
    "/rounds/{round_id}/blackjack/action",
    response_model=BlackjackGameStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Blackjack player action (direct route)",
    include_in_schema=False,
)
async def blackjack_action_direct(
    round_id: uuid.UUID,
    data: BlackjackActionRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BlackjackGameStateResponse:
    """Direct alias endpoint for Blackjack action."""
    return await blackjack_action(
        round_id=round_id,
        data=data,
        idempotency_key=idempotency_key,
        current_user=current_user,
        db=db,
    )
