"""Responsible Gaming & KYC enumerations.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from enum import Enum


class KycStatus(str, Enum):
    """Lifecycle statuses for simulated KYC verification."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentType(str, Enum):
    """Supported identification document types for simulated KYC."""

    DNI = "DNI"
    PASSPORT = "PASSPORT"
    DRIVER_LICENSE = "DRIVER_LICENSE"
