from xdsl.ir import MLContext
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, IntAttr
from xdsl.printer import Printer
from xdsl.parser import Parser
from subprocess import Popen, PIPE

from dialects.pdl_interp import PdlInterp
from dialects.pdl import Pdl
from dialects.fsm import Fsm
from dialects.hw import Hw
from dialects.hw_sum import HwSum
from dialects.comb import Comb

from analysis.pattern_dag_span import compute_usage_graph, DotNamer

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
context.register_dialect(Comb)

mlir_opt_process = Popen(
    [MLIR_OPT, "-mlir-print-op-generic", "--convert-pdl-to-pdl-interp"],
    stdin=PIPE,
    stdout=PIPE,
)
mlir_pdll_process = Popen(
    [MLIR_PDLL, "rewrites/redundant_or.pdll", "-x=mlir"], stdout=mlir_opt_process.stdin
)
mlir_opt_process.stdin.close()  # de-duplicate stdin handle
pdl_interp_src = mlir_opt_process.stdout.read().decode()

print(pdl_interp_src)

pdl_interp_parser = Parser(context, pdl_interp_src)
pdl_interp_data = pdl_interp_parser.parse_module()

matcher_func = pdl_interp_data.regions[0].ops.first

ssa_name = 0
for block in matcher_func.regions[0].blocks:
    for op in block.ops:
        for res in op.results:
            res.name = "s" + str(ssa_name)
            ssa_name += 1

pdl_interp_data.verify()

printer = Printer()
printer.print(pdl_interp_data)

print(f"\nDAG SPAN:")

try:
    namer = DotNamer()
    root_name = f"op{namer.get_id()}"
    print(compute_usage_graph(matcher_func.regions[0])[0].as_dot(namer, root_name))
except UnsupportedPatternFeature as e:
    print("Failure!")
    printer.print(e.culprit)
