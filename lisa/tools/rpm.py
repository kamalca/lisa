# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Any

from lisa.executable import Tool


class Rpm(Tool):
    @property
    def command(self) -> str:
        return self._command

    def _initialize(self, *args: Any, **kwargs: Any) -> None:
        self._command = "rpm"

    def is_package_installed(
        self,
        package_name: str,
        force_run: bool = False,
        no_info_log: bool = True,
        no_error_log: bool = True,
    ) -> bool:
        """
        Runs rpm -qa and then seaches the output to see if
        package_name is a substring of any of the package names.
        """
        result = self.run(
            "-qa",
            force_run=force_run,
            no_info_log=no_info_log,
            no_error_log=no_error_log,
        )
        if result.exit_code != 0:
            self._log.error("RPM command failed.")
            return False

        packages = result.stdout.split("\n")

        return any(package_name in package for package in packages)
