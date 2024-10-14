import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from install_dependencies import main

class BuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        main()