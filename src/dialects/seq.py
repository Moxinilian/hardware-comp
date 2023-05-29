from typing import Annotated
from attr import dataclass
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    OpAttr,
    ParameterDef,
)
from xdsl.ir import (
    ParametrizedAttribute,
    Dialect,
    Operation,
    OpResult,
    Attribute,
    Region,
    SSAValue,
)
from xdsl.dialects.builtin import (
    StringAttr,
    ArrayAttr,
    IntegerAttr,
    SymbolRefAttr,
    DictionaryAttr,
    IntegerType,
    i1,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class SeqCompregCe(IRDLOperation):
    name = "seq.compreg.ce"

    name: OpAttr[StringAttr]
    input: Annotated[Operand, AnyAttr()]
    clk: Annotated[Operand, i1]
    clockEnable: Annotated[Operand, i1]
    reset: Annotated[Operand, i1]
    resetValue: Annotated[Operand, AnyAttr()]
    data: Annotated[OpResult, AnyAttr()]

    @staticmethod
    def new(
        name: str,
        input: SSAValue,
        clock: SSAValue,
        enable: SSAValue,
        reset: SSAValue,
        reset_value: SSAValue,
    ) -> "SeqCompregCe":
        return SeqCompregCe(
            operands=[input, clock, enable, reset, reset_value],
            attributes={"name": StringAttr.from_str(name)},
        )

    def verify_(self) -> None:
        if self.input.typ != self.resetValue.typ or self.input.typ != self.data.typ:
            raise VerifyException("inconsistent data types")


Seq = Dialect([SeqCompregCe], [])
