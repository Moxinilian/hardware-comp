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


@irdl_attr_definition
class HwOperation(ParametrizedAttribute):
    name = "hw_op.operation"

    kind_integer: ParameterDef[IntegerType]

    @staticmethod
    def from_widths(kind_width: int):
        return HwOperation([IntegerType.from_width(kind_width)])


@irdl_op_definition
class HwOpGetKind(IRDLOperation):
    name = "hw_op.get_kind"

    op: Annotated[Operand, HwOperation]
    output: Annotated[OpResult, IntegerType]

    def verify_(self) -> None:
        if self.op.typ.kind_integer != self.output.typ:
            raise VerifyException("trying to get kind as the wrong type")


HwOp = Dialect([HwOpGetKind], [HwOperation])
