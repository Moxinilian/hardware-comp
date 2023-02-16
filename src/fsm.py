from typing import Annotated
from xdsl.irdl import irdl_op_definition, irdl_attr_definition, AnyAttr, Operand, OpAttr
from xdsl.ir import ParametrizedAttribute, MLIRType, Dialect, Operation, OpResult, Attribute, Region
from xdsl.dialects.builtin import (StringAttr, ArrayAttr, SymbolRefAttr,
                                   DictionaryAttr, i1)

# todo: interfaces, traits, region constraints


@irdl_attr_definition
class FsmInstanceType(ParametrizedAttribute, MLIRType):
    name = "fsm.instance"


@irdl_op_definition
class FsmHwInstance(Operation):
    name = "fsm.hw_instance"

    sym_name: OpAttr[StringAttr]
    machine: OpAttr[SymbolRefAttr]  # todo: flat constraint
    inputs: Annotated[Operand, AnyAttr()]  # todo: MLIR type constraint
    clock: Annotated[Operand, i1]
    reset: Annotated[Operand, i1]
    outputs: Annotated[OpResult, AnyAttr()]  # todo: MLIR type constraint


@irdl_op_definition
class FsmInstance(Operation):
    name = "fsm.instance"

    sym_name: OpAttr[StringAttr]
    machine: OpAttr[SymbolRefAttr]  # todo: flat constraint
    outputs: Annotated[OpResult, FsmInstanceType]


@irdl_op_definition
class FsmMachine(Operation):
    name = "fsm.machine"

    sym_name: OpAttr[StringAttr]
    initial_state: OpAttr[StringAttr]
    function_type: OpAttr[Attribute]  # todo: MLIR type constraint
    arg_attrs: OpAttr[ArrayAttr[DictionaryAttr]]
    res_attrs: OpAttr[ArrayAttr[DictionaryAttr]]
    arg_names: OpAttr[ArrayAttr[StringAttr]]
    res_names: OpAttr[ArrayAttr[StringAttr]]

    body: Region


@irdl_op_definition
class FsmOutput(Operation):
    name = "fsm.output"

    operands: Annotated[Operand, AnyAttr()]


@irdl_op_definition
class FsmReturn(Operation):
    name = "fsm.return"

    operand: Annotated[Operand, i1]


@irdl_op_definition
class FsmState(Operation):
    name = "fsm.state"

    sym_name: OpAttr[StringAttr]

    output: Region
    transitions: Region


@irdl_op_definition
class FsmTransition(Operation):
    name = "fsm.transition"

    next_state: OpAttr[SymbolRefAttr]  # todo: flat constraint

    guard: Region
    action: Region


@irdl_op_definition
class FsmTrigger(Operation):
    name = "fsm.trigger"

    inputs: Annotated[Operand, AnyAttr()]
    instance: Annotated[Operand, FsmInstanceType]
    outputs: OpResult


@irdl_op_definition
class FsmUpdate(Operation):
    name = "fsm.update"

    variable: Annotated[Operand, AnyAttr()]
    value: Annotated[Operand, AnyAttr()]


@irdl_op_definition
class FsmVariable(Operation):
    name = "fsm.variable"

    init_value: OpAttr[Attribute]
    name: OpAttr[StringAttr]
    result: OpResult


Fsm = Dialect([
    FsmHwInstance, FsmInstance, FsmMachine, FsmOutput, FsmReturn, FsmState,
    FsmTransition, FsmTrigger, FsmUpdate, FsmVariable
], [FsmInstanceType])
