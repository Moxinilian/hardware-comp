
from attr import dataclass


@dataclass
class EncodingContext:
    kind_width: int

    operand_offset_width: int

    max_operand_amount: int
