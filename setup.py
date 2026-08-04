import os
from pathlib import Path

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.install_lib import install_lib

PROJECT_ROOT = Path(__file__).resolve().parent
PTH_SOURCE = PROJECT_ROOT / "src" / "procitec_weasyprint_libs.pth"
PTH_NAME = "procitec_weasyprint_libs.pth"


class InstallLibWithPth(install_lib):
    """Install the activation .pth directly into site-packages."""

    def run(self):
        super().run()

        destination = Path(self.install_dir) / PTH_NAME
        self.mkpath(str(destination.parent))
        self.copy_file(str(PTH_SOURCE), str(destination))

    def get_outputs(self):
        outputs = super().get_outputs()
        outputs.append(os.path.join(self.install_dir, PTH_NAME))
        return outputs


class PlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        platform_tag = os.environ.get("WHEEL_PLATFORM_TAG")
        if not platform_tag:
            return super().get_tag()

        return "py3", "none", platform_tag


setup(
    cmdclass={
        "install_lib": InstallLibWithPth,
        "bdist_wheel": PlatformWheel,
    }
)
