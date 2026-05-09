#!/usr/bin/env python
"""Launch M.A.V.E.R.I.C.K from airllm workspace."""
import sys
import os

# Add airllm to path
airllm_dir = os.path.dirname(os.path.abspath(__file__))
if airllm_dir not in sys.path:
    sys.path.insert(0, airllm_dir)

# Run M.A.V.E.R.I.C.K
from maverickbot.cli import main

if __name__ == "__main__":
    main()