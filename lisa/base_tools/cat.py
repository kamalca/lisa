# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from typing import List

from lisa.executable import Tool


class Interrupt:
    irq_number: str
    interrupt_count: List[int]
    metadata: str

    def __init__(
        self, irq_number: str, interrupt_count: List[int], metadata: str = ""
    ) -> None:
        self.irq_number = irq_number
        self.interrupt_count = interrupt_count
        self.metadata = metadata

    def __str__(self) -> str:
        return (
            f"irq_number : {self.irq_number}, "
            f"count : {self.interrupt_count}, "
            f"metadata : {self.metadata}"
        )

    def __repr__(self) -> str:
        return self.__str__()


class Cat(Tool):
    _interrupt_regex = re.compile(
        r"^\s*(?P<irq_number>\S+):\s+(?P<interrupt_count>[\d+ ]+)\s*(?P<metadata>.*)$"
    )

    @property
    def command(self) -> str:
        return "cat"

    def _check_exists(self) -> bool:
        return True

    def read_from_file(
        self,
        file: str,
        force_run: bool = False,
        sudo: bool = False,
    ) -> str:
        # Run `cat <file>`
        result = self.run(file, force_run=force_run, sudo=sudo)
        result.assert_exit_code(message=f"Error : {result.stdout}")
        return result.stdout

    def get_interrupt_data(self) -> List[Interrupt]:
        # Run cat /proc/interrupts. The output is of the form :
        #          CPU0       CPU1
        # 0:         22          0  IR-IO-APIC   2-edge      timer
        # 1:          2          0  IR-IO-APIC   1-edge      i8042
        # ERR:        0
        # The first column refers to the IRQ number. The next column contains
        # number of interrupts per IRQ for each CPU in the system. The remaining
        # column report the metadata about interrupts, including type of interrupt,
        # device etc. This is variable for each distro.
        # Note : Some IRQ numbers have single entry because they're not actually
        # CPU stats, but events count belonging to the IO-APIC controller. For
        # example, `ERR` is incremented in the case of errors in the IO-APIC bus.
        result = self.run("/proc/interrupts", sudo=True).stdout
        mappings_with_header = result.splitlines(keepends=False)
        mappings = mappings_with_header[1:]
        assert len(mappings) > 0

        interrupts = []
        for line in mappings:
            matched = self._interrupt_regex.fullmatch(line)
            assert matched
            interrupt_count = [
                int(count) for count in matched.group("interrupt_count").split()
            ]
            interrupts.append(
                Interrupt(
                    irq_number=matched.group("irq_number"),
                    interrupt_count=interrupt_count,
                    metadata=matched.group("metadata"),
                )
            )
        return interrupts
