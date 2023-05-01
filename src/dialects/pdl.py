# This file is a placeholder while waiting for proper implementation of PDL in xDSL.

from __future__ import annotations
from xdsl.dialects.builtin import *
from xdsl.ir import *
from xdsl.irdl import *
from xdsl.utils import *
from xdsl.parser import Parser


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

        parser.raise_error("expected either type, attribute, value or operation")

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
class TypeType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.type"


@irdl_attr_definition
class ValueType(ParametrizedAttribute, TypeAttribute):
    name = "pdl.value"


Pdl = Dialect([], [AttributeType, OperationType, RangeType, TypeType, ValueType])
