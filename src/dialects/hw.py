from enum import Enum
from typing import Annotated
from attr import dataclass
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    irdl_data_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    OpAttr,
    ParameterDef,
    VarOperand,
)
from xdsl.ir import (
    ParametrizedAttribute,
    Dialect,
    Operation,
    OpResult,
    Attribute,
    Region,
    Data,
    SSAValue,
)
from xdsl.dialects.builtin import (
    StringAttr,
    ArrayAttr,
    SymbolRefAttr,
    DictionaryAttr,
    IntegerAttr,
    IntegerType,
    i1,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class HwConstant(IRDLOperation):
    name = "hw.constant"

    value: OpAttr[IntegerAttr]
    output: Annotated[OpResult, IntegerType]

    @staticmethod
    def from_attr(attr: IntegerAttr):
        return HwConstant.create(result_types=[attr.typ], attributes={"value": attr})

    def verify_(self) -> None:
        if self.value.typ != self.output.typ:
            raise VerifyException(f"'{self.value}' is not of type '{self.output}'")


Hw = Dialect([HwConstant], [])
