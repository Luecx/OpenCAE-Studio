from __future__ import annotations

import subprocess
from pathlib import Path


class FEMasterIntrospection:
    def __init__(self, executable): self.executable = Path(executable)
    def list_commands(self): return self._run("--doc-list").splitlines()
    def show(self, command): return self._run("--doc-show", command)
    def tokens(self, name): return self._run("--doc-tokens", name)
    def variants(self, name): return self._run("--doc-variants", name)
    def _run(self, *args):
        result = subprocess.run([str(self.executable), *args], capture_output=True, text=True, check=True)
        return result.stdout
