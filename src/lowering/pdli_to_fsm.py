from dataclasses import dataclass, field
from typing import Tuple, Union

from xdsl.ir import Region, SSAValue, Block
from xdsl.dialects.builtin import IntegerType, i1, IntegerAttr, FunctionType
from xdsl.parser import ArrayAttr

from analysis.pattern_dag_span import OperandSpan, ResultSpan

from dialects.fsm import (
    FsmMachine,
    FsmOutput,
    FsmReturn,
    FsmState,
    FsmTransition,
    FsmVariable,
)
from dialects.hw import HwConstant, HwModule, HwOutput
from dialects.hw_op import (
    HwOp,
    HwOpIsOperation,
    HwOpOperandTypeIs,
    HwOpResultTypeIs,
    HwOperation,
    HwOpGetOperandOffset,
    HwOpHasOperand,
    HwOpHasResult,
    HwOpOperandAmountIs,
)
from dialects.hw_sum import HwSumType, HwSumCreate, HwSumIs, HwSumGetAs
from dialects.pdl_interp import (
    PdlInterpCheckOperandCount,
    PdlInterpFinalize,
    PdlInterpIsNotNull,
    PdlInterpRecordMatch,
    PdlInterpSwitchOperandCount,
    PdlInterpSwitchOperationName,
    PdlInterpSwitchResultCount,
    PdlInterpSwitchType,
    PdlInterpSwitchTypes,
    PdlInterpAreEqual,
    PdlInterpCheckResultCount,
)
from dialects.seq import SeqCompregCe
from dialects.comb import *

from analysis.pattern_dag_span import (
    OperationSpan,
    OperationSpanCtx,
    compute_usage_graph,
)
from encoder import EncodingContext, OperationContext
from utils import UnsupportedPatternFeature

import math

STATE_FAILURE_NAME = "STATEFAILURE"


@dataclass
class FsmContext:
    """
    Context for the generation of FSM from PDL-Interp regions.
    Each block of the region is turned into an FSM state.
    """

    """
    Maps a block to the name of its generated state, if it exists.
    """
    block_to_state: dict[Block, str] = field(default_factory=dict)

    """
    Counter for block names.
    """
    state_namer: int = 0

    def get_state_name_of(self, block: Block):
        if not block in self.block_to_state:
            self.state_namer += 1
            self.block_to_state[block] = f"STATE{self.state_namer - 1}"
        return self.block_to_state[block]


@dataclass
class DagBufferNode:
    """
    Represents a node of the DAG buffer, storing an operation.

    Field:
    - data: contains the data currently stored in the buffer node. Can be either:
        + `unknown`: represents that an operation may come to the register at one point.
        + `located_at(operand_offset)`: represents that an operation may come, and shows
          the distance left before it comes (or not).
        + `found(HwOperation)`: exposes data about an operand that arrived in this node.
        + `never`: guarantees that an operation will never reach this node during the
          current matching attempt.
    - store_operands_at: maps to which DagBufferNode the defining operation of
                         operands of the currently stored operation will be
                         stored.
    """

    data: SSAValue
    store_operands_at: dict[int, "DagBufferNode"] = field(default_factory=dict)

    def __hash__(self):
        return hash(str(self))


@dataclass
class DagBufferCtx:
    """
    Resolves to which dag buffer node an operation span value refers to.
    """

    nodes: list[DagBufferNode] = field(default_factory=list)
    span_to_dag: dict[OperationSpan, DagBufferNode] = field(default_factory=dict)


PathToOperationSpan = list[OperandSpan]


def _paths_to_common_ancestor(
    lhs: OperationSpan, rhs: OperationSpan, root: OperationSpan
) -> Tuple[PathToOperationSpan, PathToOperationSpan]:
    """
    Compute the sequence of operand spans to go through to reach each operand starting
    from their last common ancestor. Starting from their last common operand, the last
    operand span of the list is the operand to unstack next, in order. Once the list is
    empty, the current operation span should be respectively lhs and rhs.
    """

    @dataclass
    class FoundBoth:
        left: PathToOperationSpan
        right: PathToOperationSpan

    @dataclass
    class FoundLeft:
        path: PathToOperationSpan

    @dataclass
    class FoundRight:
        path: PathToOperationSpan

    @dataclass
    class FoundNothing:
        pass

    def compute_path(
        current: OperationSpan,
    ) -> Union[FoundBoth, FoundLeft, FoundRight, FoundNothing]:
        left: FoundLeft | None = FoundLeft([]) if lhs == current else None
        right: FoundRight | None = FoundRight([]) if rhs == current else None
        for operand in current.operands.values():
            if left and right:
                break
            res = compute_path(operand.defining_op)
            if isinstance(res, FoundBoth):
                return res
            if isinstance(res, FoundLeft):
                res.path.append(operand)
                left = res
            if isinstance(res, FoundRight):
                res.path.append(operand)
                right = res
        if left and right:
            return FoundBoth(left.path, right.path)
        if left:
            return left
        if right:
            return right
        return FoundNothing()

    root_res = compute_path(root)
    # The root element is a common ancestor of lhs and rhs.
    assert isinstance(root_res, FoundBoth)
    return root_res.left, root_res.right


def _sum_path(
    block: Block,
    path: PathToOperationSpan,
    max_path_len: int,
    dag_buffer_ctx: DagBufferCtx,
    dag_buffer_node_access: dict[DagBufferNode, SSAValue],
    enc_ctx: EncodingContext,
) -> SSAValue:
    """
    Compute the offset in the operation stream between the beginning
    and the end of the provided path. `max_path_len` specifies the
    maximum length of paths against which this sum will be compared,
    and is used to determine the type of the result value.
    All operations in the path must be ready to use. This can be easily
    checked by verifying the last operation is ready.
    """
    assert len(path) <= max_path_len
    overflow_margin = math.ceil(math.log2(max_path_len))
    result_bitwidth = overflow_margin + enc_ctx.operand_offset_width
    if len(path) == 0:
        zero = HwConstant.from_attr(IntegerAttr.from_int_and_width(0, result_bitwidth))
        block.add_op(zero)
        return zero.output
    zero_padding = None
    if overflow_margin != 0:
        zero_padding = HwConstant.from_attr(
            IntegerAttr.from_int_and_width(0, overflow_margin)
        )
        block.add_op(zero_padding)

    to_sum = []
    for operand in path:
        dag_buffer_node = dag_buffer_ctx.span_to_dag[operand.operand_of]
        unwrap_op = HwSumGetAs.from_variant(
            dag_buffer_node_access[dag_buffer_node], "found"
        )
        block.add_op(unwrap_op)
        op_offset = HwOpGetOperandOffset.from_operand(
            unwrap_op.output, operand.operand_index
        )
        block.add_op(op_offset)
        adjusted_offset: SSAValue = op_offset.output
        if overflow_margin != 0:
            assert zero_padding
            concat = CombConcat.from_values([zero_padding.output, op_offset.output])
            block.add_op(concat)
            adjusted_offset = concat.output
        to_sum.append(adjusted_offset)
    summed = CombAdd.from_values(to_sum)
    block.add_op(summed)
    return summed.result


def _are_equal_values(
    fsm_ctx: FsmContext,
    dest: Block,
    lhs_blocker: OperationSpan,
    lhs_defining_op: OperationSpan,
    rhs_blocker: OperationSpan,
    rhs_defining_op: OperationSpan,
    dag_span_ctx: OperationSpanCtx,
    dag_buffer_ctx: DagBufferCtx,
    dag_buffer_node_access: dict[DagBufferNode, SSAValue],
    enc_ctx: EncodingContext,
) -> FsmTransition:
    block = Block()
    lhs_path, rhs_path = _paths_to_common_ancestor(
        lhs_defining_op,
        rhs_defining_op,
        dag_span_ctx.root,
    )
    max_path_len = max(len(lhs_path), len(rhs_path))
    lhs_sum = _sum_path(
        block,
        lhs_path,
        max_path_len,
        dag_buffer_ctx,
        dag_buffer_node_access,
        enc_ctx,
    )
    rhs_sum = _sum_path(
        block,
        lhs_path,
        max_path_len,
        dag_buffer_ctx,
        dag_buffer_node_access,
        enc_ctx,
    )
    cmp_sum = CombICmp.from_values(lhs_sum, rhs_sum, ICmpPredicate.EQ)
    block.add_op(cmp_sum)
    lhs_found = HwSumIs.from_variant(
        dag_buffer_node_access[dag_buffer_ctx.span_to_dag[lhs_blocker]],
        "found",
    )
    block.add_op(lhs_found)
    rhs_found = HwSumIs.from_variant(
        dag_buffer_node_access[dag_buffer_ctx.span_to_dag[rhs_blocker]],
        "found",
    )
    block.add_op(rhs_found)
    are_equal = CombAnd.from_values(
        [lhs_found.output, rhs_found.output, cmp_sum.output]
    )
    block.add_op(are_equal)
    block_return = FsmReturn.from_value(are_equal.result)
    block.add_op(block_return)
    return FsmTransition.new(
        fsm_ctx.get_state_name_of(dest),
        block,
        Block(),
    )


def _find_user_of_result(
    result: ResultSpan, user: OperationSpan
) -> OperationSpan | None:
    for operand in user.operands.values():
        if operand.defining_op == result.result_of:
            return user
        res = _find_user_of_result(result, operand.defining_op)
        if res:
            return res
    return None


def generate_fsm(
    pdli_region: Region,
    dag_span_ctx: OperationSpanCtx,
    dag_buffer_ctx: DagBufferCtx,
    enc_ctx: EncodingContext,
    fsm_name: str,
    node_sum_type: HwSumType,
    status_sum_type: HwSumType,
) -> FsmMachine:
    ctx = FsmContext()
    fsm_block = Block(arg_types=[node_sum_type] * len(dag_buffer_ctx.nodes))

    dag_buffer_node_access = {
        node: cast(SSAValue, ssa_val)
        for node, ssa_val in zip(dag_buffer_ctx.nodes, fsm_block.args)
    }

    # Prepare possible ouputs:
    true = HwConstant.from_attr(IntegerAttr.from_int_and_width(1, 1))
    fsm_block.add_op(true)
    false = HwConstant.from_attr(IntegerAttr.from_int_and_width(0, 1))
    fsm_block.add_op(false)
    unknown_status = HwSumCreate.from_data(status_sum_type, "unknown", true.output)
    fsm_block.add_op(unknown_status)
    success_status = HwSumCreate.from_data(status_sum_type, "success", true.output)
    fsm_block.add_op(success_status)
    failure_status = HwSumCreate.from_data(status_sum_type, "failure", true.output)
    fsm_block.add_op(failure_status)

    # Create a failure ssink state for all conditional failures.
    state_failure_block = Block()
    status_out = FsmOutput.from_output([failure_status.output])
    state_failure_block.add_op(status_out)
    fsm_block.add_op(FsmState.new(STATE_FAILURE_NAME, state_failure_block, Block()))

    for block in pdli_region.blocks:
        state_output_block = Block()
        transitions_block = Block()

        match block.last_op:
            case PdlInterpFinalize():
                # If a finalize is reached before a record match, output failure.
                status_out = FsmOutput.from_output([failure_status.output])
                state_output_block.add_op(status_out)
                # No transition after finalize.
            case PdlInterpIsNotNull(
                value=value, true_dest=true_dest, false_dest=false_dest
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if (
                    value in dag_span_ctx.value_of_operand
                    or value in dag_span_ctx.type_of_operand
                ):
                    if value in dag_span_ctx.value_of_operand:
                        operand = dag_span_ctx.value_of_operand[value]
                    else:
                        operand = dag_span_ctx.type_of_operand[value]
                    operand_dag_node = dag_buffer_node_access[
                        dag_buffer_ctx.span_to_dag[operand.operand_of]
                    ]
                    # If the operation is found and it has the wanted operand, then move to true_dest.
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operand_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operand_dag_node, "found")
                    true_trans_guard_block.add_op(unwrap_op)
                    has_operand = HwOpHasOperand.from_operand(
                        unwrap_op.output, operand.operand_index
                    )
                    true_trans_guard_block.add_op(has_operand)
                    is_not_null = CombAnd.from_values(
                        [is_found.output, has_operand.output]
                    )
                    true_trans_guard_block.add_op(is_not_null)
                    true_trans_return = FsmReturn.from_value(is_not_null.result)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(true_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                    # If the operation is found and the previous transition
                    # was not taken, then move to false_dest.
                    false_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operand_dag_node, "found")
                    false_trans_guard_block.add_op(is_found)
                    is_never = HwSumIs.from_variant(operand_dag_node, "never")
                    false_trans_guard_block.add_op(is_never)
                    is_null = CombOr.from_values([is_found.output, is_never.output])
                    false_trans_guard_block.add_op(is_null)
                    false_trans_return = FsmReturn.from_value(is_null.result)
                    false_trans_guard_block.add_op(false_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(false_dest),
                            false_trans_guard_block,
                            Block(),
                        )
                    )
                elif (
                    value in dag_span_ctx.value_of_result
                    or value in dag_span_ctx.type_of_result
                ):
                    if value in dag_span_ctx.value_of_result:
                        result = dag_span_ctx.value_of_result[value]
                    else:
                        result = dag_span_ctx.type_of_result[value]
                    result_dag_node = dag_buffer_node_access[
                        dag_buffer_ctx.span_to_dag[result.result_of]
                    ]
                    # If the operation is found and has a result, then move to true_dest.
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(result_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(result_dag_node, "found")
                    true_trans_guard_block.add_op(unwrap_op)
                    has_result = HwOpHasResult.from_operand(unwrap_op.output)
                    true_trans_guard_block.add_op(has_result)
                    is_not_null = CombAnd.from_values(
                        [is_found.output, has_result.output]
                    )
                    true_trans_guard_block.add_op(is_not_null)
                    true_trans_return = FsmReturn.from_value(is_not_null.result)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(true_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                    # If the operation is found or will never come and the previous transition
                    # was not taken, then move to false_dest.
                    false_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(result_dag_node, "found")
                    false_trans_guard_block.add_op(is_found)
                    is_never = HwSumIs.from_variant(result_dag_node, "never")
                    false_trans_guard_block.add_op(is_never)
                    is_null = CombOr.from_values([is_found.output, is_never.output])
                    false_trans_guard_block.add_op(is_null)
                    false_trans_return = FsmReturn.from_value(is_null.result)
                    false_trans_guard_block.add_op(false_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(false_dest),
                            false_trans_guard_block,
                            Block(),
                        )
                    )
                elif (
                    value in dag_span_ctx.operations
                    or value in dag_span_ctx.operand_range_of
                    or value in dag_span_ctx.operand_type_range_of
                    or value in dag_span_ctx.result_range_of
                    or value in dag_span_ctx.result_type_range_of
                ):
                    find_in = next(
                        x
                        for x in [
                            dag_span_ctx.operations,
                            dag_span_ctx.operand_range_of,
                            dag_span_ctx.operand_type_range_of,
                            dag_span_ctx.result_range_of,
                            dag_span_ctx.result_type_range_of,
                        ]
                        if value in x
                    )
                    operation_dag_node = dag_buffer_node_access[
                        dag_buffer_ctx.span_to_dag[find_in[value]]
                    ]
                    # If the operation is found, move to true_dest
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    true_trans_return = FsmReturn.from_value(is_found.output)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(true_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                    # If the operation is never coming, move to false_dest
                    false_trans_guard_block = Block()
                    is_never = HwSumIs.from_variant(operation_dag_node, "never")
                    false_trans_guard_block.add_op(is_never)
                    false_trans_return = FsmReturn.from_value(is_never.output)
                    false_trans_guard_block.add_op(false_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(false_dest),
                            false_trans_guard_block,
                            Block(),
                        )
                    )
                else:
                    raise UnsupportedPatternFeature(block.last_op)

            case PdlInterpRecordMatch(dest=dest):
                # If a match is recorded, this means success.
                status_out = FsmOutput.from_output([success_status.output])
                state_output_block.add_op(status_out)
                # No transition after record match, as the output will not change.

            case PdlInterpCheckOperandCount(
                count=count,
                compare_at_least=compare_at_least,
                input_op=input_op,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if not input_op in dag_span_ctx.operations:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[dag_span_ctx.operations[input_op]]
                ]
                # If the operation is found and has the amount of operands requested,
                # then move to true_dest.
                true_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                true_trans_guard_block.add_op(is_found)
                unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                true_trans_guard_block.add_op(unwrap_op)
                is_amount_value: SSAValue
                if compare_at_least:
                    if count.value.data <= 0:
                        is_amount_value = true.output
                    else:
                        is_amount_at_least = HwOpHasOperand.from_operand(
                            unwrap_op.output, count.value.data - 1
                        )
                        true_trans_guard_block.add_op(is_amount_at_least)
                        is_amount_value = is_amount_at_least.output
                else:
                    is_amount = HwOpOperandAmountIs.from_operand(
                        unwrap_op.output, count.value.data
                    )
                    true_trans_guard_block.add_op(is_amount)
                    is_amount_value = is_amount.output
                is_case_valid = CombAnd.from_values([is_found.output, is_amount_value])
                true_trans_guard_block.add_op(is_case_valid)
                true_trans_return = FsmReturn.from_value(is_case_valid.result)
                true_trans_guard_block.add_op(true_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(true_dest),
                        true_trans_guard_block,
                        Block(),
                    )
                )
                # If the operation is found or will never come and the previous transitions
                # were not taken, then move to false_dest.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(false_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpSwitchOperandCount(
                input_op=input_op,
                case_values=case_values,
                cases=cases,
                default_dest=default_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if not input_op in dag_span_ctx.operations:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[dag_span_ctx.operations[input_op]]
                ]
                for case, case_dest in zip(case_values.data, cases):
                    # If the operation is found and has the amount of operands requested,
                    # then move to case_dest.
                    if not isinstance(case, IntegerAttr):
                        raise UnsupportedPatternFeature(block.last_op)
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(unwrap_op)
                    is_amount = HwOpOperandAmountIs.from_operand(
                        unwrap_op.output, case.value.data
                    )
                    true_trans_guard_block.add_op(is_amount)
                    is_case_valid = CombAnd.from_values(
                        [is_found.output, is_amount.output]
                    )
                    true_trans_guard_block.add_op(is_case_valid)
                    true_trans_return = FsmReturn.from_value(is_case_valid.result)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(case_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                # If the operation is found or will never come and the previous transitions
                # were not taken, then move to default_dest.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(default_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpSwitchOperationName(
                input_op=input_op,
                case_values=case_values,
                cases=cases,
                default_dest=default_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if not input_op in dag_span_ctx.operations:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[dag_span_ctx.operations[input_op]]
                ]
                for case, case_dest in zip(case_values.data, cases):
                    # If the operation is found and is the expected operation,
                    # then move to case_dest.
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(unwrap_op)
                    is_right_op = HwOpIsOperation.from_operand(
                        unwrap_op.output, case.data
                    )
                    true_trans_guard_block.add_op(is_right_op)
                    is_case_valid = CombAnd.from_values(
                        [is_found.output, is_right_op.output]
                    )
                    true_trans_guard_block.add_op(is_case_valid)
                    true_trans_return = FsmReturn.from_value(is_case_valid.result)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(case_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                # If the operation is found or will never come and the previous transitions
                # were not taken, then move to default_dest.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(default_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpCheckResultCount(
                count=count,
                compare_at_least=compare_at_least,
                input_op=input_op,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if not input_op in dag_span_ctx.operations:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[dag_span_ctx.operations[input_op]]
                ]
                # If the operation is found and has the amount of results requested,
                # then move to true_dest.
                true_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                true_trans_guard_block.add_op(is_found)
                is_expected_amount: SSAValue
                if compare_at_least:
                    if count.value.data <= 0:
                        is_expected_amount = true.output
                    elif count.value.data > 1:
                        is_expected_amount = false.output
                    else:
                        has_result = HwOpHasResult.from_operand(input_op)
                        true_trans_guard_block.add_op(has_result)
                        is_expected_amount = has_result.output
                else:
                    if count.value.data == 0:
                        has_result = HwOpHasResult.from_operand(input_op)
                        true_trans_guard_block.add_op(has_result)
                        has_no_result = CombXor.from_values(
                            [has_result.output, true.output]
                        )
                        true_trans_guard_block.add_op(has_no_result)
                        is_expected_amount = has_no_result.result
                    elif count.value.data == 1:
                        has_result = HwOpHasResult.from_operand(input_op)
                        true_trans_guard_block.add_op(has_result)
                        is_expected_amount = has_result.output
                    else:
                        is_expected_amount = false.output
                is_true = CombAnd.from_values([is_found.output, is_expected_amount])
                true_trans_guard_block.add_op(is_true)
                default_trans_return = FsmReturn.from_value(is_true.result)
                true_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(true_dest),
                        true_trans_guard_block,
                        Block(),
                    )
                )
                # If the operation is found or will never come and the previous transitions
                # were not taken, then move to default_dest.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(false_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpSwitchResultCount(
                input_op=input_op,
                case_values=case_values,
                cases=cases,
                default_dest=default_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if not input_op in dag_span_ctx.operations:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[dag_span_ctx.operations[input_op]]
                ]
                target_for_zero = next(
                    (
                        cases[i]
                        for i, x in enumerate(case_values.data)
                        if x.value.data == 0
                    ),
                    default_dest,
                )
                target_for_one = next(
                    (
                        cases[i]
                        for i, x in enumerate(case_values.data)
                        if x.value.data == 1
                    ),
                    default_dest,
                )
                # If the case for zero is not the default case, handle it.
                if target_for_zero != default_dest:
                    zero_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    zero_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                    zero_trans_guard_block.add_op(unwrap_op)
                    has_result = HwOpHasResult.from_operand(unwrap_op.output)
                    zero_trans_guard_block.add_op(has_result)
                    has_no_result = CombXor.from_values(
                        [has_result.output, true.output]
                    )
                    zero_trans_guard_block.add_op(has_no_result)
                    is_case_valid = CombAnd.from_values(
                        [is_found.output, has_no_result.result]
                    )
                    zero_trans_guard_block.add_op(is_case_valid)
                    zero_trans_return = FsmReturn.from_value(is_case_valid.result)
                    zero_trans_guard_block.add_op(zero_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(target_for_zero),
                            zero_trans_guard_block,
                            Block(),
                        )
                    )
                # If the case for one is not the default case, handle it.
                if target_for_one != default_dest:
                    one_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    one_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                    one_trans_guard_block.add_op(unwrap_op)
                    has_result = HwOpHasResult.from_operand(unwrap_op.output)
                    one_trans_guard_block.add_op(has_result)
                    is_case_valid = CombAnd.from_values(
                        [is_found.output, has_result.output]
                    )
                    one_trans_guard_block.add_op(is_case_valid)
                    one_trans_return = FsmReturn.from_value(is_case_valid.result)
                    one_trans_guard_block.add_op(one_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(target_for_one),
                            one_trans_guard_block,
                            Block(),
                        )
                    )
                # Otherwise, if the operation is found or will never come, move to
                # the default case.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(default_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpSwitchType(
                value=value,
                case_values=case_values,
                cases=cases,
                default_dest=default_dest,
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                op_span: OperationSpan
                if value in dag_span_ctx.type_of_operand:
                    op_span = dag_span_ctx.type_of_operand[value].operand_of
                elif value in dag_span_ctx.type_of_result:
                    op_span = dag_span_ctx.type_of_result[value].result_of
                else:
                    raise UnsupportedPatternFeature(block.last_op)
                operation_dag_node = dag_buffer_node_access[
                    dag_buffer_ctx.span_to_dag[op_span]
                ]
                for case, case_dest in zip(case_values.data, cases):
                    # If the operation is found and the operand or result is of the right type,
                    # then move to case_dest.
                    true_trans_guard_block = Block()
                    is_found = HwSumIs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(is_found)
                    unwrap_op = HwSumGetAs.from_variant(operation_dag_node, "found")
                    true_trans_guard_block.add_op(unwrap_op)
                    is_right_op_value: SSAValue
                    if value in dag_span_ctx.type_of_operand:
                        is_right_op = HwOpOperandTypeIs.from_operand(
                            unwrap_op.output,
                            dag_span_ctx.type_of_operand[value].operand_index,
                            case,
                        )
                        true_trans_guard_block.add_op(is_right_op)
                        is_right_op_value = is_right_op.output
                    else:
                        is_right_op = HwOpResultTypeIs.from_operand(
                            unwrap_op.output, case
                        )
                        true_trans_guard_block.add_op(is_right_op)
                        is_right_op_value = is_right_op.output
                    is_case_valid = CombAnd.from_values(
                        [is_found.output, is_right_op_value]
                    )
                    true_trans_guard_block.add_op(is_case_valid)
                    true_trans_return = FsmReturn.from_value(is_case_valid.result)
                    true_trans_guard_block.add_op(true_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(case_dest),
                            true_trans_guard_block,
                            Block(),
                        )
                    )
                # If the operation is found or will never come and the previous transitions
                # were not taken, then move to default_dest.
                default_trans_guard_block = Block()
                is_found = HwSumIs.from_variant(operation_dag_node, "found")
                default_trans_guard_block.add_op(is_found)
                is_never = HwSumIs.from_variant(operation_dag_node, "never")
                default_trans_guard_block.add_op(is_never)
                is_null = CombOr.from_values([is_found.output, is_never.output])
                default_trans_guard_block.add_op(is_null)
                default_trans_return = FsmReturn.from_value(is_null.result)
                default_trans_guard_block.add_op(default_trans_return)
                transitions_block.add_op(
                    FsmTransition.new(
                        ctx.get_state_name_of(default_dest),
                        default_trans_guard_block,
                        Block(),
                    )
                )

            case PdlInterpSwitchTypes():
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                raise UnsupportedPatternFeature(block.last_op)  # TODO

            case PdlInterpAreEqual(
                lhs=lhs, rhs=rhs, true_dest=true_dest, false_dest=false_dest
            ):
                status_out = FsmOutput.from_output([unknown_status.output])
                state_output_block.add_op(status_out)
                if (
                    lhs in dag_span_ctx.value_of_operand
                    or lhs in dag_span_ctx.value_of_result
                ) and (
                    rhs in dag_span_ctx.value_of_operand
                    or rhs in dag_span_ctx.value_of_result
                ):
                    # If two values need to be compared, compare the offset between
                    # them and their last common ancestor of the two values.
                    if lhs in dag_span_ctx.value_of_operand:
                        lhs_operand = dag_span_ctx.value_of_operand[lhs]
                        lhs_blocker = lhs_operand.operand_of
                        if rhs in dag_span_ctx.value_of_operand:
                            rhs_operand = dag_span_ctx.value_of_operand[rhs]
                            rhs_blocker = rhs_operand.operand_of
                            transitions_block.add_op(
                                _are_equal_values(
                                    ctx,
                                    true_dest,
                                    lhs_operand.operand_of,
                                    lhs_blocker,
                                    rhs_operand.operand_of,
                                    rhs_blocker,
                                    dag_span_ctx,
                                    dag_buffer_ctx,
                                    dag_buffer_node_access,
                                    enc_ctx,
                                )
                            )
                        else:
                            rhs_result = dag_span_ctx.value_of_result[rhs]
                            rhs_blocker = (
                                _find_user_of_result(rhs_result, dag_span_ctx.root)
                                or rhs_result.result_of
                            )
                            transitions_block.add_op(
                                _are_equal_values(
                                    ctx,
                                    true_dest,
                                    lhs_operand.operand_of,
                                    lhs_blocker,
                                    rhs_result.result_of,
                                    rhs_blocker,
                                    dag_span_ctx,
                                    dag_buffer_ctx,
                                    dag_buffer_node_access,
                                    enc_ctx,
                                )
                            )
                    else:
                        lhs_result = dag_span_ctx.value_of_result[lhs]
                        lhs_blocker = (
                            _find_user_of_result(lhs_result, dag_span_ctx.root)
                            or lhs_result.result_of
                        )
                        if rhs in dag_span_ctx.value_of_operand:
                            rhs_operand = dag_span_ctx.value_of_operand[rhs]
                            rhs_blocker = rhs_operand.defining_op
                            transitions_block.add_op(
                                _are_equal_values(
                                    ctx,
                                    true_dest,
                                    lhs_result.result_of,
                                    lhs_blocker,
                                    rhs_operand.operand_of,
                                    rhs_blocker,
                                    dag_span_ctx,
                                    dag_buffer_ctx,
                                    dag_buffer_node_access,
                                    enc_ctx,
                                )
                            )
                        else:
                            rhs_result = dag_span_ctx.value_of_result[rhs]
                            rhs_blocker = (
                                _find_user_of_result(rhs_result, dag_span_ctx.root)
                                or rhs_result.result_of
                            )
                            transitions_block.add_op(
                                _are_equal_values(
                                    ctx,
                                    true_dest,
                                    lhs_result.result_of,
                                    lhs_blocker,
                                    rhs_result.result_of,
                                    rhs_blocker,
                                    dag_span_ctx,
                                    dag_buffer_ctx,
                                    dag_buffer_node_access,
                                    enc_ctx,
                                )
                            )
                    print(block.last_op)
                    lhs_blocker_dag_node = dag_buffer_node_access[
                        dag_buffer_ctx.span_to_dag[lhs_blocker]
                    ]
                    rhs_blocker_dag_node = dag_buffer_node_access[
                        dag_buffer_ctx.span_to_dag[rhs_blocker]
                    ]
                    # If both blockers are found or one of the blockers is never coming,
                    # move to false_dest.
                    false_trans_guard_block = Block()
                    found_lhs_blocker = HwSumIs.from_variant(
                        lhs_blocker_dag_node, "found"
                    )
                    false_trans_guard_block.add_op(found_lhs_blocker)
                    found_rhs_blocker = HwSumIs.from_variant(
                        rhs_blocker_dag_node, "found"
                    )
                    false_trans_guard_block.add_op(found_rhs_blocker)
                    never_lhs_blocker = HwSumIs.from_variant(
                        lhs_blocker_dag_node, "never"
                    )
                    false_trans_guard_block.add_op(never_lhs_blocker)
                    never_rhs_blocker = HwSumIs.from_variant(
                        rhs_blocker_dag_node, "never"
                    )
                    false_trans_guard_block.add_op(never_rhs_blocker)
                    found_both = CombAnd.from_values(
                        [found_lhs_blocker.output, found_rhs_blocker.output]
                    )
                    false_trans_guard_block.add_op(found_both)
                    is_false = CombOr.from_values(
                        [
                            found_both.result,
                            never_lhs_blocker.output,
                            never_rhs_blocker.output,
                        ]
                    )
                    false_trans_guard_block.add_op(is_false)
                    false_trans_return = FsmReturn.from_value(is_false.result)
                    false_trans_guard_block.add_op(false_trans_return)
                    transitions_block.add_op(
                        FsmTransition.new(
                            ctx.get_state_name_of(false_dest),
                            false_trans_guard_block,
                            Block(),
                        )
                    )

                else:
                    raise UnsupportedPatternFeature(block.last_op)

            case op:
                raise UnsupportedPatternFeature(op)

        # Finally, build the state operation
        state_op = FsmState.new(
            ctx.get_state_name_of(block), state_output_block, transitions_block
        )
        fsm_block.add_op(state_op)

    # Finally, build the FSM machine operation
    return FsmMachine.new(
        fsm_name,
        "STATE0",
        FunctionType.from_attrs(
            ArrayAttr([x.typ for x in fsm_block.args]), ArrayAttr([status_sum_type])
        ),
        fsm_block,
    )
