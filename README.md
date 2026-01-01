# VisualSynapse

<p align="center">
  <img src="ui/public/logo.png" alt="VisualSynapse" width="200" height="200">
</p>

A code visualization tool that turns source code, files, and entire folder structures into interactive graphs. With AI assistance, you can map anything from a single function to a full project hierarchy.

## What it does

When you're debugging or trying to understand unfamiliar code, you can ask your AI assistant to visualize it. The tool parses the code, extracts the structure (classes, functions, control flow), and displays it as an expandable graph in a web UI.

This is useful when:
- You want to see how functions relate to each other
- You need to trace logic flow through conditionals and loops
- You're exploring a new codebase and want a visual map

## Status

Under active development. Core functionality works but expect rough edges.

## Installation

Requires Python 3.10+ and UV.

```bash
uv pip install git+https://github.com/visualsynapse/visualsynapse
```

Or run directly without installing:

```bash
uvx --from git+https://github.com/visualsynapse/visualsynapse synapse serve
```

## Usage

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

### Web UI

Start the server:

```bash
synapse serve --port 8080
```

Open http://localhost:8080 in your browser.

### MCP Tools Available

Once connected, your AI assistant can use:

- `static_visualize_flow` - Parse a file and add it to the graph
- `get_session_graph` - Get current graph state
- `add_custom_node` / `add_custom_edge` - Manually add to the graph
- `analyze_session` - Check graph health (orphan nodes, broken edges)

## Project Structure

```
visualsynapse/
├── synapse/          # Python package
│   ├── main.py       # FastAPI server + MCP tools
│   ├── parser.py     # Tree-sitter based code analysis
│   └── graph_manager.py
├── ui/               # React frontend
└── pyproject.toml
```

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

## License

MIT