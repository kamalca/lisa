# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa import RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.util import LisaException, PassedException


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite ensures the floppy driver is disabled.
    The floppy driver is not needed on Azure and
    is known to cause problems in some scenarios.
    """,
)
class Floppy(TestSuite):
    @TestCaseMetadata(
        description="""
        This test case will
        1. Dry-run modprobe to see if floppy module can be loaded
        2. If "insmod" is executed then it is not already loaded
        3. If module cannot be found then it is not loaded
        If the module is loaded, running modprobe will have no output
        """,
        priority=0,
    )
    def check_floppy_module(self, node: RemoteNode) -> None:
        result = node.execute("modprobe -nv floppy")

        could_be_loaded = "insmod" in result.stdout
        does_not_exist = "not found" in result.stderr or "not found" in result.stdout

        if could_be_loaded or does_not_exist:
            raise PassedException

        raise LisaException(
            "The floppy module should not be loaded.",
            "Try adding the module to the blacklist.",
        )
