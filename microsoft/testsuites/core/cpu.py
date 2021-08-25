# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import PurePosixPath

from assertpy.assertpy import assert_that

from lisa import Logger, testsuite
from lisa.base_tools.cat import Cat
from lisa.base_tools.uname import Uname
from lisa.node import Node
from lisa.tools.echo import Echo
from lisa.tools.lscpu import Lscpu
from lisa.tools.lsvmbus import Lsvmbus
from lisa.util import BadEnvironmentStateException, PassedException, SkippedException


class CPUState:
    OFFLINE: str = "0"
    ONLINE: str = "1"


hyperv_interrupt_substr = ["hyperv", "Hypervisor", "Hyper-V"]


@testsuite.TestSuiteMetadata(
    area="cpu",
    category="functional",
    description="""
    This test suite is used to run CPU related tests.
    """,
)
class CPU(testsuite.TestSuite):
    def _set_cpu_state(self, cpu_id: str, state: str, node: Node) -> bool:
        file_path = f"/sys/devices/system/cpu/cpu{cpu_id}/online"
        file_exists = node.shell.exists(PurePosixPath(file_path))
        if file_exists:
            node.tools[Echo].write_to_file(state, file_path, shell=True, sudo=True)
        result = node.tools[Cat].read_from_file(file_path, force_run=True, sudo=True)
        return result == state

    @testsuite.TestCaseMetadata(
        description="""
            This test will check that CPU assigned to lsvmbus
            channels cannot be put offline.
            Steps :
            1. Get the list of lsvmbus channel cpu mappings using
            command `lsvmbus -vv`.
            2. Create a set of cpu's assigned to lsvmbus channels.
            3. Try to put cpu offline by running
            `echo 0 > /sys/devices/system/cpu/cpu/<cpu_id>/online`.
            Note : We skip cpu 0 as it handles system interrupts.
            4. Ensure that cpu is still online by checking state '1' in
            `/sys/devices/system/cpu/cpu/<target_cpu>/online`.
            """,
        priority=2,
    )
    def cpu_verify_vmbus_force_online(self, node: Node, log: Logger) -> None:
        cpu_count = node.tools[Lscpu].get_core_count()
        log.debug(f"{cpu_count} CPU cores detected...")

        channels = node.tools[Lsvmbus].get_device_channels_from_lsvmbus()
        mapped_cpu = set()
        for channel in channels:
            for channel_vp_map in channel.channel_vp_map:
                target_cpu = channel_vp_map.target_cpu
                if target_cpu != "0":
                    mapped_cpu.add(target_cpu)

        for target_cpu in mapped_cpu:
            log.debug(f"Checking CPU {target_cpu} on /sys/device/....")
            result = self._set_cpu_state(target_cpu, CPUState.OFFLINE, node)
            if result:
                # Try to bring CPU back to it's original state
                reset = self._set_cpu_state(target_cpu, CPUState.ONLINE, node)
                exception_message = (
                    f"Expected CPU {target_cpu} state : {CPUState.ONLINE}(online), "
                    f"actual state : {CPUState.OFFLINE}(offline). CPU's mapped to "
                    f"LSVMBUS channels shouldn't be in state "
                    f"{CPUState.OFFLINE}(offline)."
                )
                if not reset:
                    raise BadEnvironmentStateException(
                        exception_message,
                        f"The test failed leaving CPU {target_cpu} in a bad state.",
                    )
                raise AssertionError(exception_message)

    @testsuite.TestCaseMetadata(
        description="""
        This test case will check that L3 cache is correctly mapped
        to NUMA node.
        Steps:
        1. Check if NUMA is disabled in commandline. If disabled,
        and kernel version is <= 2.6.37, test is skipped as hyper-v
        has no support for NUMA : https://t.ly/x8k3
        2. Get the mappings using command :
        `lscpu --extended=cpu,node,socket,cache`
        3. Each line in the mapping corresponds to one CPU core. The L3
        cache of each core must be mapped to the NUMA node that core
        belongs to instead of the core itself.

        Example :
        Correct mapping:
        CPU NODE SOCKET L1d L1i L2 L3
        8   0    0      8   8   8  0
        9   1    1      9   9   9  1

        Incorrect mapping:
        CPU NODE SOCKET L1d L1i L2 L3
        8   0    0      8   8   8  8
        9   1    1      9   9   9  9
        """,
        priority=1,
    )
    def l3_cache_check(self, node: Node, log: Logger) -> None:
        cmdline = node.tools[Cat].run("/proc/cmdline").stdout
        if "numa=off" in cmdline:
            uname_result = node.tools[Uname].get_linux_information()
            log.debug("Found numa=off in /proc/cmdline. Checking the kernel version.")
            if uname_result.kernel_version <= "2.6.37":
                raise SkippedException(
                    f"kernel : {uname_result.kernel_version_raw} has numa=off in boot "
                    "parameter and its kernel version is earlier than 2.6.37. "
                    "No support for NUMA setting. https://t.ly/x8k3"
                )

        cpu_info = node.tools[Lscpu].get_cpu_info()
        for cpu in cpu_info:
            assert_that(
                cpu.l3_cache,
                "L3 cache of each core must be mapped to the NUMA node "
                "associated with the core.",
            ).is_equal_to(cpu.numa_node)

    @testsuite.TestCaseMetadata(
        description="""
            This test will verify if the CPUs inside a Linux VM are processing VMBus
            interrupts by checking the /proc/interrupts file.

            Steps:
            1. Looks for the Hyper-v timer property of each CPU under /proc/interrupts
            2. Verifies if atleast one CPU has more than 0 interrupts processed.

            Note: There are 3 types of Hyper-v interrupts : Hypervisor callback
            interrupts, Hyper-V reenlightenment interrupts, and Hyper-V stimer0
            interrupts. We also do not need to have each CPU handle vmbus message
            or event in multi CPUs VM.
            """,
        priority=2,
    )
    def verify_vmbus_interrupts(self, node: Node, log: Logger) -> None:
        found_hyperv_interrupt = False
        cpu_count = node.tools[Lscpu].get_core_count()
        is_cpu_handling_interrupt = [False] * cpu_count
        log.debug(f"{cpu_count} CPU cores detected...")

        interrupts = node.tools[Cat].get_interrupt_data()
        for interrupt in interrupts:
            is_hyperv_interrupt = any(
                [(substr in interrupt.metadata) for substr in hyperv_interrupt_substr]
            )
            found_hyperv_interrupt = found_hyperv_interrupt | is_hyperv_interrupt
            if is_hyperv_interrupt:
                log.debug(f"Hyper-V interrupt : {interrupt}")
                assert_that(
                    len(interrupt.interrupt_count),
                    "Interrupt count should be present for each cpu.",
                ).is_equal_to(cpu_count)
                is_cpu_handling_interrupt = [
                    ((interrupt.interrupt_count[i] > 0) | is_cpu_handling_interrupt[i])
                    for i in range(len(interrupt.interrupt_count))
                ]

        log.debug(f"CPU interrupt handling : {is_cpu_handling_interrupt}")

        # It is not mandatory to have the Hyper-V interrupts present under
        # `/proc/interrupts`. Skip test execution if these are not showing up
        if not found_hyperv_interrupt:
            raise SkippedException("Hyper-V interrupts are not recorded, abort test.")

        # Ensure that atleast one CPU is handling hyper-v interrupts
        is_any_cpu_handling_interrupt = any(is_cpu_handling_interrupt)
        assert_that(
            is_any_cpu_handling_interrupt, "No CPU core is processing VMBUS interrupts!"
        )

        # Pass the test with warning if not all CPU's are processing interrupts
        if sum(is_cpu_handling_interrupt) < cpu_count:
            raise PassedException(
                "Some CPU cores are processing VMBUS interrupts, but it is ok to "
                "miss a few core not processing VMBUS interrupts because of big "
                "size VM."
            )
