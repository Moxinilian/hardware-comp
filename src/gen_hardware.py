from xdsl.ir import MLContext
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, IntAttr
from xdsl.printer import Printer
from xdsl.parser import Parser, Source
from subprocess import Popen, PIPE

from dialects.pdl_interp import PdlInterp
from dialects.pdl import Pdl
from dialects.fsm import Fsm

MLIR_PDLL = "./mlir-pdll"
MLIR_OPT = "./mlir-opt"

context = MLContext()

context.register_dialect(Arith)
context.register_dialect(Builtin)
context.register_dialect(Pdl)
context.register_dialect(PdlInterp)
context.register_dialect(Fsm)

mlir_opt_process = Popen([MLIR_OPT, "-mlir-print-op-generic", "--convert-pdl-to-pdl-interp"], stdin=PIPE, stdout=PIPE)
mlir_pdll_process = Popen([MLIR_PDLL, "rewrites/redundant_or.pdll", "-x=mlir"], stdout=mlir_opt_process.stdin)
mlir_opt_process.stdin.close() # de-duplicate stdin handle
pdl_interp_src = mlir_opt_process.stdout.read().decode()

pdl_interp_parser = Parser(context, pdl_interp_src, source=Source.MLIR)
pdl_interp_data = pdl_interp_parser.parse_module()

printer = Printer(target=Printer.Target.MLIR)
printer.print(pdl_interp_data)
