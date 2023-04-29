from typing import Annotated
from attr import dataclass
from xdsl.irdl import (irdl_op_definition, irdl_attr_definition, AnyAttr,
                       Operand, OpAttr, ParameterDef)
from xdsl.ir import (ParametrizedAttribute, MLIRType, Dialect, Operation,
                     OpResult, Attribute, Region)
from xdsl.dialects.builtin import (StringAttr, ArrayAttr, SymbolRefAttr,
                                   DictionaryAttr, IntegerType, i1)
from xdsl.utils.exceptions import VerifyException
from xdsl.pattern_rewriter import (RewritePattern, op_type_rewrite_pattern,
                                   PatternRewriter)

import math


@irdl_attr_definition
class HwSumType(ParametrizedAttribute):
    name = "hw_sum.sum_type"

    cases: ParameterDef[DictionaryAttr]

    def verify(self) -> None:
        if len(self.cases.data) == 0:
            raise VerifyException("sum type has no variant")


@irdl_op_definition
class HwSumIs(Operation):
    name = "hw_sum.is"

    variant: OpAttr[StringAttr]
    sum_type: Annotated[Operand, HwSumType]
    output: Annotated[OpResult, i1]

    def verify_(self) -> None:
        sum_type: HwSumType = self.sum_type.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'")


@irdl_op_definition
class HwSumGetAs(Operation):
    name = "hw_sum.get_as"

    variant: OpAttr[StringAttr]
    sum_type: Annotated[Operand, HwSumType]
    output: Annotated[OpResult, AnyAttr()]

    def verify_(self) -> None:
        sum_type: HwSumType = self.sum_type.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'")

        expected = sum_type.cases.data.get(self.variant.data)
        if expected != self.output.typ:
            raise VerifyException(
                f"type '{self.output.typ}' does not match expected type "
                f"'{expected}' for variant '{self.variant.data}'")


@irdl_op_definition
class HwSumCreate(Operation):
    name = "hw_sum.create"

    variant: OpAttr[StringAttr]
    variant_data: Annotated[Operand, AnyAttr()]
    output: Annotated[OpResult, HwSumType]

    def verify_(self) -> None:
        sum_type: HwSumType = self.output.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'")

        expected = sum_type.cases.data.get(self.variant.data)
        if expected != self.variant_data.typ:
            raise VerifyException(
                f"type '{self.output.typ}' does not match expected type "
                f"'{expected}' for variant '{self.variant.data}'")


HwSum = Dialect([HwSumIs, HwSumGetAs, HwSumCreate], [HwSumType])


@dataclass
class LowerIntegerHwSum(RewritePattern):

    def match_and_rewrite(self, op: Operation,
                          rewriter: PatternRewriter) -> None:

        def replace_hwsumtype(attribute: Attribute) -> Attribute:
            if isinstance(attribute, HwSumType):
                converted = {}
                are_only_integers = True
                biggest_width = 0
                for k, v in attribute.cases.data:
                    new_elem = replace_hwsumtype(v)
                    if isinstance(new_elem, IntegerType):
                        biggest_width = max(new_elem.width.data, biggest_width)
                    else:
                        are_only_integers = False
                    converted[k] = new_elem

                if are_only_integers:
                    return IntegerType.from_width(
                        math.log2(len(converted)) + biggest_width)
                else:
                    return HwSumType([DictionaryAttr(converted)])
            elif isinstance(attribute, ArrayAttr):
                return ArrayAttr(
                    [replace_hwsumtype(attr) for attr in attribute.data])
            elif isinstance(attribute, DictionaryAttr):
                return DictionaryAttr(
                    {k: replace_hwsumtype(v)
                     for k, v in attribute.data})
            elif isinstance(attribute, ParametrizedAttribute):
                return type(attribute).new(
                    [replace_hwsumtype(attr) for attr in attribute.parameters])
            else:
                return attribute

        if isinstance(op, HwSumIs):
            pass
