from attr import dataclass


@dataclass
class UnsupportedPatternFeature(Exception):
    culprit: any
