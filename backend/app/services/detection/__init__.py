"""
BrandShield AI — Deterministic Detection Engine

All modules in this package are pure, deterministic, and independently testable.
No LLM calls. No external HTTP requests. No ML library dependencies at this stage.

Public API surface:
  from app.services.detection.risk_engine import run, CandidateBundle
  from app.services.detection.contracts import DetectionResult, SignalResult
"""
