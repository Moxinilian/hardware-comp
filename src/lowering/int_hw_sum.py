from attr import dataclass
from xdsl.ir import Operation, Attribute
from xdsl.pattern_rewriter import (
    RewritePattern,
    op_type_rewrite_pattern,
    PatternRewriter,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    DictionaryAttr,
    ArrayAttr,
    ParametrizedAttribute,
)

from dialects.comb import CombConcat, CombExtract, CombICmp, ICmpPredicate
from dialects.hw import HwConstant
from dialects.hw_sum import HwSumType, HwSumCreate, HwSumIs, HwSumGetAs

import math

# TODO: this code is a horrible proof of concept, please clean up

@dataclass
class LowerIntegerHwSum(RewritePattern):
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        visited = set()

        @dataclass
        class IntegerHwSumInfo:
            variant_width: int
            data_width: int

            def from_hwsum(typ: HwSumType):
                data_width = 0
                variant_width = math.ceil(math.log2(len(typ.cases.data)))
                for k, v in typ.cases.data.items():
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
                                    for k, v in attribute.cases.data
                                }
                            )
                        ]
                    )
            elif isinstance(attribute, ArrayAttr):
                return ArrayAttr([replace_hwsumtype(attr) for attr in attribute.data])
            elif isinstance(attribute, DictionaryAttr):
                return DictionaryAttr(
                    {k: replace_hwsumtype(v) for k, v in attribute.data}
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
                if not isinstance(result.typ, HwSumType):
                    continue
                info = IntegerHwSumInfo.from_hwsum(result.typ)
                if info == None:
                    continue
                for use in list(result.uses):
                    lower_op(use.operation)

            # Also lower the users of potentially created block arguments
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        if not isinstance(arg.typ, HwSumType):
                            continue
                        info = IntegerHwSumInfo.from_hwsum(arg.typ)
                        if info == None:
                            continue
                        for use in list(arg.uses):
                            lower_op(use.operation)

            # If the operation is a HwSumCreate, replace it with the appropriate integer
            if isinstance(op, HwSumCreate):
                sum_type: HwSumType = op.output.typ
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
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
                    assert op.variant_data.typ.width.data <= info.data_width
                    if op.variant_data.typ.width.data < info.data_width:
                        padding_width = info.data_width - op.variant_data.typ.width.data
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
                sum_type: HwSumType = op.sum_type.typ
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
                    return

                expected_variant = HwConstant.from_attr(
                    IntegerAttr.from_int_and_width(
                        op.sum_type.typ.get_variant_id(op.variant.data),
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
                sum_type: HwSumType = op.sum_type.typ
                info = IntegerHwSumInfo.from_hwsum(sum_type)
                if info == None:
                    return

                extracted_data = CombExtract.from_values(
                    op.sum_type, op.output.typ.width, info.variant_width+1
                )

                rewriter.replace_op(op, extracted_data)
                return

            # If the operation is unrelated to HwSumType, simply lower its attributes
            for k, v in op.attributes.items():
                op.attributes[k] = replace_hwsumtype(v)

            # Then lower its return types
            for result in op.results:
                if not isinstance(result.typ, HwSumType):
                    continue
                info = IntegerHwSumInfo.from_hwsum(result.typ)
                if info == None:
                    continue
                result.typ = replace_hwsumtype(result.typ)

            # Finally lower potentially created block arguments
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        if not isinstance(arg.typ, HwSumType):
                            continue
                        info = IntegerHwSumInfo.from_hwsum(arg.typ)
                        if info == None:
                            continue
                        rewriter.modify_block_argument_type(
                            arg, replace_hwsumtype(arg.typ)
                        )

        for region in op.regions:
            for op in list(region.ops):
                lower_op(op)
