from assertpy import assert_that

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.tools import Lsmod


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
        lsmod = node.tools[Lsmod]
        assert_that(lsmod.module_exists("floppy")).described_as(
            "Floppy module should be disabled"
        ).is_false()
