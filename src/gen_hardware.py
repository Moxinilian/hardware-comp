from xdsl.ir import MLContext
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, IntAttr
from xdsl.printer import Printer
from xdsl.parser import Parser, Source

from pdl_interp import PdlInterp
from pdl import Pdl, RangeType, RangeValue


context = MLContext()

context.register_dialect(Arith)
context.register_dialect(Builtin)
context.register_dialect(Pdl)
context.register_dialect(PdlInterp)

with open('test_pdl.mlir', 'r') as file:
    data = file.read()

parser = Parser(context, data, source=Source.MLIR, filename="test_pdl.mlir")
module = parser.parse_module()

printer = Printer(target=Printer.Target.MLIR)
printer.print(module)
