from dataclasses import dataclass

from xdsl.ir import Operation
from xdsl.pattern_rewriter import RewritePattern, PatternRewriter

from dialects.pdl_interp import *


@dataclass
class SwitchifyPdlInterp(RewritePattern):
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        match op:
            case PdlInterpCheckAttribute(
                constant_value=constant_value,
                attribute=attribute,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                rewriter.replace_op(
                    op,
                    PdlInterpSwitchAttribute.from_cases(
                        attribute, {constant_value: true_dest}, false_dest
                    ),
                )

            case PdlInterpCheckOperationName(
                op_name=op_name,
                input_op=input_op,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                rewriter.replace_op(
                    op,
                    PdlInterpSwitchOperationName.from_cases(
                        input_op, {op_name: true_dest}, false_dest
                    ),
                )

            case PdlInterpCheckType(
                typ=typ,
                value=value,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                rewriter.replace_op(
                    op,
                    PdlInterpSwitchType.from_cases(value, {typ: true_dest}, false_dest),
                )

            case PdlInterpCheckTypes(
                types=types,
                value=value,
                true_dest=true_dest,
                false_dest=false_dest,
            ):
                rewriter.replace_op(
                    op,
                    PdlInterpSwitchTypes.from_cases(
                        value, {types: true_dest}, false_dest
                    ),
                )

