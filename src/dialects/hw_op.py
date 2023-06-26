from typing import cast
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    IRDLOperation,
    Operand,
    ParameterDef,
    result_def,
    attr_def,
    operand_def,
)
from xdsl.ir import (
    ParametrizedAttribute,
    Dialect,
    OpResult,
    SSAValue,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    i1,
)
from xdsl.utils.exceptions import VerifyException

from encoder import EncodingContext


@irdl_attr_definition
class HwOperation(ParametrizedAttribute):
    name = "hw_op.operation"

    opcode_integer: ParameterDef[IntegerType]
    operand_offset_integer: ParameterDef[IntegerType]
    max_operand_amount: ParameterDef[IntegerAttr]

    @staticmethod
    def from_widths(
        opcode_width: int, operand_offset_width: int, max_operand_amount: int
    ):
        assert opcode_width.bit_length() <= 32
        assert operand_offset_width.bit_length() <= 32
        assert max_operand_amount.bit_length() <= 32
        return HwOperation(
            [
                IntegerType(opcode_width),
                IntegerType(operand_offset_width),
                IntegerAttr.from_int_and_width(max_operand_amount, 32),
            ]
        )

    @staticmethod
    def from_encoding_ctx(enc_ctx: EncodingContext):
        return HwOperation.from_widths(
            enc_ctx.opcode_width,
            enc_ctx.operand_offset_width,
            enc_ctx.max_operand_amount,
        )

    def get_bit_width(self) -> int:
        width = 0
        width += self.opcode_integer.width.data  # operation opcode
        max_op_amount = self.max_operand_amount.value.data
        width += (
            max_op_amount * self.operand_offset_integer.width.data
        )  # each operand's offset
        return width


@irdl_op_definition
class HwOpGetOpcode(IRDLOperation):
    name = "hw_op.get_opcode"

    op: Operand = operand_def(HwOperation)
    output: OpResult = result_def(IntegerType)

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.opcode_integer != self.output.typ:
            raise VerifyException("trying to get opcode as the wrong type")


@irdl_op_definition
class HwOpGetOperandOffset(IRDLOperation):
    name = "hw_op.get_operand_offset"

    op: Operand = operand_def(HwOperation)
    operand: IntegerAttr = attr_def(IntegerAttr)
    output: OpResult = result_def(IntegerType)

    @staticmethod
    def from_operand(op: SSAValue, operand: int):
        return HwOpGetOperandOffset.create(
            operands=[op],
            result_types=[cast(HwOperation, op.typ).operand_offset_integer],
            attributes={"operand": IntegerAttr.from_index_int_value(operand)},
        )

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.operand_offset_integer != self.output.typ:
            raise VerifyException("trying to get operand offset as the wrong type")
        if op_type.max_operand_amount.value.data <= self.operand.value.data:
            raise VerifyException("trying to fetch operand outside max range")


@irdl_op_definition
class HwOpHasOperand(IRDLOperation):
    name = "hw_op.has_operand"

    op: Operand = operand_def(HwOperation)
    operand: IntegerAttr = attr_def(IntegerAttr)
    output: OpResult = result_def(i1)

    @staticmethod
    def from_operand(op: SSAValue, operand: int):
        return HwOpHasOperand.create(
            operands=[op],
            result_types=[i1],
            attributes={"operand": IntegerAttr.from_index_int_value(operand)},
        )

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.max_operand_amount.value.data <= self.operand.value.data:
            raise VerifyException("trying to check operand outside max range")


HwOp = Dialect(
    [HwOpGetOpcode, HwOpGetOperandOffset, HwOpHasOperand],
    [HwOperation],
)
