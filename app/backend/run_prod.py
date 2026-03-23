#!/usr/bin/env python3
"""
Production entrypoint for TypeMaster backend server (no reload).
"""

import sys
sys.path.insert(0, '/Users/cc11001100/github/typo-master/typo-master')

import uvicorn
from app.backend.main import app

if __name__ == "__main__":
    # Use reload=False and direct app import to prevent config loading issues
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=50120,
        reload=False,
        workers=1,
    )
