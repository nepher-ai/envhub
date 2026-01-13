#!/usr/bin/env python
"""
Script to run nepher view command through isaaclab.bat -p

Usage:
    E:/IsaacLab/isaaclab.bat -p scripts/nepher_view.py <env_id> --category <category> [--scene <scene>] [--headless]
    
Example:
    E:/IsaacLab/isaaclab.bat -p scripts/nepher_view.py digital-twin-warehouse-v1 --category navigation --scene small_warehouse
"""

import os
import sys
from nepher.cli.commands import view as view_module

if __name__ == "__main__":
    # Enable debug mode to see full tracebacks
    os.environ["NEPHER_DEBUG"] = "1"
    
    # Store original sys.argv so view command can extract AppLauncher args
    # This must be done before Click processes the arguments
    view_module.original_argv = sys.argv.copy()
    
    # The view command now handles AppLauncher setup internally
    # Just call it with the current sys.argv - it will extract
    # nepher args and AppLauncher args appropriately
    from nepher.cli.commands.view import view
    view()  # type: ignore[call-arg]

