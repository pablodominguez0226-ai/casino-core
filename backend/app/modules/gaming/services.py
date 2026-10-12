"""Gaming domain service.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utc_now
from app.modules.gaming.engines.blackjack import (
    BLACKJACK_DISCLAIMER,
    BlackjackAction,
    BlackjackEngine,
    BlackjackStatus,
    Card,
    Hand,
)
from app.modules.gaming.engines.rng import IRNGProvider, StandardRNGProvider
from app.modules.gaming.engines.roulette import (
    ROULETTE_DISCLAIMER,
    RouletteBet,
    RouletteEngine,
)
from app.modules.gaming.engines.slot import SlotEngine
from app.modules.gaming.enums import GameSessionStatus, GameType
from app.modules.gaming.exceptions import (
    GameNotFoundException,
    GameRoundAlreadySettledException,
    GameRoundNotFoundException,
    GameSessionInactiveException,
    GameSessionNotFoundException,
    GamingException,
    InvalidBetAmountException,
    InvalidBlackjackActionException,
    InvalidRouletteBetException,
)
from app.modules.gaming.models import Game, GameRound, GameSession
from app.modules.gaming.schemas import (
    BetResolutionResponse,
    BlackjackCardSchema,
    BlackjackGameStateResponse,
    RouletteBetRequest,
    RouletteSpinResponse,
    SpinResponse,
)
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import DuplicateTransactionException
from app.modules.wallet.models import IdempotencyRecord
from app.modules.wallet.services import WalletService
from app.modules.responsible.services import ResponsibleGamingService
from app.modules.responsible.exceptions import PlayerSelfExcludedException
from app.modules.identity.models import User
from app.modules.operators.models import OperatorGameConfig

logger = logging.getLogger(__name__)


class GamingService:
    """Domain service managing game sessions, execution of rounds, and atomic wallet ledger integration.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    @classmethod
    async def list_active_games(
        cls,
        db: AsyncSession,
        operator_id: uuid.UUID,
    ) -> list[Game]:
        """List active games configured for a specific operator."""
        stmt = (
            select(Game)
            .where(
                Game.operator_id == operator_id,
                Game.is_active.is_(True),
            )
            .order_by(Game.name.asc())
        )
        return list((await db.scalars(stmt)).all())

    @classmethod
    async def get_effective_game_limits(
        cls,
        db: AsyncSession,
        game_id: uuid.UUID,
        operator_id: uuid.UUID | None,
    ) -> tuple[Game, int, int, bool]:
        """Fetch game entity and determine effective min/max bet and activation status for operator.

        Returns:
            tuple: (game, min_bet, max_bet, is_enabled)
        """
        game = await db.get(Game, game_id)
        if not game or not game.is_active:
            raise GameNotFoundException(f"Game '{game_id}' not found or inactive")

        min_bet = game.min_bet
        max_bet = game.max_bet
        is_enabled = game.is_active

        if operator_id:
            stmt = select(OperatorGameConfig).where(
                OperatorGameConfig.operator_id == operator_id,
                OperatorGameConfig.game_id == game_id,
            )
            override = await db.scalar(stmt)
            if override:
                min_bet = override.min_bet
                max_bet = override.max_bet
                is_enabled = override.is_enabled and game.is_active
            elif game.operator_id != operator_id:
                raise GameNotFoundException(f"Game '{game_id}' not found or inactive")

        return game, min_bet, max_bet, is_enabled

    @classmethod
    async def start_session(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        game_id: uuid.UUID,
    ) -> GameSession:
        """Validate game existence and activate a new game session for the player."""
        exclusion = await ResponsibleGamingService.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Cannot open game sessions.",
                expires_at=exclusion.expires_at,
            )

        user = await db.get(User, user_id)
        operator_id = user.operator_id if user else None
        game, _, _, is_enabled = await cls.get_effective_game_limits(db, game_id, operator_id)
        if not is_enabled:
            raise GameNotFoundException(f"Game '{game_id}' not found or inactive")

        session = GameSession(
            user_id=user_id,
            game_id=game_id,
            status=GameSessionStatus.ACTIVE,
            started_at=utc_now(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    async def get_session(
        cls,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GameSession:
        """Retrieve a game session ensuring ownership verification."""
        stmt = select(GameSession).where(
            GameSession.id == session_id,
            GameSession.user_id == user_id,
        )
        session = await db.scalar(stmt)
        if not session:
            raise GameSessionNotFoundException(f"Game session '{session_id}' not found")
        return session

    @classmethod
    async def end_session(
        cls,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GameSession:
        """Mark an active game session as COMPLETED."""
        session = await cls.get_session(db, session_id, user_id)
        if session.status != GameSessionStatus.COMPLETED:
            session.status = GameSessionStatus.COMPLETED
            session.ended_at = utc_now()
            await db.commit()
            await db.refresh(session)
        return session

    @classmethod
    async def get_session_rounds(
        cls,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[GameRound]:
        """Retrieve paginated round history for a specific game session."""
        await cls.get_session(db, session_id, user_id)
        stmt = (
            select(GameRound)
            .where(GameRound.session_id == session_id)
            .order_by(GameRound.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list((await db.scalars(stmt)).all())

    @classmethod
    async def execute_spin(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        bet_amount: int,
        idempotency_key: str | None = None,
        rng: IRNGProvider | None = None,
    ) -> SpinResponse:
        """Execute a slot spin round atomically integrated with the wallet ledger.

        Atomic transaction pipeline:
        1. Validates session existence, ownership, and ACTIVE status.
        2. Validates bet boundaries against game limits.
        3. Locks player's wallet with FOR UPDATE and debits the bet (BET_SIMULATION).
        4. Invokes SlotEngine.spin() with RNG provider to resolve symbols and calculate payout.
        5. If payout > 0, credits winnings into wallet ledger (WIN_SIMULATION).
        6. Persists GameRound entity linked to session.
        7. Commits transaction or rolls back on any error.

        Simulación educativa. RNG no apto ni certificado para juego con dinero real.
        """
        # 0. Enforce self-exclusion invariant: player cannot execute spin if self-excluded
        exclusion = await ResponsibleGamingService.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Gameplay prohibited.",
                expires_at=exclusion.expires_at,
            )

        # 1. Idempotency pre-check
        if idempotency_key:
            stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
            existing_rec = await db.scalar(stmt_rec)
            if existing_rec:
                payload = existing_rec.response_payload
                if (
                    payload.get("session_id") != str(session_id)
                    or payload.get("bet_amount") != bet_amount
                ):
                    raise DuplicateTransactionException(
                        f"Idempotency key '{idempotency_key}' was already processed with different parameters"
                    )
                return SpinResponse(
                    round_id=uuid.UUID(payload["round_id"]),
                    symbols=payload["symbols"],
                    bet_amount=payload["bet_amount"],
                    payout_amount=payload["payout_amount"],
                    is_win=payload["is_win"],
                    current_balance=payload["current_balance"],
                )

        # 2. Validate session exists, belongs to user, and is ACTIVE
        stmt_session = select(GameSession).where(GameSession.id == session_id)
        session = await db.scalar(stmt_session)
        if not session or session.user_id != user_id:
            raise GameSessionNotFoundException(f"Game session '{session_id}' not found")

        if session.status != GameSessionStatus.ACTIVE:
            raise GameSessionInactiveException(f"Game session '{session_id}' is not active")

        # 3. Validate game exists and bet_amount is within limits
        user = await db.get(User, user_id)
        operator_id = user.operator_id if user else None
        game, min_bet, max_bet, is_enabled = await cls.get_effective_game_limits(
            db, session.game_id, operator_id
        )
        if not is_enabled:
            raise GameNotFoundException(f"Game '{session.game_id}' not found or inactive")

        if bet_amount < min_bet or bet_amount > max_bet:
            raise InvalidBetAmountException(
                f"Bet amount {bet_amount} is outside allowed range [{min_bet}, {max_bet}]"
            )

        # 4. Fetch or create player's wallet
        wallet = await WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            operator_id=operator_id or game.operator_id,
        )

        # 5. ATOMIC POSTGRESQL TRANSACTION EXECUTION
        # Responsible Gaming validation (Self-exclusion, Daily bet limit, Session duration)
        await ResponsibleGamingService.validate_player_can_play(
            db=db,
            user_id=user_id,
            session_id=session_id,
            bet_amount=bet_amount,
        )

        rng_provider = rng or StandardRNGProvider()
        round_id = uuid.uuid4()

        try:
            # 5a. Debit bet amount in ledger (acquires with_for_update row lock, raises InsufficientFundsException if balance < bet)
            await WalletService.execute_transaction(
                db=db,
                wallet_id=wallet.id,
                amount=bet_amount,
                entry_type=LedgerEntryType.BET_SIMULATION,
                reference_id=round_id,
                description=f"Slot bet on {game.name}",
                commit=False,
            )

            # 5b. SlotEngine calculates RNG result and payout
            symbols, stops, payout_amount = SlotEngine.spin(rng_provider, bet_amount)
            symbols_str = [s.value if hasattr(s, "value") else str(s) for s in symbols]
            multiplier = payout_amount // bet_amount if bet_amount > 0 else 0

            # 5c. If payout > 0, credit winnings in ledger
            if payout_amount > 0:
                await WalletService.execute_transaction(
                    db=db,
                    wallet_id=wallet.id,
                    amount=payout_amount,
                    entry_type=LedgerEntryType.WIN_SIMULATION,
                    reference_id=round_id,
                    description=f"Slot win on {game.name}",
                    commit=False,
                )

            # 5d. Persist GameRound entity
            game_round = GameRound(
                id=round_id,
                session_id=session.id,
                bet_amount=bet_amount,
                payout_amount=payout_amount,
                round_data={
                    "stops": stops,
                    "symbols": symbols_str,
                    "multiplier": multiplier,
                },
                created_at=utc_now(),
            )
            db.add(game_round)

            # 5e. If idempotency_key provided, persist IdempotencyRecord
            if idempotency_key:
                idempotency_record = IdempotencyRecord(
                    key=idempotency_key,
                    wallet_id=wallet.id,
                    response_status=200,
                    response_payload={
                        "round_id": str(round_id),
                        "session_id": str(session_id),
                        "symbols": symbols_str,
                        "bet_amount": bet_amount,
                        "payout_amount": payout_amount,
                        "is_win": payout_amount > 0,
                        "current_balance": wallet.balance,
                    },
                )
                db.add(idempotency_record)

            # 5f. Commit the entire atomic transaction
            await db.commit()

            return SpinResponse(
                round_id=round_id,
                symbols=symbols_str,
                bet_amount=bet_amount,
                payout_amount=payout_amount,
                is_win=payout_amount > 0,
                current_balance=wallet.balance,
            )

        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def execute_roulette_spin(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        bets: list[RouletteBetRequest],
        idempotency_key: str | None = None,
        rng: IRNGProvider | None = None,
    ) -> RouletteSpinResponse:
        """Execute a European roulette spin round atomically integrated with the wallet ledger.

        Atomic transaction pipeline:
        1. Validates player self-exclusion and responsible gaming status.
        2. Validates session existence, ownership, and ACTIVE status.
        3. Validates game type is ROULETTE and composite bets conform to limits.
        4. Validates each individual bet with RouletteEngine.validate_bet().
        5. Locks player's wallet with FOR UPDATE and debits the total bet (BET_SIMULATION).
        6. Invokes RouletteEngine.spin() with RNG provider to resolve winning number and payouts.
        7. If total payout > 0, credits winnings into wallet ledger (WIN_SIMULATION).
        8. Persists GameRound entity linked to session with detailed breakdown in round_data.
        9. Commits transaction or rolls back on any error.

        Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
        """
        # 0. Enforce self-exclusion invariant
        exclusion = await ResponsibleGamingService.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Gameplay prohibited.",
                expires_at=exclusion.expires_at,
            )

        if not bets:
            raise InvalidRouletteBetException("At least one bet is required")

        total_bet = sum(b.amount for b in bets)

        # 1. Idempotency pre-check
        if idempotency_key:
            stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
            existing_rec = await db.scalar(stmt_rec)
            if existing_rec:
                payload = existing_rec.response_payload
                if (
                    payload.get("session_id") != str(session_id)
                    or payload.get("total_bet") != total_bet
                ):
                    raise DuplicateTransactionException(
                        f"Idempotency key '{idempotency_key}' was already processed with different parameters"
                    )
                return RouletteSpinResponse(
                    round_id=uuid.UUID(payload["round_id"]),
                    winning_number=payload["winning_number"],
                    color=payload["color"],
                    total_bet=payload["total_bet"],
                    total_payout=payload["total_payout"],
                    current_balance=payload["current_balance"],
                    resolutions=[BetResolutionResponse(**r) for r in payload["resolutions"]],
                )

        # 2. Validate session exists, belongs to user, and is ACTIVE
        stmt_session = select(GameSession).where(GameSession.id == session_id)
        session = await db.scalar(stmt_session)
        if not session or session.user_id != user_id:
            raise GameSessionNotFoundException(f"Game session '{session_id}' not found")

        if session.status != GameSessionStatus.ACTIVE:
            raise GameSessionInactiveException(f"Game session '{session_id}' is not active")

        # 3. Validate game exists, is active, and is of type ROULETTE
        user = await db.get(User, user_id)
        operator_id = user.operator_id if user else None
        game, min_bet, max_bet, is_enabled = await cls.get_effective_game_limits(
            db, session.game_id, operator_id
        )
        if not is_enabled:
            raise GameNotFoundException(f"Game '{session.game_id}' not found or inactive")

        if game.game_type != GameType.ROULETTE:
            raise GamingException(
                message=f"Game '{game.name}' is not a roulette game",
                status_code=400,
                details={"error": "invalid_game_type"},
            )

        if total_bet < min_bet or total_bet > max_bet:
            raise InvalidBetAmountException(
                f"Total bet amount {total_bet} is outside allowed range [{min_bet}, {max_bet}]"
            )

        # 4. Validate each bet structure and numbers
        roulette_bets: list[RouletteBet] = []
        for b in bets:
            rb = RouletteBet(bet_type=b.bet_type, numbers=b.numbers, amount=b.amount)
            try:
                RouletteEngine.validate_bet(rb)
            except ValueError as e:
                raise InvalidRouletteBetException(str(e))
            roulette_bets.append(rb)

        # 5. Fetch or create player's wallet
        wallet = await WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            operator_id=operator_id or game.operator_id,
        )

        # 6. Responsible Gaming validation (limits & duration)
        await ResponsibleGamingService.validate_player_can_play(
            db=db,
            user_id=user_id,
            session_id=session_id,
            bet_amount=total_bet,
        )

        # 7. ATOMIC POSTGRESQL TRANSACTION EXECUTION
        rng_provider = rng or StandardRNGProvider()
        round_id = uuid.uuid4()

        try:
            # 7a. Debit total bet amount in ledger
            await WalletService.execute_transaction(
                db=db,
                wallet_id=wallet.id,
                amount=total_bet,
                entry_type=LedgerEntryType.BET_SIMULATION,
                reference_id=round_id,
                description=f"Roulette bet on {game.name}",
                commit=False,
            )

            # 7b. RouletteEngine spin calculation
            outcome = RouletteEngine.spin(rng_provider, roulette_bets)

            # 7c. Credit winnings if total_payout > 0
            if outcome.total_payout > 0:
                await WalletService.execute_transaction(
                    db=db,
                    wallet_id=wallet.id,
                    amount=outcome.total_payout,
                    entry_type=LedgerEntryType.WIN_SIMULATION,
                    reference_id=round_id,
                    description=f"Roulette win on {game.name}",
                    commit=False,
                )

            # 7d. Persist GameRound entity
            resolutions_data = [
                {
                    "bet_type": r.bet.bet_type.value if hasattr(r.bet.bet_type, "value") else str(r.bet.bet_type),
                    "numbers": r.bet.numbers,
                    "amount": r.bet.amount,
                    "won": r.won,
                    "payout": r.payout_amount,
                }
                for r in outcome.resolutions
            ]

            game_round = GameRound(
                id=round_id,
                session_id=session.id,
                bet_amount=total_bet,
                payout_amount=outcome.total_payout,
                round_data={
                    "winning_number": outcome.winning_number,
                    "color": outcome.color,
                    "is_even": outcome.is_even,
                    "total_bet": total_bet,
                    "total_payout": outcome.total_payout,
                    "resolutions": resolutions_data,
                    "disclaimer": ROULETTE_DISCLAIMER,
                },
                created_at=utc_now(),
            )
            db.add(game_round)

            # 7e. Persist IdempotencyRecord if idempotency_key provided
            if idempotency_key:
                idempotency_record = IdempotencyRecord(
                    key=idempotency_key,
                    wallet_id=wallet.id,
                    response_status=200,
                    response_payload={
                        "round_id": str(round_id),
                        "session_id": str(session_id),
                        "winning_number": outcome.winning_number,
                        "color": outcome.color,
                        "total_bet": total_bet,
                        "total_payout": outcome.total_payout,
                        "current_balance": wallet.balance,
                        "resolutions": resolutions_data,
                    },
                )
                db.add(idempotency_record)

            # 7f. Commit the entire atomic transaction
            await db.commit()

            resolutions_resp = [
                BetResolutionResponse(
                    bet_type=r["bet_type"],
                    numbers=r["numbers"],
                    amount=r["amount"],
                    won=r["won"],
                    payout=r["payout"],
                )
                for r in resolutions_data
            ]

            return RouletteSpinResponse(
                round_id=round_id,
                winning_number=outcome.winning_number,
                color=outcome.color,
                total_bet=total_bet,
                total_payout=outcome.total_payout,
                current_balance=wallet.balance,
                resolutions=resolutions_resp,
            )

        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def start_blackjack_round(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        bet_amount: int,
        idempotency_key: str | None = None,
        rng: IRNGProvider | None = None,
    ) -> BlackjackGameStateResponse:
        """Start a new classic Blackjack round, debit initial bet, deal hands, and evaluate natural BJ.

        Atomic transaction pipeline:
        1. Validates player self-exclusion and responsible gaming limits.
        2. Validates session existence, ownership, and ACTIVE status.
        3. Validates game type is BLACKJACK and bet amount conforms to limits.
        4. Validates wallet and debits initial bet (BET_SIMULATION).
        5. Deals initial hands using BlackjackEngine.deal_initial with 6-deck shoe.
        6. Evaluates natural Blackjack immediately (pays 2.5x gross if won, 1.0x if push).
        7. Persists GameRound entity with serialized round_data.
        8. Returns state with censored dealer hole card if in progress.

        Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
        """
        # 0. Enforce self-exclusion invariant
        exclusion = await ResponsibleGamingService.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Gameplay prohibited.",
                expires_at=exclusion.expires_at,
            )

        # 1. Idempotency pre-check
        if idempotency_key:
            stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
            existing_rec = await db.scalar(stmt_rec)
            if existing_rec:
                payload = existing_rec.response_payload
                if (
                    payload.get("session_id") != str(session_id)
                    or payload.get("initial_bet") != bet_amount
                ):
                    raise DuplicateTransactionException(
                        f"Idempotency key '{idempotency_key}' was already processed with different parameters"
                    )
                return BlackjackGameStateResponse(**payload)

        # 2. Validate session exists, belongs to user, and is ACTIVE
        stmt_session = select(GameSession).where(GameSession.id == session_id)
        session = await db.scalar(stmt_session)
        if not session or session.user_id != user_id:
            raise GameSessionNotFoundException(f"Game session '{session_id}' not found")

        if session.status != GameSessionStatus.ACTIVE:
            raise GameSessionInactiveException(f"Game session '{session_id}' is not active")

        # 3. Validate game exists, is active, and is of type BLACKJACK
        user = await db.get(User, user_id)
        operator_id = user.operator_id if user else None
        game, min_bet, max_bet, is_enabled = await cls.get_effective_game_limits(
            db, session.game_id, operator_id
        )
        if not is_enabled:
            raise GameNotFoundException(f"Game '{session.game_id}' not found or inactive")

        if game.game_type != GameType.BLACKJACK:
            raise GamingException(
                message=f"Game '{game.name}' is not a blackjack game",
                status_code=400,
                details={"error": "invalid_game_type"},
            )

        if bet_amount < min_bet or bet_amount > max_bet:
            raise InvalidBetAmountException(
                f"Bet amount {bet_amount} is outside allowed range [{min_bet}, {max_bet}]"
            )

        # 4. Fetch or create player's wallet
        wallet = await WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            operator_id=operator_id or game.operator_id,
        )

        # 5. Responsible Gaming validation (limits & duration)
        await ResponsibleGamingService.validate_player_can_play(
            db=db,
            user_id=user_id,
            session_id=session_id,
            bet_amount=bet_amount,
        )

        # 6. ATOMIC POSTGRESQL TRANSACTION EXECUTION
        rng_provider = rng or StandardRNGProvider()
        round_id = uuid.uuid4()

        try:
            # 6a. Debit initial bet in ledger
            await WalletService.execute_transaction(
                db=db,
                wallet_id=wallet.id,
                amount=bet_amount,
                entry_type=LedgerEntryType.BET_SIMULATION,
                reference_id=round_id,
                description=f"Blackjack initial bet on {game.name}",
                commit=False,
            )

            # 6b. Deal cards
            shoe = BlackjackEngine.generate_shoe(num_decks=6)
            player_hand, dealer_hand, remaining_shoe = BlackjackEngine.deal_initial(shoe, rng_provider)

            initial_bet = bet_amount
            total_bet = bet_amount

            # 6c. Check immediate player natural blackjack
            if player_hand.is_blackjack():
                if dealer_hand.is_blackjack():
                    round_status = BlackjackStatus.PUSH
                    payout_amount = total_bet
                else:
                    round_status = BlackjackStatus.BLACKJACK
                    payout_amount = int(total_bet * 2.5)

                is_settled = True
                can_double = False

                if payout_amount > 0:
                    await WalletService.execute_transaction(
                        db=db,
                        wallet_id=wallet.id,
                        amount=payout_amount,
                        entry_type=LedgerEntryType.WIN_SIMULATION,
                        reference_id=round_id,
                        description=f"Blackjack win on {game.name}",
                        commit=False,
                    )
            else:
                round_status = BlackjackStatus.IN_PROGRESS
                payout_amount = 0
                is_settled = False
                can_double = True

            # 6d. Persist GameRound entity
            round_data = {
                "status": round_status.value,
                "player_cards": [{"suit": c.suit, "rank": c.rank} for c in player_hand.cards],
                "dealer_cards": [{"suit": c.suit, "rank": c.rank} for c in dealer_hand.cards],
                "shoe": [{"suit": c.suit, "rank": c.rank} for c in remaining_shoe],
                "initial_bet": initial_bet,
                "total_bet": total_bet,
                "is_settled": is_settled,
                "can_double": can_double,
                "payout_amount": payout_amount,
                "disclaimer": BLACKJACK_DISCLAIMER,
            }

            game_round = GameRound(
                id=round_id,
                session_id=session.id,
                bet_amount=bet_amount,
                payout_amount=payout_amount,
                round_data=round_data,
                created_at=utc_now(),
            )
            db.add(game_round)

            # 6e. Build card representations for response
            player_cards_schema = [
                BlackjackCardSchema(suit=c.suit, rank=c.rank, value=c.value(), hidden=False)
                for c in player_hand.cards
            ]

            if is_settled:
                dealer_cards_schema = [
                    BlackjackCardSchema(suit=c.suit, rank=c.rank, value=c.value(), hidden=False)
                    for c in dealer_hand.cards
                ]
                dealer_score = dealer_hand.calculate_total()
            else:
                dealer_cards_schema = [
                    BlackjackCardSchema(
                        suit=dealer_hand.cards[0].suit,
                        rank=dealer_hand.cards[0].rank,
                        value=dealer_hand.cards[0].value(),
                        hidden=False,
                    ),
                    BlackjackCardSchema(
                        suit="HIDDEN",
                        rank="HIDDEN",
                        value=0,
                        hidden=True,
                    ),
                ]
                dealer_score = None

            response = BlackjackGameStateResponse(
                round_id=round_id,
                status=round_status,
                player_cards=player_cards_schema,
                player_score=player_hand.calculate_total(),
                dealer_cards=dealer_cards_schema,
                dealer_score=dealer_score,
                initial_bet=initial_bet,
                total_bet=total_bet,
                payout_amount=payout_amount,
                can_double=can_double,
                is_settled=is_settled,
                current_balance=wallet.balance,
                disclaimer=BLACKJACK_DISCLAIMER,
            )

            # 6f. Idempotency record
            if idempotency_key:
                idempotency_record = IdempotencyRecord(
                    key=idempotency_key,
                    wallet_id=wallet.id,
                    response_status=200,
                    response_payload={
                        **response.model_dump(mode="json"),
                        "session_id": str(session_id),
                    },
                )
                db.add(idempotency_record)

            await db.commit()
            return response

        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def process_blackjack_action(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        round_id: uuid.UUID,
        action: BlackjackAction,
        idempotency_key: str | None = None,
        rng: IRNGProvider | None = None,
    ) -> BlackjackGameStateResponse:
        """Process player action (HIT, STAND, DOUBLE_DOWN) on an active Blackjack round.

        Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
        """
        # 0. Enforce self-exclusion invariant
        exclusion = await ResponsibleGamingService.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Gameplay prohibited.",
                expires_at=exclusion.expires_at,
            )

        # 1. Idempotency pre-check
        if idempotency_key:
            stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
            existing_rec = await db.scalar(stmt_rec)
            if existing_rec:
                payload = existing_rec.response_payload
                if (
                    payload.get("round_id") != str(round_id)
                    or payload.get("action") != action.value
                ):
                    raise DuplicateTransactionException(
                        f"Idempotency key '{idempotency_key}' was already processed with different parameters"
                    )
                return BlackjackGameStateResponse(**payload)

        # 2. Load GameRound with row-level lock
        stmt_round = (
            select(GameRound)
            .where(GameRound.id == round_id)
            .with_for_update()
        )
        game_round = await db.scalar(stmt_round)
        if not game_round:
            raise GameRoundNotFoundException(f"Game round '{round_id}' not found")

        # 3. Validate session and ownership
        stmt_session = select(GameSession).where(GameSession.id == game_round.session_id)
        session = await db.scalar(stmt_session)
        if not session or session.user_id != user_id:
            raise GameRoundNotFoundException(f"Game round '{round_id}' not found")

        if session.status != GameSessionStatus.ACTIVE:
            raise GameSessionInactiveException(f"Game session '{session.id}' is not active")

        # 4. Validate round state is IN_PROGRESS
        round_data = dict(game_round.round_data)
        current_status = round_data.get("status")

        if current_status != BlackjackStatus.IN_PROGRESS.value:
            raise GameRoundAlreadySettledException(
                f"Game round '{round_id}' is already settled with status '{current_status}'"
            )

        game = await db.get(Game, session.game_id)
        if not game or not game.is_active:
            raise GameNotFoundException(f"Game '{session.game_id}' not found or inactive")

        wallet = await WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            operator_id=game.operator_id,
        )

        player_hand = Hand([Card(suit=c["suit"], rank=c["rank"]) for c in round_data["player_cards"]])
        dealer_hand = Hand([Card(suit=c["suit"], rank=c["rank"]) for c in round_data["dealer_cards"]])
        shoe = [Card(suit=c["suit"], rank=c["rank"]) for c in round_data["shoe"]]
        initial_bet = round_data.get("initial_bet", game_round.bet_amount)
        total_bet = round_data.get("total_bet", game_round.bet_amount)

        rng_provider = rng or StandardRNGProvider()

        try:
            if action == BlackjackAction.DOUBLE_DOWN:
                if len(player_hand.cards) != 2 or not round_data.get("can_double", True):
                    raise InvalidBlackjackActionException("Double down is only allowed on the initial two cards")

                # Debit second bet equal to initial_bet
                await WalletService.execute_transaction(
                    db=db,
                    wallet_id=wallet.id,
                    amount=initial_bet,
                    entry_type=LedgerEntryType.BET_SIMULATION,
                    reference_id=round_id,
                    description=f"Blackjack double down on {game.name}",
                    commit=False,
                )

                total_bet += initial_bet
                game_round.bet_amount = total_bet

                player_hand, shoe, is_busted = BlackjackEngine.apply_hit(player_hand, shoe, rng_provider)

                if is_busted:
                    status = BlackjackStatus.PLAYER_BUSTED
                    payout_amount = 0
                    is_settled = True
                    can_double = False
                else:
                    dealer_hand, shoe = BlackjackEngine.play_dealer_turn(dealer_hand, shoe, rng_provider)
                    status, payout_amount = BlackjackEngine.evaluate_outcome(player_hand, dealer_hand, total_bet)
                    is_settled = True
                    can_double = False

                    if payout_amount > 0:
                        await WalletService.execute_transaction(
                            db=db,
                            wallet_id=wallet.id,
                            amount=payout_amount,
                            entry_type=LedgerEntryType.WIN_SIMULATION,
                            reference_id=round_id,
                            description=f"Blackjack win on {game.name}",
                            commit=False,
                        )

            elif action == BlackjackAction.HIT:
                player_hand, shoe, is_busted = BlackjackEngine.apply_hit(player_hand, shoe, rng_provider)

                if is_busted:
                    status = BlackjackStatus.PLAYER_BUSTED
                    payout_amount = 0
                    is_settled = True
                    can_double = False
                else:
                    status = BlackjackStatus.IN_PROGRESS
                    payout_amount = 0
                    is_settled = False
                    can_double = False

            elif action == BlackjackAction.STAND:
                dealer_hand, shoe = BlackjackEngine.play_dealer_turn(dealer_hand, shoe, rng_provider)
                status, payout_amount = BlackjackEngine.evaluate_outcome(player_hand, dealer_hand, total_bet)
                is_settled = True
                can_double = False

                if payout_amount > 0:
                    await WalletService.execute_transaction(
                        db=db,
                        wallet_id=wallet.id,
                        amount=payout_amount,
                        entry_type=LedgerEntryType.WIN_SIMULATION,
                        reference_id=round_id,
                        description=f"Blackjack win on {game.name}",
                        commit=False,
                    )
            else:
                raise InvalidBlackjackActionException(f"Unsupported blackjack action '{action}'")

            game_round.payout_amount = payout_amount
            round_data["status"] = status.value
            round_data["player_cards"] = [{"suit": c.suit, "rank": c.rank} for c in player_hand.cards]
            round_data["dealer_cards"] = [{"suit": c.suit, "rank": c.rank} for c in dealer_hand.cards]
            round_data["shoe"] = [{"suit": c.suit, "rank": c.rank} for c in shoe]
            round_data["total_bet"] = total_bet
            round_data["payout_amount"] = payout_amount
            round_data["is_settled"] = is_settled
            round_data["can_double"] = can_double

            game_round.round_data = round_data

            player_cards_schema = [
                BlackjackCardSchema(suit=c.suit, rank=c.rank, value=c.value(), hidden=False)
                for c in player_hand.cards
            ]

            if is_settled:
                dealer_cards_schema = [
                    BlackjackCardSchema(suit=c.suit, rank=c.rank, value=c.value(), hidden=False)
                    for c in dealer_hand.cards
                ]
                dealer_score = dealer_hand.calculate_total()
            else:
                dealer_cards_schema = [
                    BlackjackCardSchema(
                        suit=dealer_hand.cards[0].suit,
                        rank=dealer_hand.cards[0].rank,
                        value=dealer_hand.cards[0].value(),
                        hidden=False,
                    ),
                    BlackjackCardSchema(
                        suit="HIDDEN",
                        rank="HIDDEN",
                        value=0,
                        hidden=True,
                    ),
                ]
                dealer_score = None

            response = BlackjackGameStateResponse(
                round_id=round_id,
                status=status,
                player_cards=player_cards_schema,
                player_score=player_hand.calculate_total(),
                dealer_cards=dealer_cards_schema,
                dealer_score=dealer_score,
                initial_bet=initial_bet,
                total_bet=total_bet,
                payout_amount=payout_amount,
                can_double=can_double,
                is_settled=is_settled,
                current_balance=wallet.balance,
                disclaimer=BLACKJACK_DISCLAIMER,
            )

            if idempotency_key:
                idempotency_record = IdempotencyRecord(
                    key=idempotency_key,
                    wallet_id=wallet.id,
                    response_status=200,
                    response_payload={
                        **response.model_dump(mode="json"),
                        "action": action.value,
                    },
                )
                db.add(idempotency_record)

            await db.commit()
            return response

        except Exception:
            await db.rollback()
            raise

