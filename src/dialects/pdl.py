# This file is a placeholder while waiting for proper implementation of PDL in xDSL.

from enum import Enum
from xdsl.ir import TypeAttribute, ParametrizedAttribute, Data, Dialect
from xdsl.irdl import irdl_attr_definition
from xdsl.parser import Parser
from xdsl.printer import Printer


@irdl_attr_definition
class AttributeType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.attribute"


@irdl_attr_definition
class OperationType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.operation"


class RangeValue(Enum):
    TYPE = 0
    ATTRIBUTE = 1
    VALUE = 2
    OPERATION = 3


@irdl_attr_definition
class RangeType(Data[RangeValue], TypeAttribute):
    name = "pdl.range"

    @staticmethod
    def parse_parameter(parser: Parser) -> RangeValue:
        try:
            parser.parse_characters("type")
            return RangeValue.TYPE
        except:
            pass

        try:
            parser.parse_characters("attribute")
            return RangeValue.ATTRIBUTE
        except:
            pass

        try:
            parser.parse_characters("value")
            return RangeValue.VALUE
        except:
            pass

        try:
            parser.parse_characters("operation")
            return RangeValue.OPERATION
        except:
            pass

        parser.raise_error("expected either type, attribute, value or operation")

    def print_parameter(self, printer: Printer) -> None:
        if self.data == RangeValue.TYPE:
            printer.print_string("type")
        elif self.data == RangeValue.ATTRIBUTE:
            printer.print_string("attribute")
        elif self.data == RangeValue.VALUE:
            printer.print_string("value")
        elif self.data == RangeValue.OPERATION:
            printer.print_string("operation")
        else:
            raise ValueError("illegal pdl range type")


@irdl_attr_definition
class TypeType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.type"


@irdl_attr_definition
class ValueType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.value"


Pdl = Dialect([], [AttributeType, OperationType, RangeType, TypeType, ValueType])
