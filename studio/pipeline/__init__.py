"""Automated movie production pipeline.

Reading order for anyone new:
  RESEARCH.md      what captures and retains attention, with sources
  doctrine/        those findings as numbers the machine can check
  agents/          the role cards — the craft half of each job
  pipeline/        the executable half
"""

from .ceo import ProductionRun, Studio
from .models import Beat, Clue, Doctrine, Episode, Twist, TwistLedger
from .retention import RetentionEngine, RetentionReport

__all__ = [
    "Studio", "ProductionRun",
    "Doctrine", "Episode", "Beat", "Twist", "Clue", "TwistLedger",
    "RetentionEngine", "RetentionReport",
]
