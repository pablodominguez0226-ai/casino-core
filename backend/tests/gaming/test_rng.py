"""Unit tests for RNG providers.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import pytest

from app.modules.gaming.engines.rng import (
    DeterministicRNGProvider,
    StandardRNGProvider,
)


def test_standard_rng_within_bounds() -> None:
    """Validate that StandardRNGProvider generates values strictly within [min_val, max_val]."""
    rng = StandardRNGProvider()
    min_val = 0
    max_val = 4

    for _ in range(200):
        val = rng.generate_int(min_val, max_val)
        assert min_val <= val <= max_val
        assert isinstance(val, int)


def test_standard_rng_single_value_range() -> None:
    """Validate that StandardRNGProvider handles equal min_val and max_val correctly."""
    rng = StandardRNGProvider()
    assert rng.generate_int(5, 5) == 5
    assert rng.generate_int(0, 0) == 0


def test_standard_rng_invalid_bounds_raises_error() -> None:
    """Validate that min_val > max_val raises ValueError."""
    rng = StandardRNGProvider()
    with pytest.raises(ValueError):
        rng.generate_int(10, 5)


def test_deterministic_rng_reproducibility() -> None:
    """Validate that DeterministicRNGProvider reliably reproduces exact predefined sequences."""
    sequence = [4, 2, 0, 3, 1]
    rng = DeterministicRNGProvider(sequence=sequence)

    results = [rng.generate_int(0, 10) for _ in range(len(sequence))]
    assert results == sequence


def test_deterministic_rng_exhaustion_raises_index_error() -> None:
    """Validate that DeterministicRNGProvider raises IndexError once sequence is exhausted."""
    rng = DeterministicRNGProvider([1, 2])
    assert rng.generate_int(0, 5) == 1
    assert rng.generate_int(0, 5) == 2

    with pytest.raises(IndexError):
        rng.generate_int(0, 5)


def test_deterministic_rng_set_sequence() -> None:
    """Validate resetting sequence in DeterministicRNGProvider."""
    rng = DeterministicRNGProvider([1])
    assert rng.generate_int(0, 5) == 1

    rng.set_sequence([9, 8])
    assert rng.generate_int(0, 10) == 9
    assert rng.generate_int(0, 10) == 8
