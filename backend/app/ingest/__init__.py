"""Source-agnostic ingest package.

All data providers — whether polled APIs or future Kafka stream consumers —
implement IngestSource and flow through shared normalization and signal generation.
"""
from app.ingest.base import IngestEvent, IngestSource, SourceType

__all__ = ["IngestEvent", "IngestSource", "SourceType"]
