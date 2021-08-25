# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import PurePath, PurePosixPath
from typing import List, Type

from retry import retry

from lisa.base_tools import Cat, Sed
from lisa.executable import Tool
from lisa.operating_system import Debian, Posix, Redhat, Suse
from lisa.tools.service import Service
from lisa.tools.sysctl import Sysctl
from lisa.util import LisaException, UnsupportedDistroException


class Kexec(Tool):
    """
    kexec - directly boot into a new kernel
    kexec is a system call that enables you to load and boot into another
    kernel from the currently running kernel. The primary difference between
    a standard system boot and a kexec boot is that the hardware initialization
    normally performed by the BIOS or firmware (depending on architecture)
    is not performed during a kexec boot. This has the effect of reducing the
    time required for a reboot.
    """

    @property
    def command(self) -> str:
        return "kexec"

    @property
    def can_install(self) -> bool:
        return True

    def _install(self) -> bool:
        assert isinstance(self.node.os, Posix)
        self.node.os.install_packages("kexec-tools")
        return self._check_exists()


class Makedumpfile(Tool):
    """
    makedumpfile - make a small dumpfile of kdump
    With kdump, the memory image of the first kernel can be taken as vmcore
    while the second kernel is running. makedumpfile makes a small DUMPFILE by
    compressing dump data or by excluding unnecessary pages for analysis, or both.
    """

    @property
    def command(self) -> str:
        return "makedumpfile"

    @property
    def can_install(self) -> bool:
        return True

    def _install(self) -> bool:
        assert isinstance(self.node.os, Posix)
        if isinstance(self.node.os, Redhat):
            self.node.os.install_packages("kexec-tools")
        else:
            self.node.os.install_packages("makedumpfile")
        return self._check_exists()


class Kdump(Tool):
    """
    kdump is a feature of the Linux kernel that creates crash dumps in the event of a
    kernel crash. When triggered, kdump exports a memory image (also known as vmcore)
    that can be analyzed for the purposes of debugging and determining the cause of a
    crash.

    kdump tool manages the kdump feature of the Linux kernel. Different distro os has
    different kdump tool.

    We can support Redhat, Suse, Debian family distro now. We will add support for
    other distros.
    """

    # If the file /sys/kernel/kexec_crash_loaded does not exist. This means that the
    # currently running kernel either was not configured to support kdump, or that a
    # crashkernel= commandline parameter was not used when the currently running kernel
    # booted. Value "1" means crash kernel is loaded, otherwise not loaded.
    #
    # It also has /sys/kernel/kexec_crash_size file, which record the crash kernel size
    # of memory reserved. We don't need to check this file in our test case.
    kexec_crash = "/sys/kernel/kexec_crash_loaded"

    # This file shows you the current map of the system's memory for each physical
    # device. We can check /proc/iomem file for memory reserved for crash kernel.
    iomem = "/proc/iomem"

    # Following are the configuration setting required for system and dump-capture
    # kernels for enabling kdump support.
    required_kernel_config = [
        "CONFIG_KEXEC",
        "CONFIG_CRASH_DUMP",
        "CONFIG_PROC_VMCORE",
    ]

    dump_path = "/var/crash"

    @property
    def dependencies(self) -> List[Type[Tool]]:
        return [Kexec, Makedumpfile]

    @property
    def command(self) -> str:
        if isinstance(self.node.os, Redhat):
            return "kdumpctl"
        elif isinstance(self.node.os, Debian):
            return "kdump-config"
        elif isinstance(self.node.os, Suse):
            return "kdumptool"
        else:
            raise UnsupportedDistroException(
                "Unsupported distro "
                f"{self.node.os.name} {self.node.os.information.version}"
            )

    @property
    def can_install(self) -> bool:
        return True

    def _install(self) -> bool:
        if isinstance(self.node.os, Redhat):
            self.node.os.install_packages("kexec-tools")
        elif isinstance(self.node.os, Debian):
            self.node.os.install_packages("kdump-tools")
        elif isinstance(self.node.os, Suse):
            self.node.os.install_packages("kdump")
        else:
            raise UnsupportedDistroException(
                "Unsupported distro "
                f"{self.node.os.name} {self.node.os.information.version}"
            )
        return self._check_exists()

    def check_required_kernel_config(self, config_path: str) -> None:
        for config in self.required_kernel_config:
            result = self.node.execute(f"grep {config}=y {config_path}")
            result.assert_exit_code(
                message=f"The kernel config {config} is not set."
                "Kdump is not supported."
            )

    def _get_crashkernel_cfg_file(self) -> str:
        if isinstance(self.node.os, Debian):
            cfg_file = "/etc/default/grub.d/kdump-tools.cfg"
        elif (
            isinstance(self.node.os, Redhat)
            and self.node.os.information.version >= "8.0.0-0"
        ):
            # For Redhat 8 and later version, we can use grubby command to config
            # crashkernel. No need to get the crashkernel cfg file
            cfg_file = ""
        else:
            cfg_file = "/etc/default/grub"

        if cfg_file:
            assert self.node.shell.exists(PurePosixPath(cfg_file)), (
                f"{cfg_file} doesn't exist. Please check the right grub file for "
                f"{self.node.os.name} {self.node.os.information.version}."
            )
        return cfg_file

    def _get_crashkernel_update_cmd(self, crashkernel: str) -> str:
        """
        After setting crashkernel into grub cfg file, need updating grub configuration.
        This function returns the update command string. For Redhat 8 and later version
        use grubby command to set crashkernel.
        """
        if isinstance(self.node.os, Debian):
            cmd = "update-grub"
        elif isinstance(self.node.os, Redhat):
            if self.node.os.information.version >= "8.0.0-0":
                cmd = f'grubby --update-kernel=ALL --args="crashkernel={crashkernel}"'
            else:
                if self.node.shell.exists(PurePath("/sys/firmware/efi")):
                    # System with UEFI firmware
                    cmd = "grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg"
                else:
                    # System with BIOS firmware
                    cmd = "grub2-mkconfig -o /boot/grub2/grub.cfg"
        else:
            cmd = "grub2-mkconfig -o /boot/grub2/grub.cfg"
        return cmd

    def config_crashkernel_memory(
        self,
        crashkernel: str,
    ) -> None:

        cfg_file = self._get_crashkernel_cfg_file()
        update_cmd = self._get_crashkernel_update_cmd(crashkernel)
        cat = self.node.tools[Cat]
        sed = self.node.tools[Sed]

        # For Redhat 8 and later version, the cfg_file should be "".
        if cfg_file != "":
            result = cat.run(cfg_file)
            if "crashkernel" in result.stdout:
                sed.substitute(
                    match_lines="^GRUB_CMDLINE_LINUX",
                    regexp='crashkernel=[^[:space:]"]*',
                    replacement=f"crashkernel={crashkernel}",
                    file=cfg_file,
                    sudo=True,
                )
            else:
                sed.substitute(
                    match_lines="^GRUB_CMDLINE_LINUX",
                    regexp='"$',
                    replacement=f" crashkernel={crashkernel}",
                    file=cfg_file,
                    sudo=True,
                )
            # Check if crashkernel is insert in cfg file
            result = cat.run(cfg_file, force_run=True)
            if f"crashkernel={crashkernel}" not in result.stdout:
                raise LisaException(f'No "crashkernel={crashkernel}" in {cfg_file}')

        # Update grub
        result = self.node.execute(update_cmd, sudo=True)
        result.assert_exit_code(message="Failed to update grub")

    def enable_kdump_service(self) -> None:
        service = self.node.tools[Service]
        if isinstance(self.node.os, Redhat) or isinstance(self.node.os, Suse):
            service.enable_service("kdump")
        elif isinstance(self.node.os, Debian):
            service.enable_service("kdump-tools")
        else:
            raise UnsupportedDistroException(
                "Unsupported distro "
                f"{self.node.os.name} {self.node.os.information.version}"
            )

    def set_unknown_nmi_panic(self) -> None:
        nmi_panic_file = PurePath("/proc/sys/kernel/unknown_nmi_panic")
        if self.node.shell.exists(nmi_panic_file):
            sysctl = self.node.tools[Sysctl]
            sysctl.write("kernel.unknown_nmi_panic", "1")

    @retry(exceptions=LisaException, tries=60, delay=1)  # type: ignore
    def check_kexec_crash_loaded(self) -> None:
        cat = self.node.tools[Cat]
        result = cat.run(self.kexec_crash, force_run=True)
        if "1" != result.stdout:
            raise LisaException(f"{self.kexec_crash} file's value is not 1.")

    def is_crashkernel_loaded(self, crashkernel_memory: str) -> bool:
        # Check crashkernel parameter in cmdline
        cat = self.node.tools[Cat]
        result = cat.run("/proc/cmdline", force_run=True)
        if f"crashkernel={crashkernel_memory}" not in result.stdout:
            self._log.error(
                f"crashkernel={crashkernel_memory} boot parameter is not present in"
                "kernel cmdline"
            )
            return False

        # Check crash kernel loaded
        if not self.node.shell.exists(PurePosixPath(self.kexec_crash)):
            self._log.error(
                f"{self.kexec_crash} file doesn't exist. Kexec crash is not loaded."
            )
            return False

        # Sometimes it cost a while to load the value.
        self.check_kexec_crash_loaded()

        # Check crash kernel memory reserved
        result = cat.run(self.iomem, force_run=True)
        if "Crash kernel" not in result.stdout:
            self._log.error(
                f"No 'Crash' in {self.iomem}. Memory isn't reserved for crash kernel"
            )
            return False
        return True

    def is_vmcore_exist(self) -> bool:
        if isinstance(self.node.os, Debian):
            cmd = f"find {self.dump_path}/2* -type f -size +10M"
        else:
            cmd = f"find {self.dump_path}/*/vmcore -type f -size +10M"
        result = self.node.execute(cmd, shell=True, sudo=True)
        if result.exit_code != 0:
            self._log.error(
                "No file was found in /var/crash of size greater than 10M. "
                f"{result.stdout}"
            )
            return False
        return True
