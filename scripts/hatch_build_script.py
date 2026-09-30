from __future__ import annotations

import sys
import sysconfig
import os

sys.path.insert(0, os.path.dirname(__file__))

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from install_dependencies import main

class BuildHook(BuildHookInterface):
    BIN_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "mikeio1d", "bin")

    def initialize(self, version, build_data):
        if not self._binaries_exist():
            main()
        self.update_build_data(build_data)

    def _binaries_exist(self):
        return any(f.endswith(".dll") for f in os.listdir(self.BIN_DIR) if os.path.isfile(os.path.join(self.BIN_DIR, f)))

    def update_build_data(self, build_data):
        tag = build_data.get("tag", None)
        build_data["tag"] = self.update_tag_platform(tag)
        build_data["artifacts"] = [
            "src/mikeio1d/bin/**/*.dll",
            "src/mikeio1d/bin/**/*.pfs",
            "src/mikeio1d/bin/**/*.ubg",
            "src/mikeio1d/bin/**/*.xml",
            "src/mikeio1d/bin/**/*.so",
            "src/mikeio1d/bin/**/*so.5",
            "src/mikeio1d/bin/DHI.Mike1D.MikeIO/**/*",
        ]

    def update_tag_platform(self, tag: str | None) -> str:
        DEFAULT_TAG = "py3-none-any"
        if tag is None:
            tag = DEFAULT_TAG 
        platform = self._get_platform()
        return self._replace_platform_part_of_tag(tag, platform)

    def _replace_platform_part_of_tag(self, tag: str, platform: str):
        TAG_DELIMITER = "-"
        tag = tag.split(TAG_DELIMITER)
        tag[-1] = platform
        return TAG_DELIMITER.join(tag)

    def _get_platform(self):
        platform = sysconfig.get_platform()
        if platform.startswith("linux"):
            return "manylinux2010_x86_64"
        elif platform.startswith("win"):
            return "win_amd64"
        else:
            raise Exception(f"Unsupported platform: {platform}")
        