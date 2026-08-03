import os

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel


class PlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        platform_tag = os.environ.get("WHEEL_PLATFORM_TAG")
        if not platform_tag:
            return super().get_tag()
        return "py3", "none", platform_tag


setup(cmdclass={"bdist_wheel": PlatformWheel})
