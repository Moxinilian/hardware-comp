from dataclasses import dataclass, field
from typing import Tuple
from attr import has

from xdsl.ir import Region, SSAValue, Block
from xdsl.dialects.builtin import IntegerType, i1, IntegerAttr, FunctionType
from xdsl.parser import ArrayAttr

from dialects.fsm import (
    FsmHwInstance,
    FsmMachine,
    FsmOutput,
    FsmReturn,
    FsmState,
    FsmTransition,
    FsmVariable,
)
from dialects.hw import HwConstant, HwModule, HwOutput
from dialects.hw_op import HwOp, HwOperation, HwOpGetOperandOffset, HwOpHasOperand
from dialects.hw_sum import HwSumType, HwSumCreate, HwSumIs, HwSumGetAs
from dialects.pdl_interp import PdlInterpFinalize, PdlInterpIsNotNull
from dialects.seq import SeqCompregCe
from dialects.comb import *

from lowering.pdli_to_fsm import *

from analysis.pattern_dag_span import (
    OperationSpan,
    OperationSpanCtx,
    compute_usage_graph,
)
from encoder import EncodingContext, OperationContext

# TODO: Fix HwSum lowering to remove dummy i1s


@dataclass
class FillerNodeOutput:
    output: SSAValue
    write_to_out: SSAValue  # all operands share the same write_to
    write_val_out: dict[int, SSAValue]


@dataclass
class MatcherUnitInputs:
    clock: SSAValue
    input_op: SSAValue
    is_stream_paused: SSAValue
    new_sequence: SSAValue
    stream_completed: SSAValue


def build_filler_node(
    matcher_unit_inputs: MatcherUnitInputs,
    default_value: SSAValue,
    write_to: SSAValue,
    write_val: SSAValue,
    block: Block,
    operands: list[int],
    enc_ctx: EncodingContext,
    node_name: str,
) -> FillerNodeOutput:
    sum_type = cast(HwSumType, default_value.typ)

    # Register declaration
    true = HwConstant.from_attr(IntegerAttr.from_int_and_width(1, 1))
    block.add_op(true)
    is_stream_running = CombXor.from_values(
        [matcher_unit_inputs.is_stream_paused, true.output]
    )
    block.add_op(is_stream_running)
    register = SeqCompregCe.new(
        "register_" + node_name,
        sum_type,
        default_value,  # input is defined later, use default_value as dummy
        matcher_unit_inputs.clock,
        is_stream_running.result,
        matcher_unit_inputs.new_sequence,
        default_value,
    )
    block.add_op(register)

    # Sum type variant checks
    is_never = HwSumIs.from_variant(register.data, "never")
    block.add_op(is_never)
    is_located_at = HwSumIs.from_variant(register.data, "located_at")
    block.add_op(is_located_at)
    is_found = HwSumIs.from_variant(register.data, "found")
    block.add_op(is_found)

    # Constants
    offset_zero = HwConstant.from_attr(
        IntegerAttr.from_int_and_width(0, enc_ctx.operand_offset_width)
    )
    block.add_op(offset_zero)
    offset_one = HwConstant.from_attr(
        IntegerAttr.from_int_and_width(1, enc_ctx.operand_offset_width)
    )
    block.add_op(offset_one)

    # Located at content and derivatives
    get_located_at = HwSumGetAs.from_variant(register.data, "located_at")
    block.add_op(get_located_at)
    located_at_content_is_zero = CombICmp.from_values(
        get_located_at.output, offset_zero.output, ICmpPredicate.EQ
    )
    block.add_op(located_at_content_is_zero)
    located_at_content_decr = CombSub.from_values(
        get_located_at.output, offset_one.output
    )
    block.add_op(located_at_content_decr)
    is_located_at_zero = CombAnd.from_values(
        [is_located_at.output, located_at_content_is_zero.output]
    )
    block.add_op(is_located_at_zero)

    # Inputs for muxers
    found_input_op = HwSumCreate.from_data(
        sum_type, "found", matcher_unit_inputs.input_op
    )
    block.add_op(found_input_op)
    located_at_decr = HwSumCreate.from_data(
        sum_type, "located_at", located_at_content_decr.result
    )
    block.add_op(located_at_decr)
    constant_never = HwSumCreate.from_data(sum_type, "never", true.output)
    block.add_op(constant_never)

    # Muxers
    decr_muxer = CombMux.from_values(
        is_located_at.output, located_at_decr.output, register.data
    )
    block.add_op(decr_muxer)
    stream_end_muxer = CombMux.from_values(
        matcher_unit_inputs.stream_completed, constant_never.output, decr_muxer.result
    )
    block.add_op(stream_end_muxer)
    found_muxer = CombMux.from_values(
        is_found.output, register.data, stream_end_muxer.result
    )
    block.add_op(found_muxer)
    located_at_zero_muxer = CombMux.from_values(
        is_located_at_zero.result, found_input_op.output, found_muxer.result
    )
    block.add_op(located_at_zero_muxer)
    write_to_muxer = CombMux.from_values(
        write_to, write_val, located_at_zero_muxer.result
    )
    block.add_op(write_to_muxer)

    # The input for the register is now ready, set it.
    register.replace_operand(0, write_to_muxer.result)

    # Finally, schedule updates for operands when an op is received or when the current op is never.
    should_write_to = CombOr.from_values([is_never.output, is_located_at_zero.result])
    block.add_op(should_write_to)
    write_val_operands: dict[int, SSAValue] = dict()
    for operand in operands:
        has_operand = HwOpHasOperand.from_operand(matcher_unit_inputs.input_op, operand)
        block.add_op(has_operand)
        operand_offset = HwOpGetOperandOffset.from_operand(
            matcher_unit_inputs.input_op, operand
        )
        block.add_op(operand_offset)
        wrapped_operand_offset = HwSumCreate.from_data(
            sum_type, "located_at", operand_offset.output
        )
        block.add_op(wrapped_operand_offset)
        should_write_offset = CombAnd.from_values(
            [has_operand.output, is_located_at_zero.result]
        )
        block.add_op(should_write_offset)
        write_val_muxer = CombMux.from_values(
            should_write_offset.result,
            wrapped_operand_offset.output,
            constant_never.output,
        )
        block.add_op(write_val_muxer)
        write_val_operands[operand] = write_val_muxer.result

    return FillerNodeOutput(register.data, should_write_to.result, write_val_operands)


def create_filler(
    span: OperationSpan,
    block: Block,
    matcher_unit_inputs: MatcherUnitInputs,
    matcher_unit_name: str,
    node_sum_type: HwSumType,
    enc_ctx: EncodingContext,
) -> DagBufferCtx:
    name_counter = 0

    false = HwConstant.from_attr(IntegerAttr.from_int_and_width(0, 1))
    block.add_op(false)
    constant_unknown = HwSumCreate.from_data(node_sum_type, "unknown", false.output)
    block.add_op(constant_unknown)
    constant_never = HwSumCreate.from_data(node_sum_type, "never", false.output)
    block.add_op(constant_never)

    ctx = DagBufferCtx()

    def register_in_ctx(node: DagBufferNode, span: OperationSpan) -> DagBufferNode:
        ctx.nodes.append(node)
        ctx.span_to_dag[span] = node
        return node

    def construct_node(
        span: OperationSpan,
        default_value: SSAValue,
        write_to: SSAValue,
        write_val: SSAValue,
    ) -> DagBufferNode:
        nonlocal name_counter
        operands = list(
            filter(lambda x: span.operands[x].defining_op.used, span.operands.keys())
        )
        filler: FillerNodeOutput = build_filler_node(
            matcher_unit_inputs,
            default_value,
            write_to,
            write_val,
            block,
            operands,
            enc_ctx,
            f"{matcher_unit_name}_dag_buffer_{name_counter}",
        )
        name_counter += 1

        store_operands_at: dict[int, "DagBufferNode"] = dict()
        for operand in operands:
            operand_node = construct_node(
                span.operands[operand].defining_op,
                constant_unknown.output,
                filler.write_to_out,
                filler.write_val_out[operand],
            )
            store_operands_at[operand] = operand_node
        return register_in_ctx(DagBufferNode(filler.output, store_operands_at), span)

    found_input_op = HwSumCreate.from_data(
        node_sum_type, "found", matcher_unit_inputs.input_op
    )
    block.add_op(found_input_op)

    # The root and its immediate operands have special-cased
    # default values that must be handled separately.
    operands = list(
        filter(lambda x: span.operands[x].defining_op.used, span.operands.keys())
    )
    root_filler: FillerNodeOutput = build_filler_node(
        matcher_unit_inputs,
        found_input_op.output,
        false.output,
        found_input_op.output,
        block,
        operands,
        enc_ctx,
        f"{matcher_unit_name}_dag_buffer_{name_counter}",
    )
    name_counter += 1
    store_operands_at: dict[int, "DagBufferNode"] = dict()
    for operand in operands:
        has_operand = HwOpHasOperand.from_operand(matcher_unit_inputs.input_op, operand)
        block.add_op(has_operand)
        operand_offset = HwOpGetOperandOffset.from_operand(
            matcher_unit_inputs.input_op, operand
        )
        block.add_op(operand_offset)
        wrapped_operand_offset = HwSumCreate.from_data(
            node_sum_type, "located_at", operand_offset.output
        )
        block.add_op(wrapped_operand_offset)
        write_val_muxer = CombMux.from_values(
            has_operand.output,
            wrapped_operand_offset.output,
            constant_never.output,
        )
        block.add_op(write_val_muxer)
        operand_node = construct_node(
            span.operands[operand].defining_op,
            write_val_muxer.result,
            root_filler.write_to_out,
            root_filler.write_val_out[operand],
        )
        store_operands_at[operand] = operand_node

    register_in_ctx(DagBufferNode(root_filler.output, store_operands_at), span)
    return ctx


def insert_module_output(
    block: Block,
    fsm_output: SSAValue,
    matcher_unit_inputs: MatcherUnitInputs,
    matcher_unit_name: str,
):
    # Construct next input_op
    true = HwConstant.from_attr(IntegerAttr.from_int_and_width(1, 1))
    block.add_op(true)
    is_stream_running = CombXor.from_values(
        [matcher_unit_inputs.is_stream_paused, true.output]
    )
    block.add_op(is_stream_running)
    false = HwConstant.from_attr(IntegerAttr.from_int_and_width(0, 1))
    block.add_op(false)
    output_register = SeqCompregCe.new(
        "output_" + matcher_unit_name,
        matcher_unit_inputs.input_op.typ,
        matcher_unit_inputs.input_op,
        matcher_unit_inputs.clock,
        is_stream_running.result,
        false.output,
        matcher_unit_inputs.input_op,
    )
    block.add_op(output_register)

    # Yield output.
    output = HwOutput.from_outputs([output_register.data, fsm_output])
    block.add_op(output)


def generate_matcher_unit(
    pdli_region: Region,
    enc_ctx: EncodingContext,
    op_ctx: OperationContext,
    matcher_unit_name: str,
) -> Tuple[HwModule, FsmMachine]:
    hw_module_block = Block(
        arg_types=[
            i1,  # clock
            HwOperation.from_encoding_ctx(enc_ctx),  # input_op
            i1,  # is_stream_paused
            i1,  # new_sequence
            i1,  # stream_completed
        ]
    )

    matcher_unit_inputs = MatcherUnitInputs(
        hw_module_block.args[0],
        hw_module_block.args[1],
        hw_module_block.args[2],
        hw_module_block.args[3],
        hw_module_block.args[4],
    )

    dag_buffer_node_sum_type = HwSumType.from_variants(
        {
            "unknown": i1,  # dummy i1
            "located_at": IntegerType(enc_ctx.operand_offset_width),
            "found": matcher_unit_inputs.input_op.typ,
            "never": i1,  # dummy i1
        }
    )

    # First step: generate the DAG buffer.
    dag_span, dag_span_ctx = compute_usage_graph(pdli_region)
    dag_buffer_ctx = create_filler(
        dag_span,
        hw_module_block,
        matcher_unit_inputs,
        matcher_unit_name,
        dag_buffer_node_sum_type,
        enc_ctx,
    )

    # Then, generate the FSM and instanciate it.
    status_sum_type = HwSumType.from_variants(
        {
            "unknown": i1,  # dummy i1
            "success": i1,  # dummy i1
            "failure": i1,  # dummy i1
        }
    )

    fsm_name = f"{matcher_unit_name}_fsm"
    fsm = generate_fsm(
        pdli_region,
        dag_span_ctx,
        dag_buffer_ctx,
        enc_ctx,
        fsm_name,
        dag_buffer_node_sum_type,
        status_sum_type,
    )

    inputs = list(map(lambda x: x.data, dag_buffer_ctx.nodes))
    fsm_inst = FsmHwInstance.new(
        f"{fsm_name}_inst",
        fsm_name,
        inputs,
        matcher_unit_inputs.clock,
        matcher_unit_inputs.new_sequence,
        [status_sum_type],
    )
    hw_module_block.add_op(fsm_inst)

    # Finally, yield module output.
    assert len(fsm_inst.outputs) == 1
    insert_module_output(hw_module_block, fsm_inst.outputs[0], matcher_unit_inputs, matcher_unit_name)

    # Build the hardware module
    return (
        HwModule.from_block(
            matcher_unit_name,
            hw_module_block,
            [
                "clock",
                "input_op",
                "is_stream_paused",
                "new_sequence",
                "stream_completed",
            ],
            ["output_op", "match_result"],
        ),
        fsm,
    )
