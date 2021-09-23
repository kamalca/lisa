# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from assertpy import assert_that
from semver import VersionInfo

from lisa import Logger, RemoteNode, TestCaseMetadata, TestSuite, TestSuiteMetadata
from lisa.operating_system import Redhat
from lisa.sut_orchestrator.azure.tools import LisDriver
from lisa.tools import Lsmod, Modinfo, Modprobe, Uname
from lisa.util import SkippedException


@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite covers test cases previously handled by LISAv2:
    LIS-MODULES-CHECK, VERIFY-LIS-MODULES-VERSION,
    INITRD-MODULES-CHECK, RELOAD-MODULES-SMP

    It is responsible for ensuring the Hyper V drivers are all present,
    are included in initrd, and are all the same version.
    """,
)
class HvModule(TestSuite):
    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the list of given LIS kernel modules and verify if the version
           matches with the Linux kernel release number. (Drivers loaded directly in
           to the kernel are skipped)
        """,
        priority=0,
    )
    def verify_lis_modules_version(
        self, case_name: str, log: Logger, node: RemoteNode
    ) -> None:
        if not isinstance(node.os, Redhat):
            log.info(f"{node.os.name} not supported.")
            raise SkippedException("This test case only supports Redhat distros.")

        lis_driver = node.tools[LisDriver]
        lis_version = lis_driver.get_version()
        hv_modules = self.__get_modules_not_in_kernel(node)
        lis_installed = node.os.package_exists("microsoft-hyper-v")

        if lis_installed:
            modinfo = node.tools[Modinfo]
            for module in hv_modules:
                module_version = VersionInfo.parse(modinfo.get_version(module))
                assert_that(module_version).described_as(
                    f"Version of {module} does not match LIS version"
                ).is_equal_to(lis_version)

    @TestCaseMetadata(
        description="""
        This test case will
        1. Verify the presence of all Hyper V drivers using lsmod
           to look for the drivers not directly loaded into the kernel.
        """,
        priority=0,
    )
    def verify_hyperv_modules(
        self, case_name: str, log: Logger, node: RemoteNode
    ) -> None:
        hv_modules = self.__get_modules_not_in_kernel(node)
        distro_version = node.os.information.version

        # Some versions of RHEL and CentOS have the LIS package installed
        #   which includes extra drivers
        if isinstance(node.os, Redhat):
            modprobe = node.tools[Modprobe]
            lis_installed = node.os.package_exists("microsoft-hyper-v")

            if lis_installed:
                hv_modules.append("pci_hyperv")
                modprobe.run("pci_hyperv", sudo=True)

            if (
                distro_version >= "7.3.0" or distro_version < "7.5.0"
            ) and lis_installed:
                hv_modules.append("mlx4_en")
                modprobe.run("mlx4_en", sudo=True)

        # Counts the Hyper V drivers loaded as modules
        num_modules_loaded = 0
        lsmod = node.tools[Lsmod]
        for module in hv_modules:
            if lsmod.module_exists(module):
                log.info(f"Module {module} present")
                num_modules_loaded = num_modules_loaded + 1
            else:
                log.error(f"Module {module} absent")

        num_modules_expected = len(hv_modules)
        assert_that(num_modules_loaded).described_as(
            "Not all Hyper V drivers are present."
        ).is_equal_to(num_modules_expected)

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
        hv_modules = self.__get_modules_not_in_kernel(node)
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

    def __get_modules_not_in_kernel(self, node: RemoteNode) -> list[str]:
        """
        Returns the hv_modules that are not directly loaded into the kernel.
        """
        hv_modules_configuration = {
            "hv_storvsc": "CONFIG_HYPERV_STORAGE",
            "hv_netvsc": "CONFIG_HYPERV_NET",
            "hv_vmbus": "CONFIG_HYPERV",
            "hv_utils": "CONFIG_HYPERV_UTILS",
            "hid_hyperv": "CONFIG_HID_HYPERV_MOUSE",
            "hv_balloon": "CONFIG_HYPERV_BALLOON",
            "hyperv_keyboard": "CONFIG_HYPERV_KEYBOARD",
        }
        uname = node.tools[Uname]
        kernel_version = uname.get_linux_information().kernel_version_raw
        config_path = f"/boot/config-{kernel_version}"

        for module in hv_modules_configuration:
            if (
                node.execute(
                    f"grep {hv_modules_configuration[module]}=y {config_path}"
                ).exit_code
                == 0
            ):
                hv_modules_configuration.pop(module)

        return [*hv_modules_configuration]
