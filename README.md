# VisualSynapse

<p align="center">
  <img src="assets/showcase.png" alt="VisualSynapse Showcase" width="100%" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
</p>


A code visualization tool that turns source code, files, and entire folder structures into interactive graphs. With AI assistance, you can map anything from a single function to a full project hierarchy.

## Status

Under active development. Core functionality works but expect rough edges.

## Installation

### Method 1: Run directly (Recommended)
You can run the latest version directly without installing anything manually:

```bash
uvx --from git+https://github.com/visualsynapse/visualsynapse synapse serve
```

### Method 2: Install as a tool
To have the `synapse` command available globally:

```bash
uv tool install git+https://github.com/visualsynapse/visualsynapse
synapse serve --port 8080
```

### Method 3: Development / From Source
If you have cloned the repository:

1. Sync dependencies:
   ```bash
   uv sync
   ```
2. Run using `uv run` (handles environment automatically):
   ```bash
   uv run synapse serve
   ```

## Usage

### Web UI
Start the server using one of the methods above. Then open [http://localhost:8080](http://localhost:8080) in your browser.

### As MCP Server
Add to your MCP config:

```json
{
  "visual-synapse": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/visualsynapse/visualsynapse", "synapse-mcp"]
  }
}
```

## What it does

When you're debugging or trying to understand unfamiliar code, you can ask your AI assistant to visualize it. The tool parses the code, extracts the structure (classes, functions, control flow), and displays it as an expandable graph in a web UI.

This is useful when:
- You want to see how functions relate to each other
- You need to trace logic flow through conditionals and loops
- You're exploring a new codebase and want a visual map



## Contributing

This project is small and under development. If you want to contribute:

1. Fork the repo
2. Make your changes
3. Test that the server starts and basic parsing works
4. Submit a PR with a clear description of what you changed and why

Keep PRs focused. One fix or feature per PR.

If you find a bug, open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce



## Technologies

### Core Analysis
- **Tree-sitter**: Robust AST parsing for Python, JavaScript, and TypeScript.
- **Logic Extraction**: Captures control flow (if/else), loops (for/while), and exception handling.
- **Hierarchical Mapping**: transforms linear code into expandable File > Class > Function > Logic trees.
- **Smart Grouping**: automatically clusters complex logic blocks to simplify visual flow.
- **MCP (Model Context Protocol)**: Standardized interface for AI agent interaction.
- **FastAPI**: Efficient web server for graph data and static assets.

### Visualization
- **React Flow**: Interactive, node-based graph rendering with progressive disclosure.
- **Zustand**: Performant state management for large graph datasets.
- **Vite**: Modern build tooling.

## Structure & Optimizations

### Frontend 
- **React.memo & useMemo**: Heavy use of React's memoization to ensure stable frame rates even with hundreds of nodes. `CustomNode` components are memoized to prevent unnecessary re-renders during graph updates.
- **Efficient Child Counting**: Implements a dual-strategy for hierarchy calculations—using a "Fast Path" with pre-calculated backend data and a "Slow Fallback" for dynamic updates.

### Backend
- **SQLite WAL Mode**: The graph database runs in **Write-Ahead Logging (WAL)** mode. This allows for high-concurrency performance, enabling the UI to read graph state while the parser is simultaneously writing new nodes.
- **Hybrid Storage Model**: Uses a relational schema for edges (`source`, `target`) but stores complex node metadata as **JSON blobs**. This provides the flexibility of a NoSQL document store with the ACID guarantees of SQL.

### Graph Algorithms
- **Structural Analysis**: Built-in BFS (Breadth-First Search) algorithms to detect orphan nodes, calculate graph components, and validate edge integrity on every save.
- **Pathfinding**: Optimized shortest-path algorithms to trace execution flow between any two code entities.


## License

MIT