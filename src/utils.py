from dataclasses import dataclass
from typing import Any

@dataclass
class UnsupportedPatternFeature(Exception):
    culprit: Any
