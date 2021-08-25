# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from typing import List

from lisa.executable import Tool
from lisa.util import LisaException
from lisa.util.process import ExecutableResult


class Dmesg(Tool):
    # meet any pattern will be considered as potential error line.
    __errors_patterns = [
        re.compile("Call Trace"),
        re.compile("rcu_sched self-detected stall on CPU"),
        re.compile("rcu_sched detected stalls on"),
        re.compile("BUG: soft lockup"),
    ]

    __vmbus_vesion_pattern = re.compile(
        r"^\[\s+\d+.\d+\]\s+hv_vmbus:\s+Vmbus version:(?P<major>\d+).(?P<minor>\d+)"
    )

    @property
    def command(self) -> str:
        return "dmesg"

    def _check_exists(self) -> bool:
        return True

    def get_output(self, force_run: bool = False) -> str:
        command_output = self._run(force_run=force_run)
        return command_output.stdout

    def check_kernel_errors(
        self,
        force_run: bool = False,
        throw_error: bool = True,
    ) -> str:
        command_output = self._run(force_run=force_run)
        if command_output.exit_code != 0:
            raise LisaException(f"exit code should be zero: {command_output.exit_code}")
        matched_lines: List[str] = []
        for line in command_output.stdout.splitlines(keepends=False):
            for pattern in self.__errors_patterns:
                if pattern.search(line):
                    matched_lines.append(line)
                    # match one rule, so skip for other patterns
                    break
        result = "\n".join(matched_lines)
        if result:
            # log first line only, in case it's too long
            error_message = (
                f"dmesg error with {len(matched_lines)} lines, "
                f"first line: '{matched_lines[0]}'"
            )
            if throw_error:
                raise LisaException(error_message)
            else:
                self._log.debug(error_message)
        return result

    def get_vmbus_version(self) -> str:
        output = self._run()
        output.assert_exit_code(
            message=f"exit code should be zero, but actually {output.exit_code}"
        )
        for line in output.stdout.splitlines(keepends=False):
            matched_vmbus_version = self.__vmbus_vesion_pattern.match(line)
            if matched_vmbus_version:
                major = matched_vmbus_version.group("major")
                minor = matched_vmbus_version.group("minor")
                self._log.info(f"vmbus version is {major}.{minor}")
                return major
        self._log.info("No vmbus version in dmesg")
        return ""

    def _run(self, force_run: bool = False) -> ExecutableResult:
        # sometime it need sudo, we can retry
        # so no_error_log for first time
        result = self.run(force_run=force_run, no_error_log=True)
        if result.exit_code != 0:
            # may need sudo
            result = self.run(sudo=True)
        self._cached_result = result
        return result
