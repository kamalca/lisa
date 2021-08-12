# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa.tools.docker import Docker
from pathlib import Path

from assertpy import assert_that

from lisa import (
    Node,
    SkippedException,
    TestCaseMetadata,
    TestSuite,
    TestSuiteMetadata,
)

@TestSuiteMetadata(
    area="container",
    category="functional",
    description="""
    This test suite runs the docker test cases.
    """,
)
class docker(TestSuite):

    @TestCaseMetadata(
        description="""
            This test case ...

            Steps:
            1. x
            2. x
        """,
        priority=2,
    )
    def _generate_java_program():
        docker_tool = node.tools[Docker]
        pass

    @TestCaseMetadata(
        description="""
            This test case ...

            Steps:
            1. x
            2. x
        """,
        priority=2,
    )
    def _generate_docker_file():
        docker_tool = node.tools[Docker]
        pass

    @TestCaseMetadata(
        description="""
            This test case ...

            Steps:
            1. x
            2. x
        """,
        priority=2,
    )
    def _evaluate_test_results():
        docker_tool = node.tools[Docker]
        pass


    def before_suite(self, **kwargs: Any) -> None:
        pass

    def after_suite(self, **kwargs: Any) -> None:
        pass

    def before_case(self, **kwargs: Any) -> None:
        pass

    def after_case(self, **kwargs: Any) -> None:
        pass