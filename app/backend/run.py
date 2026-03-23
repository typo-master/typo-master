"""
Development entrypoint for TypeMaster backend server.
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.backend.main:app",
        host="0.0.0.0",
        port=50120,
        reload=True,
    )
