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
    os.environ["NEPHER_DEBUG"] = "1"
    
    view_module.original_argv = sys.argv.copy()
    from nepher.cli.commands.view import view
    view()
