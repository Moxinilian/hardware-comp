from attr import dataclass

"""
Encoding of operations follows the following structure, in order of least
significant bit to most significant bit:

- The opcode of the operation
- For i in 1..=m:
    - The offset to the value of the i-th operand
"""


@dataclass
class OperationInfo:
    opcode: int
    operand_typcodes: list[int]

@dataclass
class OperationContext:
    operations: dict[str, OperationInfo]

@dataclass
class EncodingContext:
    opcode_width: int
    operand_offset_width: int
    max_operand_amount: int
