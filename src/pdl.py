from __future__ import annotations
from xdsl.dialects.builtin import *
from xdsl.ir import *
from xdsl.irdl import *
from xdsl.utils import *
from xdsl.parser import Parser


@irdl_attr_definition
class AttributeType(ParametrizedAttribute, MLIRType):
    name = "pdl.attribute"


@irdl_attr_definition
class OperationType(ParametrizedAttribute, MLIRType):
    name = "pdl.operation"


class RangeValue(Enum):
    TYPE = 0
    ATTRIBUTE = 1
    VALUE = 2
    OPERATION = 3


@irdl_attr_definition
class RangeType(Data[RangeValue], MLIRType):
    name = "pdl.range"

    @staticmethod
    def parse_parameter(parser: Parser) -> RangeValue:
        try:
            parser.parse_char("type")
            return RangeValue.TYPE
        except:
            pass

        try:
            parser.parse_char("attribute")
            return RangeValue.ATTRIBUTE
        except:
            pass

        try:
            parser.parse_char("value")
            return RangeValue.VALUE
        except:
            pass

        try:
            parser.parse_char("operation")
            return RangeValue.OPERATION
        except:
            pass

        parser.raise_error(
            "expected either type, attribute, value or operation")

    @staticmethod
    def print_parameter(data: RangeValue, printer: Printer) -> None:
        if data == RangeValue.TYPE:
            printer.print_string("type")
        elif data == RangeValue.ATTRIBUTE:
            printer.print_string("attribute")
        elif data == RangeValue.VALUE:
            printer.print_string("value")
        elif data == RangeValue.OPERATION:
            printer.print_string("operation")
        else:
            printer.diagnostic.raise_exception("invalid range element type")


@irdl_attr_definition
class TypeType(ParametrizedAttribute, MLIRType):
    name = "pdl.type"


@irdl_attr_definition
class ValueType(ParametrizedAttribute, MLIRType):
    name = "pdl.value"


@irdl_op_definition
class AttributeOp(Operation):
    """
    https://mlir.llvm.org/docs/Dialects/PDLOps/#pdlattribute-mlirpdlattributeop
    """
    name: str = "pdl.attribute"
    value: OptOpAttr[Attribute]
    value_type: Annotated[OptOperand, TypeType]
    output: Annotated[OpResult, AttributeType]


@irdl_op_definition
class EraseOp(Operation):
    """
    https://mlir.llvm.org/docs/Dialects/PDLOps/#pdlerase-mlirpdleraseop
    """
    name: str = "pdl.erase"
    op_value: Annotated[Operand, OperationType]


@irdl_op_definition
class OperandOp(Operation):
    """
    https://mlir.llvm.org/docs/Dialects/PDLOps/#pdloperand-mlirpdloperandop
    """
    name: str = "pdl.operand"
    value_type: Annotated[Operand, TypeType]
    output: Annotated[OpResult, ValueType]


@irdl_op_definition
class OperandsOp(Operation):
    """
    https://mlir.llvm.org/docs/Dialects/PDLOps/#pdloperands-mlirpdloperandsop
    """
    name: str = "pdl.operands"
    value_type: Annotated[Operand,
                          RangeType]  # Range of Types can we parametrize this?
    output: Annotated[OpResult,
                      RangeType]  # Range of Values can we parametrize this?


Pdl = Dialect([AttributeOp, OperandOp, EraseOp, OperandsOp],
              [AttributeType, OperationType, RangeType, TypeType, ValueType])
