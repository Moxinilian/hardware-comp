from enum import Enum
from typing import Annotated
from attr import dataclass
from xdsl.irdl import (irdl_op_definition, irdl_attr_definition,
                       irdl_data_definition, AnyAttr, Operand, OpAttr,
                       ParameterDef)
from xdsl.ir import (ParametrizedAttribute, MLIRType, Dialect, Operation,
                     OpResult, Attribute, Region, Data)
from xdsl.dialects.builtin import (StringAttr, ArrayAttr, SymbolRefAttr,
                                   DictionaryAttr, IntegerAttr, IntegerType,
                                   i1)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class CombExtract(Operation):
    name = "comb.extract"

    low_bit: OpAttr[IntegerAttr]
    inputs: Annotated[Operand, IntegerType]
    output: Annotated[OpResult, IntegerType]

    def verify_(self) -> None:
        if self.low_bit.data + self.output.typ.width > self.inputs.typ.width + 1:
            raise VerifyException(f"output width {self.output.typ.width} is "
                                  f"too large for input of width "
                                  f"{self.inputs.width} (included low bit "
                                  f"is at {self.low_bit.data})")


class ICmpPredicate(Enum):
    EQ = 0
    NE = 1
    SLT = 2
    SLE = 3
    SGT = 4
    SGE = 5
    ULT = 6
    ULE = 7
    UGT = 8
    UGE = 9
    CEQ = 10
    CNE = 11
    WEQ = 12
    WNE = 13


@irdl_op_definition
class CombICmp(Operation):
    name = "comb.icmp"

    predicate: OpAttr[IntegerAttr]
    lhs: Annotated[Operand, IntegerType]
    rhs: Annotated[Operand, IntegerType]
    output: Annotated[OpResult, i1]


Comb = Dialect([CombExtract, CombICmp], [])
