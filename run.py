#!/usr/bin/env python3
"""
A convenience script to launch the sarif-tools without installing first.

Not part of the tool package.

Usage:
python run.py <arguments>
"""

import os
import sys

BASEDIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASEDIR, "src"))

from sarif.cmdline import main

sys.exit(main.main())
