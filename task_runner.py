#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


PLUGIN_DIR_DEFAULT = Path("./plugins")


@dataclass
class PluginInfo:
    name: str
    origin: str


def find_spec_origin(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return "NOT FOUND"
    return str(spec.origin)


def print_meta_path() -> None:
    print("[sys.meta_path] import finders order:")
    for f in sys.meta_path:
        print(" -", type(f).__name__)


def list_plugins(plugin_dir: Path) -> list[PluginInfo]:
    plugin_dir = plugin_dir.resolve()
    if not plugin_dir.exists():
        return []

    out: list[PluginInfo] = []
    for p in sorted(plugin_dir.glob("*.py")):
        if p.name.startswith("_"):
            continue
        out.append(PluginInfo(name=p.stem, origin=str(p)))
    return out


def import_by_name(module_name: str) -> ModuleType:
    return importlib.import_module(module_name)


def import_from_file(module_name: str, file_path: Path) -> ModuleType:
    file_path = file_path.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Plugin file not found: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    # Put into sys.modules to make reload and relative imports behave better
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_plugin(target: str, plugin_dir: Path) -> tuple[ModuleType, str]:
    """
    target formats:
      - "hello" -> loads ./plugins/hello.py as module "__plugin__hello"
      - "path:./plugins/hello.py" -> loads plugin from explicit file path
      - "name:json" -> imports a module by import name (stdlib or installed)
    """
    plugin_dir = plugin_dir.resolve()

    if target.startswith("path:"):
        path_str = target[len("path:") :]
        p = Path(path_str)
        mod_name = "__plugin__" + p.stem
        m = import_from_file(mod_name, p)
        return m, f"file:{p.resolve()}"

    if target.startswith("name:"):
        name = target[len("name:") :]
        m = import_by_name(name)
        return m, f"name:{name}"

    # default: plugin name in plugin_dir
    p = plugin_dir / f"{target}.py"
    mod_name = "__plugin__" + target
    m = import_from_file(mod_name, p)
    return m, f"plugin:{p.resolve()}"


def call_plugin(module: ModuleType, argv: list[str]) -> int:
    """
    Plugin convention:
      - must define main(argv: list[str]) -> int
      - or main() -> int
    """
    if not hasattr(module, "main"):
        raise AttributeError("Plugin must define function main(argv) or main()")

    fn = getattr(module, "main")
    try:
        return int(fn(argv))
    except TypeError:
        return int(fn())


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="task_runner.py",
        description="Plugin-based task runner using sys + importlib (dynamic imports).",
    )

    p.add_argument(
        "--plugin-dir",
        default=str(PLUGIN_DIR_DEFAULT),
        help="Directory with single-file plugins (*.py). Default: ./plugins",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List available plugins from plugin-dir.",
    )
    p.add_argument(
        "--where",
        metavar="MODULE",
        help="Show import origin for a module name. Example: --where json",
    )
    p.add_argument(
        "--meta-path",
        action="store_true",
        help="Print sys.meta_path (import finders).",
    )

    sub = p.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="Run a plugin by name or file path.")
    run.add_argument(
        "target",
        help='Plugin name (from plugin-dir), "path:./plugins/x.py", or "name:json".',
    )
    run.add_argument(
        "--reload",
        action="store_true",
        help="Reload module before executing (useful during development).",
    )
    run.add_argument(
        "plugin_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to plugin main(argv). Use -- to separate.",
    )
    return p


def main() -> int:
    parser = build_cli()
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir)

    if args.meta_path:
        print_meta_path()

    if args.where:
        origin = find_spec_origin(args.where)
        print(f"[where] {args.where} -> {origin}")

    if args.list:
        plugs = list_plugins(plugin_dir)
        if not plugs:
            print(f"[list] no plugins found in {plugin_dir.resolve()}")
            print("[list] create ./plugins/hello.py to test")
            return 0
        print(f"[list] plugins in {plugin_dir.resolve()}:")
        for pi in plugs:
            print(f" - {pi.name} ({pi.origin})")
        return 0

    if args.cmd == "run":
        target: str = args.target
        module, label = load_plugin(target, plugin_dir)

        if args.reload:
            try:
                module = importlib.reload(module)
                label += " (reloaded)"
            except Exception as e:
                print("[reload] failed, continuing without reload:", repr(e))

        print(f"[run] loaded: {label}")
        print(f"[run] module.__name__: {module.__name__}")
        print(f"[run] module.__file__: {getattr(module, '__file__', 'builtin')}")

        # separate runner args from plugin args using --
        plugin_argv = [a for a in args.plugin_args if a != "--"]
        return call_plugin(module, plugin_argv)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
