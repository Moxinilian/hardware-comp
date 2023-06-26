from attr import dataclass
from typing import cast
from xdsl.ir import Operation, Attribute, ParametrizedAttribute
from xdsl.pattern_rewriter import (
    RewritePattern,
    PatternRewriter,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    DictionaryAttr,
    ArrayAttr,
)

from dialects.comb import CombConcat, CombExtract, CombICmp, ICmpPredicate
from dialects.hw import HwConstant
from dialects.hw_sum import HwSumType, HwSumCreate, HwSumIs, HwSumGetAs

import math


@dataclass
class LowerIntegerHwSum(RewritePattern):
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        visited = set()

        @dataclass
        class IntegerHwSumInfo:
            variant_width: int
            data_width: int

            @staticmethod
            def from_hwsum(typ: HwSumType):
                data_width = 0
                variant_width = math.ceil(math.log2(len(typ.cases.data)))
                for v in typ.cases.data.values():
                    if not isinstance(v, IntegerType):
                        return None
                    data_width = max(v.width.data, data_width)
                return IntegerHwSumInfo(
                    variant_width=variant_width, data_width=data_width
                )

        def replace_hwsumtype(attribute: Attribute) -> Attribute:
            if isinstance(attribute, HwSumType):
                info = IntegerHwSumInfo.from_hwsum(attribute)
                if info != None:
                    return IntegerType(info.variant_width + info.data_width)
                else:
                    return HwSumType(
                        [
                            DictionaryAttr(
                                {
                                    k: replace_hwsumtype(v)
                                    for k, v in attribute.cases.data.items()
                                }
                            )
                        ]
                    )
            elif isinstance(attribute, ArrayAttr):
                return ArrayAttr([replace_hwsumtype(attr) for attr in attribute.data])
            elif isinstance(attribute, DictionaryAttr):
                return DictionaryAttr(
                    {k: replace_hwsumtype(v) for k, v in attribute.data.items()}
                )
            elif isinstance(attribute, ParametrizedAttribute):
                return type(attribute).new(
                    [replace_hwsumtype(attr) for attr in attribute.parameters]
                )
            return attribute

        def lower_op(op: Operation):
            if op in visited:
                return
            visited.add(op)

            # Before lowering, propagate the lowering to users so type information is not lost
            for result in op.results:
                for use in list(result.uses):
                    lower_op(use.operation)

            # Also lower the users of potentially created block arguments within the current op
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        for use in list(arg.uses):
                            lower_op(use.operation)

            # If the operation is a HwSumCreate, replace it with the appropriate integer
            if isinstance(op, HwSumCreate):
                sum_type = cast(HwSumType, op.output.typ)
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
                    return

                if not isinstance(op.variant_data.typ, IntegerType):
                    return

                # Create the new integer value
                if info.variant_width == 0:
                    op.output.replace_by(op.variant_data)
                    rewriter.erase_matched_op()
                else:
                    variant_id = sum_type.get_variant_id(op.variant.data)
                    variant = HwConstant.from_attr(
                        IntegerAttr.from_int_and_width(variant_id, info.variant_width)
                    )

                    concatenated = []
                    data_type_as_int = cast(IntegerType, op.variant_data.typ)
                    assert data_type_as_int.width.data <= info.data_width
                    if data_type_as_int.width.data < info.data_width:
                        padding_width = info.data_width - data_type_as_int.width.data
                        padding = HwConstant.from_attr(
                            IntegerAttr.from_int_and_width(0, padding_width)
                        )
                        concatenated.append(padding.output)
                        rewriter.insert_op_before(padding, op)

                    concatenated += [op.variant_data, variant.output]

                    hwsum_int = CombConcat.from_values(concatenated)
                    rewriter.insert_op_before(variant, op)
                    rewriter.replace_op(op, hwsum_int)
                return

            # If the operation is a HwSumIs, compare the variant with the expected one
            if isinstance(op, HwSumIs):
                sum_type = cast(HwSumType, op.sum_type.typ)
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
                    return

                expected_variant = HwConstant.from_attr(
                    IntegerAttr.from_int_and_width(
                        sum_type.get_variant_id(op.variant.data),
                        info.variant_width,
                    )
                )
                extracted_variant = CombExtract.from_values(
                    op.sum_type, info.variant_width, 0
                )
                compared = CombICmp.from_values(
                    expected_variant.output, extracted_variant.output, ICmpPredicate.EQ
                )

                rewriter.insert_op_before(expected_variant, op)
                rewriter.insert_op_before(extracted_variant, op)
                rewriter.replace_op(op, compared)
                return

            # If the operation is a HwSumGetAs, extract the data appropriately
            if isinstance(op, HwSumGetAs):
                sum_type = cast(HwSumType, op.sum_type.typ)
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
                    return

                output_type_as_int = cast(IntegerType, op.output.typ)
                extracted_data = CombExtract.from_values(
                    op.sum_type, output_type_as_int.width.data, info.variant_width
                )

                rewriter.replace_op(op, extracted_data)
                return

            # If the operation is unrelated to HwSumType, simply lower its attributes
            for k, v in op.attributes.items():
                op.attributes[k] = replace_hwsumtype(v)

            # Then lower its return types
            for result in op.results:
                result.typ = replace_hwsumtype(result.typ)

            # Finally lower potentially created block arguments
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        rewriter.modify_block_argument_type(
                            arg, replace_hwsumtype(arg.typ)
                        )

        for region in op.regions:
            for op in list(region.ops):
                lower_op(op)
