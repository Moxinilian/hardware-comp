from types import FunctionType
from typing import Annotated
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    result_def,
    attr_def,
    operand_def,
    region_def,
)
from xdsl.ir import (
    ParametrizedAttribute,
    TypeAttribute,
    Dialect,
    OpResult,
    Attribute,
    Region,
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
    inputs: Operand = operand_def(AnyAttr())  # todo: MLIR type constraint
    clock: Operand = operand_def(i1)
    reset: Operand = operand_def(i1)
    outputs: OpResult = result_def(AnyAttr())  # todo: MLIR type constraint


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
    initial_state: StringAttr = attr_def(StringAttr)
    function_type: FunctionType = attr_def(FunctionType)
    arg_attrs: ArrayAttr[DictionaryAttr] = attr_def(ArrayAttr[DictionaryAttr])
    res_attrs: ArrayAttr[DictionaryAttr] = attr_def(ArrayAttr[DictionaryAttr])
    arg_names: ArrayAttr[StringAttr] = attr_def(ArrayAttr[StringAttr])
    res_names: ArrayAttr[StringAttr] = attr_def(ArrayAttr[StringAttr])

    body: Region = region_def()


@irdl_op_definition
class FsmOutput(IRDLOperation):
    name = "fsm.output"

    operands: Operand = operand_def(AnyAttr())


@irdl_op_definition
class FsmReturn(IRDLOperation):
    name = "fsm.return"

    operand: Operand = operand_def(i1)


@irdl_op_definition
class FsmState(IRDLOperation):
    name = "fsm.state"

    sym_name: StringAttr = attr_def(StringAttr)

    output: Region = region_def()
    transitions: Region = region_def()


@irdl_op_definition
class FsmTransition(IRDLOperation):
    name = "fsm.transition"

    next_state: SymbolRefAttr = attr_def(SymbolRefAttr)  # todo: flat constraint

    guard: Region = region_def()
    action: Region = region_def()


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

    init_value: Attribute = attr_def(Attribute)
    var_name: StringAttr = attr_def(StringAttr, attr_name="name")
    result: OpResult = result_def()


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
