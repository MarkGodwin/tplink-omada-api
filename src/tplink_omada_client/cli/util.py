"""Common functionality for multiple commands"""
import argparse

from typing import Any

TARGET_ARG: str = "target"

def assert_target_argument(args: dict[str, Any]) -> str:
    """Throws ArgumentError if target arg missing"""
    if TARGET_ARG not in args or args[TARGET_ARG] is None:
        raise argparse.ArgumentError(None, f"error: Missing --{TARGET_ARG} argument")
    return args[TARGET_ARG]
