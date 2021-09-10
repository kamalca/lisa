# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that

from lisa import RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.tools import Lsmod


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
        1. Ensure the floppy driver is not loaded directly
        into the kernel by checking boot config
        2. Ensure the floppy driver is not loaded as a module using lsmod
        """,
        priority=0,
    )
    def check_floppy_module(self, node: RemoteNode) -> None:
        # 1
        uname = node.execute("uname -r").stdout
        configPath = f"/boot/config-{uname}"

        assert_that(
            node.execute(f"grep CONFIG_BLK_DEV_FD=y {configPath}").exit_code
        ).described_as(
            "Floppy driver should not be installed in the kernel."
        ).is_equal_to(
            1
        )

        # 2
        lsmod = node.tools[Lsmod]
        assert_that(lsmod.module_exists("floppy")).described_as(
            "Floppy module should be disabled by adding it to the blacklist"
        ).is_false()
