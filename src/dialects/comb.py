from enum import Enum
from typing import Annotated, cast
from xdsl.irdl import (
    irdl_op_definition,
    IRDLOperation,
    Operand,
    VarOperand,
    ConstraintVar,
    var_operand_def,
    result_def,
    attr_def,
    operand_def,
    opt_attr_def,
)
from xdsl.ir import (
    Dialect,
    OpResult,
    SSAValue,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    i1,
    UnitAttr,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class CombConcat(IRDLOperation):
    name = "comb.concat"

    inputs: VarOperand = var_operand_def(IntegerType)
    output: OpResult = result_def(IntegerType)

    @staticmethod
    def from_values(inputs: list[SSAValue]):
        sum_of_width = sum([cast(IntegerType, arg.typ).width.data for arg in inputs])
        return CombConcat.create(
            operands=inputs, result_types=[IntegerType(sum_of_width)]
        )

    def verify_(self) -> None:
        output_type = cast(IntegerType, self.output.typ)
        sum_of_width = sum(
            [cast(IntegerType, arg.typ).width.data for arg in self.inputs]
        )
        if sum_of_width != output_type.width.data:
            raise VerifyException(
                f"sum of integer width ({sum_of_width}) "
                f"is different to result"
                f"width ({output_type.width.data})"
            )


@irdl_op_definition
class CombExtract(IRDLOperation):
    name = "comb.extract"

    low_bit: IntegerAttr = attr_def(IntegerAttr, attr_name="lowBit")
    inputs: Operand = operand_def(IntegerType)
    output: OpResult = result_def(IntegerType)

    @staticmethod
    def from_values(inputs: SSAValue, result_width: int, start: int):
        return CombExtract.create(
            operands=[inputs],
            result_types=[IntegerType(result_width)],
            attributes={"lowBit": IntegerAttr.from_int_and_width(start, 32)},
        )

    def verify_(self) -> None:
        output_type = cast(IntegerType, self.output.typ)
        input_type = cast(IntegerType, self.inputs.typ)
        if self.low_bit.value.data + output_type.width.data > input_type.width.data + 1:
            raise VerifyException(
                f"output width {output_type.width} is "
                f"too large for input of width "
                f"{input_type.width} (included low bit "
                f"is at {self.low_bit.value.data})"
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

    predicate: IntegerAttr = attr_def(IntegerAttr)
    lhs: Operand = operand_def(IntegerType)
    rhs: Operand = operand_def(IntegerType)
    output: OpResult = result_def(i1)

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

    lhs: Operand = operand_def(T)
    rhs: Operand = operand_def(T)
    result: OpResult = result_def(T)

    two_state: UnitAttr | None = opt_attr_def(UnitAttr)


class VariadicCombOp(IRDLOperation):
    """
    A variadic comb operation. It has a variadic number of operands, and a single
    result, all of the same type.
    """

    T = Annotated[IntegerType, ConstraintVar("T")]

    inputs: VarOperand = var_operand_def(T)
    result: OpResult = result_def(T)

    two_state: UnitAttr | None = opt_attr_def(UnitAttr)


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

    cond: Operand = operand_def(IntegerType(1))
    true_value: Operand = operand_def(T)
    false_value: Operand = operand_def(T)
    result: OpResult = result_def(T)

    @staticmethod
    def from_values(cond: SSAValue, true: SSAValue, false: SSAValue):
        return CombMux(operands=[cond, true, false], result_types=[true.typ])


Comb = Dialect(
    [CombConcat, CombExtract, CombICmp, CombXor, CombAnd, CombOr, CombSub, CombMux], []
)
