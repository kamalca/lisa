# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.operating_system import CentOs, Redhat
from lisa.util import SkippedException
from lisa.tools import Modinfo


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite covers test cases previously handled by LISAv2:
    LIS-MODULES-CHECK, VERIFY-LIS-MODULES-VERSION,
    INITRD-MODULES-CHECK, RELOAD-MODULES-SMP
    """,
)
class HvModule(TestSuite):
    def get_modules(self, node: RemoteNode) -> list[str]:
        hvModules = ["hv_storvsc", "hv_netvsc", "hv_vmbus", "hv_utils", "hid_hyperv"]
        uname = node.execute("uname -r").stdout
        configPath = f"/boot/config-{uname}"

        if node.execute(f"grep CONFIG_HYPERV_STORAGE=y {configPath}").exit_code == 0:
            hvModules.remove("hv_storvsc")
        if node.execute(f"grep CONFIG_HYPERV_NET=y {configPath}").exit_code == 0:
            hvModules.remove("hv_netvsc")
        if node.execute(f"grep CONFIG_HYPERV=y {configPath}").exit_code == 0:
            hvModules.remove("hv_vmbus")
        if node.execute(f"grep CONFIG_HYPERV_UTILS=y {configPath}").exit_code == 0:
            hvModules.remove("hv_utils")
        if node.execute(f"grep CONFIG_HID_HYPERV_MOUSE=y {configPath}").exit_code == 0:
            hvModules.remove("hid_hyperv")

        return hvModules

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the list of given LIS kernel modules and verify if the version
        matches with the Linux kernel release number.
        """,
        priority=0,
    )
    def verify_lis_modules_version(
        self, case_name: str, log: Logger, node: RemoteNode
    ) -> None:
        if not (isinstance(node.os, CentOs) or isinstance(node.os, Redhat)):
            log.info("Distro not supported")
            raise SkippedException

        # TODO: rpm check if LIS is installed
        # TODO: Check LIS version
        hvModules = ["hv_storvsc", "hv_netvsc", "hv_vmbus", "hv_utils", "hid_hyperv"]
        modinfo = node.tools[Modinfo]
        print("Module versions:")
        for module in hvModules:
            print(f"{module}: {modinfo.get_version(module)}")

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the presence of all LIS modules
        """,
        priority=0,
    )
    def lis_modules_check(self, case_name: str, log: Logger, node: RemoteNode) -> None:
        hvModules = self.get_modules(node)

        # TODO: Special checks for RHEL and CentOS

        presentModules = 0
        output = node.execute("lsmod").stdout
        for module in hvModules:
            if module in output:
                log.info(f"Module {module} present")
                presentModules = presentModules + 1
            else:
                log.error(f"Module {module} absent")

        print(f"{len(hvModules)} == {presentModules}")
        assert_that(presentModules, "Not all LIS modules are present.").is_equal_to(
            len(hvModules)
        )

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the list of given LIS kernel modules and verify if the version
        matches with the Linux kernel release number.
        """,
        priority=0,
    )
    def initrd_modules_check(
        self, case_name: str, log: Logger, node: RemoteNode
    ) -> None:
        hvModules = self.get_modules(node)
        uname = node.execute("uname -r").stdout
        # TODO: Install dracut
        node.execute("dracut -f", sudo=True)
        node.execute("rm -rf /root/initrd", sudo=True)
        node.execute("mkdir /root/initrd", sudo=True)
        node.execute(f"cp /boot/initrd-{uname} /root/initrd/boot.img", sudo=True)
        node.execute("cd /root/initrd", sudo=True)
        node.execute(
            "gunzip -c boot.img | cpio -i -d -H newc --no-absolute-filenames",
            shell=True,
            sudo=True,
        )
        for module in hvModules:
            print(module)
