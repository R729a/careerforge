import os
import sys

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from mcp_server.main import mcp

if __name__ == "__main__":
    mcp.run()
