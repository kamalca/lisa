# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.operating_system import CentOs, Redhat
from lisa.tools import Dmesg, Lsmod, Modinfo, Modprobe, Rpm, Uname
from lisa.util import SkippedException


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
        """
        Returns the hv_modules that are not directly loaded into the kernel.
        """
        hv_modules = [
            "hv_storvsc",
            "hv_netvsc",
            "hv_vmbus",
            "hv_utils",
            "hid_hyperv",
            "hv_baloon",
            "hyperv_keyboard",
        ]
        uname = node.tools[Uname]
        kernel_version = uname.get_linux_information().kernel_version_raw
        config_path = f"/boot/config-{kernel_version}"

        if node.execute(f"grep CONFIG_HYPERV_STORAGE=y {config_path}").exit_code == 0:
            hv_modules.remove("hv_storvsc")
        if node.execute(f"grep CONFIG_HYPERV_NET=y {config_path}").exit_code == 0:
            hv_modules.remove("hv_netvsc")
        if node.execute(f"grep CONFIG_HYPERV=y {config_path}").exit_code == 0:
            hv_modules.remove("hv_vmbus")
        if node.execute(f"grep CONFIG_HYPERV_UTILS=y {config_path}").exit_code == 0:
            hv_modules.remove("hv_utils")
        if node.execute(f"grep CONFIG_HID_HYPERV_MOUSE=y {config_path}").exit_code == 0:
            hv_modules.remove("hid_hyperv")

        return hv_modules

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

        hv_modules = self.get_modules(node)
        rpm = node.tools[Rpm]
        lis_installed = rpm.is_package_installed("microsoft-hyper-v")

        modinfo = node.tools[Modinfo]
        dmesg = node.tools[Dmesg]
        lis_version = dmesg.get_lis_version()

        if lis_installed:
            for module in hv_modules:
                module_version = modinfo.get_version(module)
                assert_that(lis_version == module_version).described_as(
                    f"Version of {module} is {module_version}, expected {lis_version}"
                ).is_true()

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the presence of all LIS modules
        """,
        priority=0,
    )
    def lis_modules_check(self, case_name: str, log: Logger, node: RemoteNode) -> None:
        hv_modules = self.get_modules(node)
        distro_version = node.os.information.version

        if isinstance(node.os, CentOs) or isinstance(node.os, Redhat):
            rpm = node.tools[Rpm]
            modprobe = node.tools[Modprobe]
            lis_installed = rpm.is_package_installed("microsoft-hyper-v")

            if distro_version >= "4.3.0" and lis_installed:
                hv_modules.append("pci_hyperv")
                modprobe.run("pci_hyperv", sudo=True)

            if (
                distro_version >= "7.3.0" or distro_version < "7.5.0"
            ) and lis_installed:
                dmesg = node.tools[Dmesg]
                lis_version = dmesg.get_lis_version()
                if lis_version >= "4.3.0":
                    hv_modules.append("mlx4_en")
                    modprobe.run("mlx4_en", sudo=True)

        present_modules = 0
        lsmod = node.tools[Lsmod]
        output = lsmod.run().stdout
        for module in hv_modules:
            if module in output:
                log.info(f"Module {module} present")
                present_modules = present_modules + 1
            else:
                log.error(f"Module {module} absent")

        print(f"{len(hv_modules)} == {present_modules}")
        assert_that(present_modules, "Not all LIS modules are present.").is_equal_to(
            len(hv_modules)
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
        hv_modules = self.get_modules(node)
        uname = node.tools[Uname]
        kernel_version = uname.get_linux_information().kernel_version_raw
        # TODO: Install dracut
        node.execute("dracut -f", sudo=True)
        node.execute("rm -rf /root/initrd", sudo=True)
        node.execute("mkdir /root/initrd", sudo=True)
        node.execute(
            f"cp /boot/initrd-{kernel_version} /root/initrd/boot.img", sudo=True
        )
        node.execute("cd /root/initrd", sudo=True)
        node.execute(
            "gunzip -c boot.img | cpio -i -d -H newc --no-absolute-filenames",
            shell=True,
            sudo=True,
        )
        for module in hv_modules:
            print(module)
