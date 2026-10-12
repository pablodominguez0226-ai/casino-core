from enum import Enum


class LedgerEntryType(str, Enum):
    """Enumeration of immutable ledger transaction movement types."""

    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    BET_SIMULATION = "BET_SIMULATION"
    WIN_SIMULATION = "WIN_SIMULATION"
    BONUS = "BONUS"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"
