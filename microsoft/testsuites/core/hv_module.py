# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata


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
        pass

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the presence of all LIS modules
        """,
        priority=0,
    )
    def lis_modules_check(self, case_name: str, log: Logger, node: RemoteNode) -> None:
        uname = node.execute("uname -r").stdout
        configPath = f"/boot/config-{uname}"
        hvModules = ["hv_storvsc", "hv_netvsc", "hv_vmbus", "hv_utils", "hid_hyperv"]
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
