from assertpy import assert_that

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.tools import Lsmod
from lisa.util import LisaException


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite ensures the floppy module is disabled.
    """,
)
class Floppy(TestSuite):
    @TestCaseMetadata(
        description="""
        This test case will
        1. Ensure the floppy module is not loaded.
        """,
        priority=0,
    )
    def check_floppy_module(
        self, case_name: str, log: Logger, node: RemoteNode
    ) -> None:
        # cmd_result = node.execute("/usr/sbin/lsmod | /usr/bin/grep floppy", shell=True)
        # assert_that(cmd_result.exit_code).described_as(
        #     "Floppy module should be disabled."
        # ).is_equal_to(1)

        node.execute("sudo modprobe floppy")

        lsmod = node.tools[Lsmod]
        if lsmod.module_exists(mod_name="floppy"):
            raise LisaException("Module present")
