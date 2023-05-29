from attr import dataclass
from xdsl.ir import Region, SSAValue, Block
from xdsl.dialects.builtin import IntegerType

from dialects.fsm import FsmMachine
from dialects.hw import HwConstant, HwModule
from dialects.hw_op import HwOperation
from dialects.seq import SeqCompregCe

from analysis.pattern_dag_span import (
    OperationSpan,
    OperationSpanCtx,
    compute_usage_graph,
)


@dataclass
class DagBufferNode:
    """
    Represents a node of the DAG buffer, storing an operation.

    Field:
    - register: contains a register to an HwOperation from the `hw_op` dialect.
                This operation is the data stored in this node.
    - store_operands_at: maps to which DagBufferNode the defining operation of
                         operands of the currently stored operation will be
                         stored.
    """

    register: SeqCompregCe
    store_operands_at: dict[int, "DagBufferNode"] = dict()


@dataclass
class NodeAccess:
    node: DagBufferNode


@dataclass
class OperandAccess(NodeAccess):
    operand_pos: int


@dataclass
class ResultAccess(NodeAccess):
    result_pos: int


def create_dag_buffer(
    dag_span: OperationSpan, block: Block
) -> dict[SSAValue, NodeAccess]:
    """Constructs the DAG buffer and inserts its associated registers in the provided block.
    Returns a dictionary mapping a given PDL Interp value to the register in which the
    corresponding data should be fetched from."""

    name_counter = 0

    # TODO: replace dummy values with values from the filler
    dummy_op = block.insert_arg(HwOperation.from_widths(1), len(block.args))
    dummy_i1 = block.insert_arg(IntegerType.from_width(1), len(block.args))

    value_to_node: dict[SSAValue, NodeAccess] = dict()

    def add_all_values(values: list[SSAValue], node: NodeAccess):
        for v in values:
            value_to_node[v] = node

    def walk_operation_span(span: OperationSpan) -> DagBufferNode | None:
        if not span.used:
            return None
        new_node = DagBufferNode(
            SeqCompregCe.new(
                f"dag_buffer_op_{name_counter}",
                dummy_op,
                dummy_i1,
                dummy_i1,
                dummy_i1,
                dummy_op,
            )
        )
        name_counter += 1
        node_access = NodeAccess(new_node)
        add_all_values(span.pdl_values, node_access)
        add_all_values(span.all_operands_ranges, node_access)
        add_all_values(span.all_operand_types_ranges, node_access)
        add_all_values(span.all_results_ranges, node_access)
        add_all_values(span.all_result_types_ranges, node_access)
        for i, result in span.results.items():
            result_access = ResultAccess(new_node, i)
            add_all_values(result.pdl_values, result_access)
            add_all_values(result.pdl_types, result_access)
        for i, operand in span.operands.items():
            operand_access = OperandAccess(new_node, i)
            add_all_values(operand.pdl_values, operand_access)
            add_all_values(operand.pdl_types, operand_access)
            operand_node = walk_operation_span(operand.defining_op)
            if operand_node:
                new_node.store_operands_at[i] = operand_node
        return new_node

    walk_operation_span(dag_span)
    return value_to_node


def generate_matcher_unit(pdli_region: Region) -> HwModule:
    hw_module_block = Block()

    # First step: generate the DAG buffer.
    dag_span, dag_span_ctx = compute_usage_graph(pdli_region)
    dag_buffer = create_dag_buffer(dag_span, hw_module_block)
