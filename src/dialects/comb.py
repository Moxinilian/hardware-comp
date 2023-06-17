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
    ConstraintVar,
    OptOpAttr,
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
    UnitAttr,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class CombConcat(IRDLOperation):
    name = "comb.concat"

    inputs: Annotated[VarOperand, IntegerType]
    output: Annotated[OpResult, IntegerType]

    @staticmethod
    def from_values(inputs: list[SSAValue]):
        sum_of_width = sum([arg.typ.width.data for arg in inputs])
        return CombConcat.create(
            operands=inputs, result_types=[IntegerType(sum_of_width)]
        )

    def verify_(self) -> None:
        sum_of_width = sum([arg.typ.width.data for arg in self.inputs])
        if sum_of_width != self.output.typ.width.data:
            raise VerifyException(
                f"sum of integer width ({sum_of_width}) "
                f"is different to result"
                f"width ({self.output.typ.width.data})"
            )


@irdl_op_definition
class CombExtract(IRDLOperation):
    name = "comb.extract"

    lowBit: OpAttr[IntegerAttr]
    inputs: Annotated[Operand, IntegerType]
    output: Annotated[OpResult, IntegerType]

    @staticmethod
    def from_values(inputs: SSAValue, result_width: int, start: int):
        return CombExtract.create(
            operands=[inputs],
            result_types=[IntegerType(result_width)],
            attributes={"lowBit": IntegerAttr.from_int_and_width(start, 32)},
        )

    def verify_(self) -> None:
        if (
            self.lowBit.value.data + self.output.typ.width.data
            > self.inputs.typ.width.data + 1
        ):
            raise VerifyException(
                f"output width {self.output.typ.width} is "
                f"too large for input of width "
                f"{self.inputs.width} (included low bit "
                f"is at {self.lowBit.data})"
            )


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
class CombICmp(IRDLOperation):
    name = "comb.icmp"

    predicate: OpAttr[IntegerAttr]
    lhs: Annotated[Operand, IntegerType]
    rhs: Annotated[Operand, IntegerType]
    output: Annotated[OpResult, i1]

    @staticmethod
    def from_values(lhs: SSAValue, rhs: SSAValue, predicate: ICmpPredicate):
        return CombICmp(
            operands=[lhs, rhs],
            result_types=[i1],
            attributes={
                "predicate": IntegerAttr.from_int_and_width(predicate.value, 64)
            },
        )


class BinCombOp(IRDLOperation):
    """
    A binary comb operation. It has two operands and one
    result, all of the same integer type.
    """

    T = Annotated[IntegerType, ConstraintVar("T")]

    lhs: Annotated[Operand, T]
    rhs: Annotated[Operand, T]
    result: Annotated[OpResult, T]

    two_state: OptOpAttr[UnitAttr]


class VariadicCombOp(IRDLOperation):
    """
    A variadic comb operation. It has a variadic number of operands, and a single
    result, all of the same type.
    """

    T = Annotated[IntegerType, ConstraintVar("T")]

    inputs: Annotated[VarOperand, T]
    result: Annotated[OpResult, T]

    two_state: OptOpAttr[UnitAttr]


@irdl_op_definition
class CombXor(VariadicCombOp):
    name = "comb.xor"

    @staticmethod
    def from_values(operands: list[SSAValue]):
        return CombXor(operands=operands, result_types=[operands[0].typ])


@irdl_op_definition
class CombAnd(VariadicCombOp):
    name = "comb.and"

    @staticmethod
    def from_values(operands: list[SSAValue]):
        return CombAnd(operands=operands, result_types=[operands[0].typ])


@irdl_op_definition
class CombOr(VariadicCombOp):
    name = "comb.or"

    @staticmethod
    def from_values(operands: list[SSAValue]):
        return CombOr(operands=operands, result_types=[operands[0].typ])


@irdl_op_definition
class CombSub(BinCombOp):
    name = "comb.sub"

    @staticmethod
    def from_values(lhs: SSAValue, rhs: SSAValue):
        return CombSub(operands=[lhs, rhs], result_types=[lhs.typ])


@irdl_op_definition
class CombMux(IRDLOperation):
    """
    Select between two values based on a condition.
    """

    name = "comb.mux"

    T = Annotated[IntegerType, ConstraintVar("T")]

    cond: Annotated[Operand, IntegerType(1)]
    true_value: Annotated[Operand, T]
    false_value: Annotated[Operand, T]
    result: Annotated[OpResult, T]

    @staticmethod
    def from_values(cond: SSAValue, true: SSAValue, false: SSAValue):
        return CombMux(operands=[cond, true, false], result_types=[true.typ])


Comb = Dialect(
    [CombConcat, CombExtract, CombICmp, CombXor, CombAnd, CombOr, CombSub, CombMux], []
)
