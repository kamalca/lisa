from lisa import (
    LisaException,
    Logger,
    PassedException,
    RemoteNode,
    SkippedException,
    TestCaseMetadata,
    TestSuite,
    TestSuiteMetadata,
    create_timer,
    simple_requirement,
)


from lisa import Node
from lisa.tools import Lsmod

from assertpy import assert_that


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite is a test.
    """,
)
class check_floppy_module(TestSuite):
    @TestCaseMetadata(
        description="""
        This test case will
        1. Ensure the floppy module is disabled.
        """,
        priority=0,
    )
    def test(self, case_name: str, log: Logger, node: RemoteNode) -> None:
        result = node.execute("sudo modprobe floppy")
        print(result.stdout)
        print(result.stderr)
        print(result.exit_code)

        # lsmod = node.tools[Lsmod]
        # if lsmod.module_exists("floppy"):
        #     raise LisaException("Module present")
        # else:
        #     print("Module not present")

        cmd_result = node.execute("lsmod | grep floppy")
        assert_that(cmd_result.exit_code).described_as(
            f"Floppy module should be disabled."
        ).is_equal_to(1)
