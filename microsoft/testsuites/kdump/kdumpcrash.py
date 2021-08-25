# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import PurePosixPath
from random import randint

from assertpy import assert_that

from lisa import (
    Logger,
    Node,
    SkippedException,
    TestCaseMetadata,
    TestSuite,
    TestSuiteMetadata,
    UnsupportedDistroException,
    node_requirement,
    schema,
)
from lisa.operating_system import Redhat
from lisa.tools import Dmesg, Lscpu, Uname
from lisa.tools.kdump import Kdump


@TestSuiteMetadata(
    area="kdump",
    category="functional",
    description="""
    This test suite is used to check if kernel crash dmup is effect, which is judged by
    if vmcore file is generated after triggering kdump by sysrq.

    Steps:
    1. Check if vmbus version, kernel configurations is supported for crash dump.
    2. Specify the memory reserved for kdump kernel in kernel cmdline, setting the
         crashkernel= option to the required value.
        a. Modify the grub config file to add crashkrenel option or change the value to
            the required one. (For Redhat 8, no need to modify grub config file. It can
            specify crashkernel by using grubby command directly)
        b. Update grub config
    3. Reboot system to make kdump effect.
    4. Check if the crash kernel is loaded.
        a. Check if kernel cmdline has crashkernel option and the value is expected.
        b. Check if /sys/kernel/kexec_crash_loaded file exists and the value is '1'.
        c. Check if /proc/iomem is reserved memory for crash kernel
    5. Trigger kdump through 'echo c > /proc/sysrq-trigger'
    6. Check if vmcore or dump file is generated under'/var/crash' after system boot up.

    It has 6 test cases in this test suite. They verfy if the kdump is effect when:
        1. with different vcpu count.
        2. having crash on different vcpu.
        3. the crashkernel is set auto.
    """,
)
class KdumpCrash(TestSuite):
    crash_kernel = "512M"
    activate_sysrq_cmd = "echo 1 > /proc/sys/kernel/sysrq"
    trigger_kdump_cmd = "echo c > /proc/sysrq-trigger"
    timeout_of_dump_crash = 60

    def _get_boot_config_path(self, node: Node) -> str:
        uname_tool = node.tools[Uname]
        kernel_ver = uname_tool.get_linux_information().kernel_version
        config_path = f"/boot/config-{kernel_ver}"
        assert_that(node.shell.exists(PurePosixPath(config_path))).described_as(
            f"/boot/config-{kernel_ver} not exist. "
            "Please check if the kernel version is right."
        ).is_true()
        return config_path

    def _check_supported(self, node: Node) -> None:
        # Check the VMBus version for kdump supported
        dmesg = node.tools[Dmesg]
        vmbus_major_version = dmesg.get_vmbus_version()
        if vmbus_major_version == "" or int(vmbus_major_version) < 3:
            raise SkippedException(
                "No negotiated VMBus version. "
                "Kernel might be old or patches not included. "
                "Full support for kdump is not present."
            )

        # Below code aims to check the kernel config for "auto crashkernel" supported.
        # Rehat/Centos has this "auto crashkernel" feature. For version 7, it needs the
        # CONFIG_KEXEC_AUTO_RESERVE. For version 8, the ifdefine of that config is
        # removed. For these changes we can refer to Centos kernel, gotten according
        # to https://wiki.centos.org/action/show/Sources?action=show&redirect=sources
        # In addiation, we didn't see upstream kernel has the auto crashkernel feature.
        # It may be a patch owned by Redhat/Centos.
        config_path = self._get_boot_config_path(node)
        if not (
            isinstance(node.os, Redhat) and node.os.information.version >= "8.0.0-0"
        ):
            result = node.execute(
                f"grep CONFIG_KEXEC_AUTO_RESERVE=y {config_path}", shell=True
            )
            if self.crash_kernel == "auto" and result.exit_code != 0:
                raise SkippedException("crashkernel=auto doesn't work for the distro.")

        # Check the kernel config for kdump supported
        kdump = node.tools[Kdump]
        kdump.check_required_kernel_config(config_path)

    def _kdump_test(self, node: Node, log: Logger) -> None:
        try:
            self._check_supported(node)
        except UnsupportedDistroException as identifier:
            raise SkippedException(identifier)

        kdump = node.tools[Kdump]
        kdump.config_crashkernel_memory(self.crash_kernel)
        kdump.enable_kdump_service()

        node.execute(
            f"mkdir -p {kdump.dump_path} && rm -rf {kdump.dump_path}/*",
            shell=True,
            sudo=True,
        ).assert_exit_code()

        # Reboot system to make kdump take effect
        node.reboot()

        # Confirm that the kernel dump mechanism is enabled
        assert_that(
            kdump.is_crashkernel_loaded(self.crash_kernel),
            description="crashkernel is not loaded",
        ).is_equal_to(True)

        # Activate the magic SysRq option
        node.execute(self.activate_sysrq_cmd, shell=True, sudo=True).assert_exit_code(
            message="Failed to set sysrq"
        )

        try:
            # Trigger kdump. After execute the trigger cmd, the VM will be disconnected.
            # We set the timeout 60s. Normally, the VM will start up after 60s.
            node.execute(
                self.trigger_kdump_cmd,
                shell=True,
                sudo=True,
                timeout=self.timeout_of_dump_crash,
            )
        except Exception as identifier:
            log.debug(f"ignorable ssh exception: {identifier}")

        node.close()
        node.initialize()
        # Verify if the kernel panic process creates a vmcore file of size 10M+
        assert_that(
            kdump.is_vmcore_exist(),
            description="No file was found in /var/crash of size greater than 10M",
        ).is_equal_to(True)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when VM has one vcpu
        """,
        priority=1,
        requirement=node_requirement(
            node=schema.NodeSpace(core_count=1, memory_mb=3584),
        ),
    )
    def kdumpcrash_validate_single_core(self, node: Node, log: Logger) -> None:
        self._kdump_test(node, log)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when VM has two vcpu
        """,
        priority=1,
        requirement=node_requirement(
            node=schema.NodeSpace(core_count=2),
        ),
    )
    def kdumpcrash_validate_smp(self, node: Node, log: Logger) -> None:
        self._kdump_test(node, log)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when crashkernel is set auto
        """,
        priority=1,
    )
    def kdumpcrash_validate_auto_size(self, node: Node, log: Logger) -> None:
        self.crash_kernel = "auto"
        self._kdump_test(node, log)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when VM has 4 vcpu and triggers
        crash on one of them.
        """,
        priority=1,
        requirement=node_requirement(
            node=schema.NodeSpace(core_count=4),
        ),
    )
    def kdumpcrash_validate_different_vcpu(self, node: Node, log: Logger) -> None:
        lscpu = node.tools[Lscpu]
        core_count = lscpu.get_core_count()
        random_cpu = randint(0, core_count - 1)
        self.trigger_kdump_cmd = f"taskset -c {random_cpu} echo c > /proc/sysrq-trigger"
        self._kdump_test(node, log)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when VM has 16 vcpu
        """,
        priority=1,
        requirement=node_requirement(
            node=schema.NodeSpace(core_count=16),
        ),
    )
    def kdumpcrash_validate_16_cores(self, node: Node, log: Logger) -> None:
        self._kdump_test(node, log)

    @TestCaseMetadata(
        description="""
        This test case verfiy if the kdump is effect when VM has 96 vcpu and triggers
        crash on one of them.
        """,
        priority=1,
        requirement=node_requirement(
            node=schema.NodeSpace(core_count=96),
        ),
    )
    def kdumpcrash_validate_large_cores(self, node: Node, log: Logger) -> None:
        lscpu = node.tools[Lscpu]
        core_count = lscpu.get_core_count()
        random_cpu = randint(0, core_count - 1)
        self.trigger_kdump_cmd = f"taskset -c {random_cpu} echo c > /proc/sysrq-trigger"
        self.timeout_of_dump_crash = 90
        self._kdump_test(node, log)
