from types import FunctionType
from typing import Annotated
import attr
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    result_def,
    attr_def,
    operand_def,
    var_operand_def,
    var_result_def,
    region_def,
    VarOperand,
    VarOpResult,
)
from xdsl.traits import IsTerminator, NoTerminator
from xdsl.ir import (
    ParametrizedAttribute,
    SSAValue,
    TypeAttribute,
    Dialect,
    OpResult,
    Attribute,
    Region,
    Block,
    VerifyException,
)
from xdsl.dialects.builtin import (
    StringAttr,
    ArrayAttr,
    SymbolRefAttr,
    DictionaryAttr,
    FunctionType,
    i1,
)

# todo: interfaces, traits, region constraints


@irdl_attr_definition
class FsmInstanceType(ParametrizedAttribute, TypeAttribute):
    name = "fsm.instance"


@irdl_op_definition
class FsmHwInstance(IRDLOperation):
    name = "fsm.hw_instance"

    sym_name: StringAttr = attr_def(StringAttr)
    machine: SymbolRefAttr = attr_def(SymbolRefAttr)  # todo: flat constraint
    inputs: VarOperand = var_operand_def(Attribute)
    clock: Operand = operand_def(i1)
    reset: Operand = operand_def(i1)
    outputs: VarOpResult = var_result_def(Attribute)

    @staticmethod
    def new(
        instance_name: str,
        machine_name: str,
        inputs: list[SSAValue],
        clock: SSAValue,
        reset: SSAValue,
        output_types: list[Attribute],
    ):
        return FsmHwInstance(
            operands=[inputs, clock, reset],
            result_types=[output_types],
            attributes={
                "sym_name": StringAttr(instance_name),
                "machine": SymbolRefAttr(machine_name),
            },
        )

    def verify_(self) -> None:
        for i, must_be_type in enumerate(self.inputs):
            if not isinstance(must_be_type.typ, TypeAttribute):
                raise VerifyException(f"input {i} is not a TypeAttribute")
        for i, must_be_type in enumerate(self.outputs):
            if not isinstance(must_be_type.typ, TypeAttribute):
                raise VerifyException(f"output {i} is not a TypeAttribute")


@irdl_op_definition
class FsmInstance(IRDLOperation):
    name = "fsm.instance"

    sym_name: StringAttr = attr_def(StringAttr)
    machine: SymbolRefAttr = attr_def(SymbolRefAttr)  # todo: flat constraint
    outputs: OpResult = result_def(FsmInstanceType)


@irdl_op_definition
class FsmMachine(IRDLOperation):
    name = "fsm.machine"

    sym_name: StringAttr = attr_def(StringAttr)
    initial_state: StringAttr = attr_def(StringAttr, attr_name="initialState")
    function_type: FunctionType = attr_def(FunctionType)

    body: Region = region_def()

    traits = frozenset([NoTerminator()])

    @staticmethod
    def new(name: str, initial_state: str, function_type: FunctionType, body: Block):
        return FsmMachine(
            attributes={
                "sym_name": StringAttr(name),
                "initialState": StringAttr(initial_state),
                "function_type": function_type,
            },
            regions=[Region(blocks=[body])],
        )


@irdl_op_definition
class FsmOutput(IRDLOperation):
    name = "fsm.output"

    operands_out: VarOperand = var_operand_def(AnyAttr())

    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_output(output: list[SSAValue]):
        return FsmOutput(operands=[output])


@irdl_op_definition
class FsmReturn(IRDLOperation):
    name = "fsm.return"

    operand: Operand = operand_def(i1)

    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_value(to_return: SSAValue):
        return FsmReturn(operands=[to_return])


@irdl_op_definition
class FsmState(IRDLOperation):
    name = "fsm.state"

    sym_name: StringAttr = attr_def(StringAttr)

    output: Region = region_def()
    transitions: Region = region_def()

    traits = frozenset([NoTerminator()])

    @staticmethod
    def new(name: str, output: Block, transitions: Block):
        return FsmState(
            attributes={"sym_name": StringAttr(name)},
            regions=[Region(blocks=[output]), Region(blocks=[transitions])],
        )


@irdl_op_definition
class FsmTransition(IRDLOperation):
    name = "fsm.transition"

    next_state: SymbolRefAttr = attr_def(
        SymbolRefAttr, attr_name="nextState"
    )  # todo: flat constraint

    guard: Region = region_def()
    action: Region = region_def()

    traits = frozenset([NoTerminator()])

    @staticmethod
    def new(next_state: str, guard: Block, action: Block):
        return FsmTransition(
            attributes={"nextState": SymbolRefAttr(next_state)},
            regions=[Region(blocks=[guard]), Region(blocks=[action])],
        )


@irdl_op_definition
class FsmTrigger(IRDLOperation):
    name = "fsm.trigger"

    inputs: Operand = operand_def(AnyAttr())
    instance: Operand = operand_def(FsmInstanceType)
    outputs: OpResult = result_def()


@irdl_op_definition
class FsmUpdate(IRDLOperation):
    name = "fsm.update"

    variable: Operand = operand_def(AnyAttr())
    value: Operand = operand_def(AnyAttr())


@irdl_op_definition
class FsmVariable(IRDLOperation):
    name = "fsm.variable"

    init_value: Attribute = attr_def(Attribute, attr_name="initValue")
    var_name: StringAttr = attr_def(StringAttr, attr_name="name")
    result: OpResult = result_def()

    @staticmethod
    def from_init_val(name: str, typ: Attribute, init_value: Attribute):
        return FsmVariable(
            attributes={"initValue": init_value, "name": StringAttr(name)},
            result_types=[typ],
        )


Fsm = Dialect(
    [
        FsmHwInstance,
        FsmInstance,
        FsmMachine,
        FsmOutput,
        FsmReturn,
        FsmState,
        FsmTransition,
        FsmTrigger,
        FsmUpdate,
        FsmVariable,
    ],
    [FsmInstanceType],
)
