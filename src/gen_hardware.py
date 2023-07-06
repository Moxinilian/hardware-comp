from xdsl.ir import MLContext
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, IntAttr, i32
from xdsl.printer import Printer
from xdsl.parser import ModuleOp, Parser
from xdsl.pattern_rewriter import PatternRewriteWalker, GreedyRewritePatternApplier
from subprocess import Popen, PIPE

from dialects.pdl_interp import PdlInterp
from dialects.pdl import Pdl
from dialects.fsm import Fsm
from dialects.hw import Hw
from dialects.hw_op import HwOp
from dialects.hw_sum import HwSum
from dialects.comb import Comb

from analysis.pattern_dag_span import compute_usage_graph, DotNamer
from encoder import EncodingContext, OperationContext, OperationInfo
from lowering.pdli_to_matcher_unit import generate_matcher_unit
from lowering.int_hw_sum import LowerIntegerHwSum
from lowering.int_hw_op import LowerIntegerHwOperation
from lowering.pdli_switchify import SwitchifyPdlInterp

from utils import UnsupportedPatternFeature

MIN_PYTHON = (3, 10)

MLIR_PDLL = "./mlir-pdll"
MLIR_OPT = "./mlir-opt"

import sys

if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

context = MLContext()

context.register_dialect(Arith)
context.register_dialect(Builtin)
context.register_dialect(Pdl)
context.register_dialect(PdlInterp)
context.register_dialect(Fsm)
context.register_dialect(Hw)
context.register_dialect(HwSum)
context.register_dialect(HwOp)
context.register_dialect(Comb)

mlir_opt_process = Popen(
    [MLIR_OPT, "-mlir-print-op-generic", "--convert-pdl-to-pdl-interp"],
    stdin=PIPE,
    stdout=PIPE,
)
mlir_pdll_process = Popen(
    [MLIR_PDLL, "rewrites/redundant_or.pdll", "-x=mlir"], stdout=mlir_opt_process.stdin
)

mlir_opt_process.stdin.close()  # de-duplicate stdin handle # type: ignore
pdl_interp_src = mlir_opt_process.stdout.read().decode()  # type: ignore

pdl_interp_parser = Parser(context, pdl_interp_src)
pdl_interp_data = pdl_interp_parser.parse_module()

walker = PatternRewriteWalker(
    GreedyRewritePatternApplier([SwitchifyPdlInterp()]),
    walk_regions_first=True,
    apply_recursively=True,
    walk_reverse=False,
)

walker.rewrite_module(pdl_interp_data)

matcher_func = pdl_interp_data.regions[0].ops.first

ssa_name = 0
for block in matcher_func.regions[0].blocks:  # type: ignore
    for op in block.ops:
        for res in op.results:
            res.name_hint = "s" + str(ssa_name)
            ssa_name += 1

pdl_interp_data.verify()

print(pdl_interp_data)

printer = Printer(print_debuginfo=True)

op_context = OperationContext({"rv32i.or": OperationInfo(0, [i32, i32], i32)})

hw_module, fsm = generate_matcher_unit(matcher_func.regions[0], EncodingContext(4, 4, 2), op_context, "matcher_unit")  # type: ignore

module = ModuleOp([fsm, hw_module])

walker = PatternRewriteWalker(
    GreedyRewritePatternApplier([LowerIntegerHwOperation(op_context)]),
    walk_regions_first=True,
    apply_recursively=True,
    walk_reverse=False,
)

walker.rewrite_module(module)

walker = PatternRewriteWalker(
    GreedyRewritePatternApplier([LowerIntegerHwSum()]),
    walk_regions_first=True,
    apply_recursively=True,
    walk_reverse=False,
)

walker.rewrite_module(module)

module.verify()
printer.print(module)
