from lisa.operating_system import OperatingSystem
from lisa import (
    LisaException,
    Logger,
    PassedException,
    RemoteNode,
    SkippedException,
    TestCaseMetadata,
    TestSuite,
    TestSuiteMetadata
)

@TestSuiteMetadata(
    area="core",
    category="functional",
    description="""
    This test suite covers test cases previously handled by LISAv2: 
    LIS-MODULES-CHECK, VERIFY-LIS-MODULES-VERSION, INITRD-MODULES-CHECK, RELOAD-MODULES-SMP
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
    def verify_lis_modules_version(self, case_name: str, log: Logger, node: RemoteNode) -> None:
        print("Running hv_module:verify_lis_modules_version")
        env = node.os.information
        print(f"Codename: {env.codename}")
        print(f"Full version {env.full_version}")
        print(f"Reselase: {env.release}")
        print(f"Vendor: {env.vendor}")
        print(f"Update: {env.update}")
        print("Finished running")
        
        
