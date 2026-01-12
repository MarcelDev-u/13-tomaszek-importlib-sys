#!/usr/bin/env python3
from __future__ import annotations

import sys
import importlib.abc
import importlib.util


class DemoFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """
    This finder/loader synthesizes module "demo_hook" without any file on disk.
    It demonstrates the real import pipeline: meta_path -> spec -> loader -> sys.modules.
    """

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "demo_hook":
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        # Returning None uses default module creation
        return None

    def exec_module(self, module):
        module.VALUE = 123
        module.hello = lambda: "hook works"
        module.__doc__ = "Synthetic module created at import time by DemoFinder"


def main() -> int:
    print("[before] demo_hook in sys.modules:", "demo_hook" in sys.modules)

    print("[install] inserting DemoFinder at sys.meta_path[0]")
    sys.meta_path.insert(0, DemoFinder())

    print("[meta_path] current finders order:")
    for f in sys.meta_path[:5]:
        print(" -", type(f).__name__)

    print("[import] importing demo_hook")
    import demo_hook  # type: ignore

    print("[after] demo_hook in sys.modules:", "demo_hook" in sys.modules)
    print("[demo_hook] VALUE =", demo_hook.VALUE)
    print("[demo_hook] hello() =", demo_hook.hello())
    print("[demo_hook] __doc__ =", demo_hook.__doc__)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
