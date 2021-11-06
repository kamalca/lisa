# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that

from lisa import Logger, Node, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.operating_system import Ubuntu
from lisa.util import SkippedException


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    Tests the functionality of infiniband.
    """,
)
class Infiniband(TestSuite):
    @TestCaseMetadata(
        description="""
        This test case will
        1. Determine whether the VM is IB over ND, IB over SR-IOV, or non-HPC
        2. Ensure waagent is configures with OS.EnableRDMA=y
        3. Check that appropriate drivers are present
        """,
        priority=2,
    )
    def verify_hpc_vm(self, log: Logger, node: Node) -> None:

        # Ubuntu is used for HPC SKU but manual configuration required.
        # It's exceptional.
        if isinstance(node.os, Ubuntu):
            raise SkippedException(
                f"{node.os.name} not supported. "
                "Only HPC machines are supported by this test."
            )

        if node.execute("test -d /sys/class/infiniband", shell=True).exit_code != 0:
            raise SkippedException(
                "/sys/class/infiniband/ not found. "
                "Only HPC machines are supported by this test."
            )

        is_over_SRIOV = (
            node.execute(
                'lspci | grep "Virtual Function"', shell=True, sudo=True
            ).exit_code
            == 0
            and node.execute(
                'dmesg | grep "IB Infiniband driver"', shell=True, sudo=True
            ).exit_code
            == 0
        )
        is_over_ND = (
            node.execute(
                "dmesg | grep hvnd_try_bind_nic", shell=True, sudo=True
            ).exit_code
            == 0
        )

        assert_that(is_over_ND or is_over_SRIOV).described_as(
            "Could not determine VM type is either HPC or non-HPC."
        ).is_true()

        result = node.execute(
            "cat /etc/waagent.conf | grep OS.EnableRDMA=y", shell=True
        )
        assert_that(result.stdout).described_as(
            "Found waagent configuration of OS.EnableRDMA=y "
            "was missing or commented out"
        ).is_equal_to("OS.EnableRDMA=y")
        log.debug("Verified waagent config OS.EnableRDMA=y set successfully")

        if is_over_ND:
            version = node.os.information.version
            node.execute(
                f"test -d /opt/microsoft/rdma/rhel{version.major}{version.minor}",
                sudo=True,
                shell=True,
                expected_exit_code=0,
                expected_exit_code_failure_message="Failed to find "
                "ND driver in /opt/microsoft/rdma/",
            )

        if is_over_SRIOV and not is_over_ND:
            result = node.execute(
                "dmesg | grep 'Mellanox Connect-IB Infiniband driver'",
                shell=True,
                sudo=True,
                expected_exit_code=0,
                expected_exit_code_failure_message="Failed to find "
                "SR-IOV driver for IB interface",
            )
            log.debug(
                "Successfully found the SR-IOV driver for IB interface - "
                f"{result.stdout}"
            )
