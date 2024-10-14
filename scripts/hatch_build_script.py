import sys
<<<<<<< Updated upstream
=======
import sysconfig
>>>>>>> Stashed changes
import os

sys.path.insert(0, os.path.dirname(__file__))

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from install_dependencies import main

class BuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
<<<<<<< Updated upstream
        main()
=======
        main()
        self.update_build_data(build_data)

    def update_build_data(self, build_data):
        tag = build_data.get("tag", None)
        build_data["tag"] = self.update_tag_platform(tag)

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
        
>>>>>>> Stashed changes
