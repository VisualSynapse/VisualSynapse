import sys
import os
import logging

# Add parent directory to path so synapse package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

try:
    from synapse.main import mcp
    
    if __name__ == "__main__":
        mcp.run(transport="stdio")
        
except ImportError as e:
    logging.fatal(f"Failed to import MCP server: {e}")
    sys.exit(1)
except Exception as e:
    logging.fatal(f"MCP Server crashed: {e}")
    sys.exit(1)
