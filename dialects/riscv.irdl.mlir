irdl.dialect @rv32i {
    irdl.type @register {}
    irdl.type @imm12 {}
    irdl.type @imm20 {}

    %reg = irdl.parametric @register<>
    %imm12 = irdl.parametric @imm12<>
    %imm20 = irdl.parametric @imm20<>

    irdl.operation @add {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @sub {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @addi {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @slt {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @slti {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @sltu {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @sltiu {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @lui {
        irdl.operands(%imm20)
        irdl.results(%reg)
    }

    irdl.operation @auip {
        irdl.operands(%imm20)
        irdl.results(%reg)
    }

    irdl.operation @xori {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @ori {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @andi {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @slli {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @srli {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @srai {
        irdl.operands(%reg, %imm12)
        irdl.results(%reg)
    }

    irdl.operation @sll {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @xor {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @srl {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @sra {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @or {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }

    irdl.operation @and {
        irdl.operands(%reg, %reg)
        irdl.results(%reg)
    }
}
