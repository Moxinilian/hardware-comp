from typing import Annotated
from dataclasses import dataclass
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    OpAttr,
    ParameterDef,
)
from xdsl.ir import (
    ParametrizedAttribute,
    Dialect,
    Operation,
    OpResult,
    Attribute,
    Region,
    SSAValue,
)
from xdsl.dialects.builtin import (
    StringAttr,
    ArrayAttr,
    SymbolRefAttr,
    DictionaryAttr,
    IntegerType,
    i1,
)
from xdsl.utils.exceptions import VerifyException


@dataclass
class VariantNotFoundException(Exception):
    variant: str


@irdl_attr_definition
class HwSumType(ParametrizedAttribute):
    name = "hw_sum.sum_type"

    cases: ParameterDef[DictionaryAttr]

    @staticmethod
    def from_variants(variants: dict[str, Attribute]) -> "HwSumType":
        return HwSumType([DictionaryAttr.from_dict(variants)])

    def verify(self) -> None:
        if len(self.cases.data) == 0:
            raise VerifyException("sum type has no variant")

    def get_variant_id(self, variant: str) -> int:
        variant_id = 0
        variants = list(self.cases.data.keys())
        while variant_id < len(variants) and variants[variant_id] != variant:
            variant_id += 1
        if variant_id < len(variants):
            return variant_id
        raise VariantNotFoundException(variant)


@irdl_op_definition
class HwSumIs(IRDLOperation):
    name = "hw_sum.is"

    variant: OpAttr[StringAttr]
    sum_type: Annotated[Operand, HwSumType]
    output: Annotated[OpResult, i1]

    @staticmethod
    def from_variant(sum_type_inst: SSAValue, variant: str):
        if not variant in sum_type_inst.typ.cases.data.keys():
            raise VariantNotFoundException(variant)
        return HwSumIs.create(
            operands=[sum_type_inst],
            result_types=[i1],
            attributes={"variant": StringAttr.from_str(variant)},
        )

    def verify_(self) -> None:
        sum_type: HwSumType = self.sum_type.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'"
            )


@irdl_op_definition
class HwSumGetAs(IRDLOperation):
    name = "hw_sum.get_as"

    variant: OpAttr[StringAttr]
    sum_type: Annotated[Operand, HwSumType]
    output: Annotated[OpResult, AnyAttr()]

    @staticmethod
    def from_variant(sum_type_inst: SSAValue, variant: str):
        variants = sum_type_inst.typ.cases.data
        if not variant in variants.keys():
            raise VariantNotFoundException(variant)
        return HwSumGetAs.create(
            operands=[sum_type_inst],
            result_types=[variants[variant]],
            attributes={"variant": StringAttr.from_str(variant)},
        )

    def verify_(self) -> None:
        sum_type: HwSumType = self.sum_type.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'"
            )

        expected = sum_type.cases.data.get(self.variant.data)
        if expected != self.output.typ:
            raise VerifyException(
                f"type '{self.output.typ}' does not match expected type "
                f"'{expected}' for variant '{self.variant.data}'"
            )


@irdl_op_definition
class HwSumCreate(IRDLOperation):
    name = "hw_sum.create"

    variant: OpAttr[StringAttr]
    variant_data: Annotated[Operand, AnyAttr()]
    output: Annotated[OpResult, HwSumType]

    @staticmethod
    def from_data(sum_type: HwSumType, variant: str, data: SSAValue):
        if not variant in sum_type.cases.data.keys():
            raise VariantNotFoundException(variant)
        return HwSumCreate.create(
            operands=[data],
            result_types=[sum_type],
            attributes={"variant": StringAttr.from_str(variant)},
        )

    def verify_(self) -> None:
        sum_type: HwSumType = self.output.typ
        if not self.variant.data in sum_type.cases.data:
            raise VerifyException(
                f"'{self.variant.data}' is not a variant of '{sum_type}'"
            )

        expected = sum_type.cases.data.get(self.variant.data)
        if expected != self.variant_data.typ:
            raise VerifyException(
                f"type '{self.output.typ}' does not match expected type "
                f"'{expected}' for variant '{self.variant.data}'"
            )


HwSum = Dialect([HwSumIs, HwSumGetAs, HwSumCreate], [HwSumType])
