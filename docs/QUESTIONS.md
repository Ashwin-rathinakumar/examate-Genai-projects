# 10 real questions my user will ask

Write them the way your user would type them. At least 3 must need more than one page to answer, and at least 1 must be a question your documents cannot answer.

| # | Question | Where the answer is (document, page) | Needs more than one page? |
|---|---|---|---|
| 1 | What does the MPP field in `mstatus` control? | RISC-V Privileged ISA, Machine Status Registers (page TBD) | No |
| 2 | Which instructions are added by the `Zba` extension? | RISC-V Unprivileged ISA, Zba Address Generation Instructions (page TBD) | No |
| 3 | What's the difference between `FENCE` and `FENCE.I`, and when should I use them for self-modifying code? | RISC-V Unprivileged ISA, FENCE and Zifencei sections (pages TBD) | Yes |
| 4 | How do `CSRRW`, `CSRRS`, and `CSRRC` behave when `x0` is used? | RISC-V Unprivileged ISA, Zicsr Extension (page TBD) | No |
| 5 | What do the `MODE`, `ASID`, and `PPN` fields in `satp` mean? | RISC-V Privileged ISA, Supervisor Address Translation Register (page TBD) | No |
| 6 | When do I need to execute `SFENCE.VMA` after changing `satp` or updating page tables? | RISC-V Privileged ISA, satp and SFENCE.VMA sections (pages TBD) | Yes |
| 7 | How does `JALR` calculate the jump target address? | RISC-V Unprivileged ISA, Unconditional Jumps (page TBD) | No |
| 8 | How do `mstatus.MPP`, `MPIE`, and `MIE` change when a trap occurs and `MRET` executes? | RISC-V Privileged ISA, Machine Status Registers and Privilege Levels (pages TBD) | Yes |
| 9 | What happens when `mstatus.TVM` is set to 1? | RISC-V Privileged ISA, Machine Status Registers (page TBD) | No |
| 10 | Who approved yesterday's RTL changes in our company's private GitHub repository? (cannot be answered from my documents) | none | No |
