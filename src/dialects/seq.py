from xdsl.irdl import (
    irdl_op_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    result_def,
    attr_def,
    operand_def,
)
from xdsl.ir import Dialect, OpResult, SSAValue, Attribute
from xdsl.dialects.builtin import (
    StringAttr,
    i1,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class SeqCompregCe(IRDLOperation):
    name = "seq.compreg.ce"

    register_name: StringAttr = attr_def(StringAttr, attr_name="name")
    input: Operand = operand_def(AnyAttr())
    clk: Operand = operand_def(i1)
    clockEnable: Operand = operand_def(i1)
    reset: Operand = operand_def(i1)
    resetValue: Operand = operand_def(AnyAttr())
    data: OpResult = result_def(AnyAttr())

    @staticmethod
    def new(
        name: str,
        data_type: Attribute,
        input: SSAValue | None,
        clock: SSAValue,
        enable: SSAValue,
        reset: SSAValue | None = None,
        reset_value: SSAValue | None = None,
    ) -> "SeqCompregCe":
        return SeqCompregCe(
            operands=[input, clock, enable, reset, reset_value],
            result_types=[data_type],
            attributes={"name": StringAttr.from_str(name)},
        )

    def verify_(self) -> None:
        if self.input.typ != self.resetValue.typ or self.input.typ != self.data.typ:
            raise VerifyException("inconsistent data types")


Seq = Dialect([SeqCompregCe], [])
