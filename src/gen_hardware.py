from xdsl.ir import MLContext
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin
from xdsl.printer import Printer


# MLContext, containing information about the registered dialects
context = MLContext()

# Some useful dialects
context.register_dialect(Arith)
context.register_dialect(Builtin)

# Printer used to pretty-print MLIR data structures
printer = Printer()
