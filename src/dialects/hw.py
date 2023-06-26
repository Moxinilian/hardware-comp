from typing import cast
from dataclasses import dataclass
from xdsl.irdl import (
    irdl_op_definition,
    IRDLOperation,
    var_operand_def,
    result_def,
    attr_def,
    region_def,
    VarOperand,
)
from xdsl.ir import (
    Dialect,
    OpResult,
    Attribute,
    Region,
    SSAValue,
    Block,
)
from xdsl.traits import IsTerminator
from xdsl.dialects.builtin import (
    StringAttr,
    ArrayAttr,
    SymbolNameAttr,
    IntegerAttr,
    IntegerType,
    FunctionType,
    i1,
)
from xdsl.utils.exceptions import VerifyException


@irdl_op_definition
class HwConstant(IRDLOperation):
    name = "hw.constant"

    value: IntegerAttr = attr_def(IntegerAttr)
    output: OpResult = result_def(IntegerType)

    @staticmethod
    def from_attr(attr: IntegerAttr):
        return HwConstant.create(result_types=[attr.typ], attributes={"value": attr})

    def verify_(self) -> None:
        if self.value.typ != self.output.typ:
            raise VerifyException(f"'{self.value}' is not of type '{self.output}'")


@dataclass
class HwOutputNotFound(Exception):
    block: Block


@irdl_op_definition
class HwOutput(IRDLOperation):
    name = "hw.output"

    outputs: VarOperand = var_operand_def()

    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_outputs(outputs: list[SSAValue]):
        return HwOutput.create(operands=outputs)

    @staticmethod
    def get_unique_output(block: Block) -> "HwOutput":
        if block.last_op and isinstance(block.last_op, HwOutput):
            return block.last_op
        raise HwOutputNotFound(block)


@irdl_op_definition
class HwModule(IRDLOperation):
    name = "hw.module"

    sym_name: SymbolNameAttr = attr_def(SymbolNameAttr)
    function_type: FunctionType = attr_def(FunctionType)
    parameters: ArrayAttr = attr_def(ArrayAttr)
    comment: StringAttr = attr_def(StringAttr)
    argNames: ArrayAttr[StringAttr] = attr_def(ArrayAttr[StringAttr])
    argLocs: ArrayAttr = attr_def(ArrayAttr)  # TODO: location attr constraint
    resultNames: ArrayAttr[StringAttr] = attr_def(ArrayAttr[StringAttr])
    resultLocs: ArrayAttr = attr_def(ArrayAttr)  # TODO: location attr constraint

    region: Region = region_def()

    @staticmethod
    def from_block(
        name: str,
        block: Block,
        arg_names: list[str],
        result_names: list[str],
        comment: str = "",
        parameters: list[Attribute] = [],
    ):
        input_attrs = list(map(lambda x: x.typ, block.args))
        output_attrs = list(
            map(lambda x: x.typ, HwOutput.get_unique_output(block).outputs)
        )
        return HwModule.create(
            attributes={
                "sym_name": SymbolNameAttr(name),
                "function_type": FunctionType.from_attrs(
                    ArrayAttr(input_attrs), ArrayAttr(output_attrs)
                ),
                "parameters": ArrayAttr(parameters),
                "comment": StringAttr(comment),
                "argNames": ArrayAttr(
                    list(map(lambda x: StringAttr(x), arg_names))
                ),
                "argLocs": ArrayAttr([]),  # TODO: support locations
                "resultNames": ArrayAttr(
                    list(map(lambda x: StringAttr(x), result_names))
                ),
                "resultLocs": ArrayAttr([]),  # TODO: support locations
            },
            regions=[Region([block])],
        )


Hw = Dialect([HwConstant, HwModule, HwOutput], [])
