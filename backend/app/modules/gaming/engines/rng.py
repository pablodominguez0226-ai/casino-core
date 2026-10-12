"""RNG abstraction and providers for casino game engines.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from abc import ABC, abstractmethod
import secrets


class IRNGProvider(ABC):
    """Abstract interface for Random Number Generation providers.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    @abstractmethod
    def generate_int(self, min_val: int, max_val: int) -> int:
        """Generate a pseudo-random integer between min_val and max_val (inclusive).

        Args:
            min_val: Minimum integer value (inclusive).
            max_val: Maximum integer value (inclusive).

        Returns:
            An integer N such that min_val <= N <= max_val.
        """
        pass


class StandardRNGProvider(IRNGProvider):
    """Cryptographically-secure pseudo-random number generator for educational simulation.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    def generate_int(self, min_val: int, max_val: int) -> int:
        """Generate a random integer in range [min_val, max_val] using secrets.randbelow.

        Args:
            min_val: Minimum integer (inclusive).
            max_val: Maximum integer (inclusive).

        Returns:
            Generated integer.
        """
        if min_val > max_val:
            raise ValueError(f"min_val ({min_val}) must be <= max_val ({max_val})")
        if min_val == max_val:
            return min_val
        span = (max_val - min_val) + 1
        return min_val + secrets.randbelow(span)


class DeterministicRNGProvider(IRNGProvider):
    """Deterministic RNG provider yielding a predefined sequence for testing.

    Simulación educativa. RNG no apto ni certificado para juego con dinero real.
    """

    def __init__(self, sequence: list[int] | None = None) -> None:
        """Initialize deterministic provider with an optional sequence.

        Args:
            sequence: List of integers to return sequentially.
        """
        self._sequence: list[int] = list(sequence) if sequence is not None else []
        self._index: int = 0

    def set_sequence(self, sequence: list[int]) -> None:
        """Replace the sequence and reset index."""
        self._sequence = list(sequence)
        self._index = 0

    def generate_int(self, min_val: int, max_val: int) -> int:
        """Return the next integer from the predefined sequence.

        Raises:
            IndexError: If the predefined sequence is exhausted.
        """
        if self._index >= len(self._sequence):
            raise IndexError("Deterministic RNG sequence exhausted")
        val = self._sequence[self._index]
        self._index += 1
        return val
