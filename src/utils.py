from dataclasses import dataclass


@dataclass
class UnsupportedPatternFeature(Exception):
    culprit: any
