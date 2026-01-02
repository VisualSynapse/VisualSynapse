import os
import sys
import json
import logging
import socket
import asyncio
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Internal Modules (package-relative)
from synapse.graph_manager import GraphManager
from synapse.parser import ASTParser, get_visual_base_mcp

# Configure Logging - Send to stderr to keep stdout clean for MCP
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("visual_base")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Store sessions in user's home directory so both MCP (uvx) and UI serve share data
SESSIONS_DIR = os.path.join(os.path.expanduser("~/.visualsynapse"), "sessions")
PORT_FILE = os.path.join(os.path.dirname(SESSIONS_DIR), ".ui_port")


graph = GraphManager(sessions_dir=SESSIONS_DIR)
parser = ASTParser()
mcp = get_visual_base_mcp(graph)

@mcp.tool()
def create_session(session_id: str) -> str:
    """
    Creates a new graph session.
    
    IMPORTANT: Only create a new session when explicitly requested by the user.
    When working with the same codebase or making incremental changes to existing graphs,
    reuse the current session instead of creating a new one. Creating unnecessary sessions
    clutters the workspace and loses context from previous work.
    
    Args:
        session_id: A unique identifier for the session.
    """
    logger.info(f"Tool Call: create_session(session_id={session_id})")
    if graph.create_session(session_id):
        return f"Session '{session_id}' created."
    return f"Session '{session_id}' already exists."



@mcp.tool()
def list_sessions() -> List[str]:
    """
    Lists all available graph sessions.
    Use this to see which sessions already exist before creating a new one, or to find a session ID to query.
    Returns: A list of session ID strings.
    """
    logger.info("Tool Call: list_sessions()")
    return graph.list_sessions()

@mcp.tool()
def delete_session(session_id: str) -> str:
    """
    Deletes a graph session and all its associated data.
    Use this tool to clean up old or unused analysis sessions to free up resources or clear clutter.
    
    Args:
        session_id: The ID of the session to delete.
        
    WARNING: This action is irreversible. All nodes and edges within the session will be permanently removed.
    """
    logger.info(f"Tool Call: delete_session(session_id={session_id})")
    if graph.delete_session(session_id):
        return f"Session '{session_id}' deleted."
    return f"Session '{session_id}' not found."

@mcp.tool()
def add_custom_node(session_id: str, node_id: str, label: str, node_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Adds a custom node to a specific session graph.
    Use this tool to manually insert nodes representing code entities, logic steps, or data points.

    Args:
        session_id: The target session ID (must exist).
        node_id: A unique identifier for the node within the session.
        label: The text label displayed on the node in the UI.
        node_type: The category of the node, which determines its styling/icon. 
                   Standard types: 'class', 'function', 'file', 'logic', 'database', 'api', 'call_step', 'data'.
                   Note: You can use any string (e.g., 'service', 'module'), but non-standard types will use a default generic style.
        metadata: Optional dictionary for extra context. 
                  - 'lineno': Line number in source file (int).
                  - 'file': Source file path (str).
                  - 'description': Additional details (str).
    """
    logger.info(f"Tool Call: add_custom_node(session_id={session_id}, node_id={node_id}, label={label}, type={node_type})")
    graph.add_node(session_id, node_id, label, node_type, metadata)
    return f"Node '{label}' ({node_type}) added to session '{session_id}'."

@mcp.tool()
def remove_node(session_id: str, node_id: str) -> str:
    """
    Removes a node and its connections from a specific session.
    Use this tool to delete a specific node. Any edges connected to this node will also be removed.
    
    Args:
        session_id: The session ID.
        node_id: The ID of the node to remove.
    """
    logger.info(f"Tool Call: remove_node(session_id={session_id}, node_id={node_id})")
    if graph.remove_node(session_id, node_id):
        return f"Node '{node_id}' removed."
    return f"Node '{node_id}' not found."

@mcp.tool()
def add_custom_edge(session_id: str, source: str, target: str, label: str, edge_type: str = "default") -> str:
    """
    Adds a directed edge between two existing nodes in a session.
    Use this tool to define relationships, control flow, or dependencies between nodes.

    IMPORTANT: The 'label' parameter is REQUIRED. Always provide a descriptive label
    that explains the relationship (e.g., 'calls', 'returns', 'updates state', 'imports').
    Unlabeled edges make graphs unreadable.

    Args:
        session_id: The target session ID.
        source: The ID of the source node (must exist).
        target: The ID of the target node (must exist).
        label: REQUIRED. A descriptive text label for the edge (e.g., 'calls', 'imports', 'updates').
        edge_type: The semantic type of the connection (e.g., 'calls', 'imports', 'inherits', 'data_flow', 'flow').
                   Different types may be styled differently in the UI. Defaults to 'default'.
    """
    logger.info(f"Tool Call: add_custom_edge(session_id={session_id}, source={source}, target={target}, label={label})")
    eid = graph.add_edge(session_id, source, target, edge_type, label)
    return f"Edge '{label}' ({edge_type}) added: {source} -> {target}"

@mcp.tool()
def remove_edge(session_id: str, edge_id: str) -> str:
    """
    Removes a specific edge from a session.
    Use this tool to remove a connection between nodes without deleting the nodes themselves.
    
    Args:
        session_id: The session ID.
        edge_id: The ID of the edge to remove.
    """
    logger.info(f"Tool Call: remove_edge(session_id={session_id}, edge_id={edge_id})")
    if graph.remove_edge(session_id, edge_id):
        return f"Edge '{edge_id}' removed."
    return f"Edge '{edge_id}' not found."

@mcp.tool()
def update_node_position(session_id: str, node_id: str, x: float, y: float) -> str:
    """
    Updates the visual position of a node in the graph.
    Use this to programmatically arrange nodes or save AI-generated layouts.

    Args:
        session_id: The target session ID.
        node_id: The ID of the node to move.
        x: The new X coordinate.
        y: The new Y coordinate.
    """
    logger.info(f"Tool Call: update_node_position(session_id={session_id}, node_id={node_id}, x={x}, y={y})")
    if graph.update_node_position(session_id, node_id, x, y):
        return f"Position updated for '{node_id}' to ({x}, {y})"
    return f"Node '{node_id}' not found in session '{session_id}'."

@mcp.tool()
def batch_update_positions(session_id: str, positions: List[Dict[str, Any]]) -> str:
    """
    Updates positions for multiple nodes in one call.
    Use this for efficient bulk layout updates.

    Args:
        session_id: The target session ID.
        positions: A list of dicts, each with 'node_id', 'x', 'y' keys.
    """
    logger.info(f"Tool Call: batch_update_positions(session_id={session_id}, count={len(positions)})")
    updated = 0
    for pos in positions:
        if graph.update_node_position(session_id, pos['node_id'], pos['x'], pos['y']):
            updated += 1
    return f"Updated positions for {updated}/{len(positions)} nodes."

@mcp.tool()
def search_nodes(session_id: str, query: str) -> str:
    """
    Search for nodes in a session matching a query string.
    Use this to find specific nodes by label, ID, or type without retrieving the entire graph.
    
    Args:
        session_id: The session ID to search in.
        query: The search string (case-insensitive).
        
    Returns:
        A JSON string containing a list of matching node objects.
    """
    logger.info(f"Tool Call: search_nodes(session_id={session_id}, query={query})")
    results = graph.search_nodes(session_id, query)
    return json.dumps(results, indent=2)

@mcp.tool()
def find_node_id(session_id: str, query: str) -> str:
    """
    Finds the unique ID of a node by name.
    Use this helper to resolve a readable name (e.g. "Processor") to its internal ID (e.g. "node_123") for other operations.
    
    Args:
        session_id: The session ID.
        query: The node name or label to search for.
    
    Returns:
        The exact ID string if found, or an error message if missing/ambiguous.
    """
    logger.info(f"Tool Call: find_node_id(session_id={session_id}, query={query})")
    results = graph.search_nodes(session_id, query)
    if not results:
        return f"Error: No node found matching '{query}'"
    if len(results) > 1:

        exact = next((n for n in results if n['label'] == query or n['id'] == query), None)
        if exact: return exact['id']
        matches = [f"{n['label']} ({n['id']})" for n in results]
        return f"Error: Ambiguous match. Found: {', '.join(matches[:5])}"
    
    return results[0]['id']

@mcp.tool()
def add_child_node(session_id: str, parent_query: str, node_id: str, label: str, node_type: str, metadata: Optional[Dict[str, Any]] = None, edge_label: str = "", edge_type: str = "contains") -> str:
    """
    Adds a new node as a child of an existing node (found by name).
    Use this to easily build hierarchy without knowing exact parent IDs.
    
    Args:
        session_id: The target session.
        parent_query: Name or ID of the parent node to search for.
        node_id: Unique ID for the new child node.
        label: Visual label for the child.
        node_type: Type of the child (e.g., 'function', 'logic', 'call_step').
        metadata: Optional extra data dictionary.
        edge_label: Label to display on the parent-child edge (e.g., 'contains', 'inherits').
        edge_type: Semantic type of edge (default: 'contains'). Options: 'contains', 'calls', 'data_flow'.
    """
    logger.info(f"Tool Call: add_child_node(parent_query={parent_query}, child_id={node_id})")
    parent_results = graph.search_nodes(session_id, parent_query)
    parent_id = None
    
    if len(parent_results) == 1:
        parent_id = parent_results[0]['id']
    elif len(parent_results) > 1:
        exact = next((n for n in parent_results if n['label'] == parent_query or n['id'] == parent_query), None)
        if exact:
            parent_id = exact['id']
        else:
            return f"Error: Parent '{parent_query}' is ambiguous ({len(parent_results)} matches)."
    else:
        return f"Error: Parent '{parent_query}' not found."

    if metadata is None: metadata = {}
    metadata['parentId'] = parent_id
    
    graph.add_node(session_id, node_id, label, node_type, metadata)
    graph.add_edge(session_id, parent_id, node_id, edge_type=edge_type, label=edge_label)
    
    return f"Node '{label}' added as child of '{parent_query}' ({parent_id}) with edge."

@mcp.tool()
def get_session_metrics(session_id: str) -> str:
    """
    Get graph complexity metrics for a specific session.
    Use this to track graph size, edge density, and node type distribution.
    
    Args:
        session_id: The session ID to analyze.
        
    Returns:
        JSON string with 'total_nodes', 'total_edges', 'complexity_ratio', and 'node_distribution'.
    """
    logger.info(f"Tool Call: get_session_metrics(session_id={session_id})")
    metrics = graph.get_metrics(session_id)
    return json.dumps(metrics, indent=2)

@mcp.tool()
def find_path(session_id: str, source: str, target: str) -> str:
    """
    Finds the shortest path between two nodes in the graph.
    Use this to trace dependencies or debug control flow.
    
    Args:
        session_id: The session ID.
        source: The start node ID.
        target: The end node ID.
        
    Returns:
        A list of node IDs representing the path, or null if no path exists.
    """
    logger.info(f"Tool Call: find_path(from={source}, to={target})")
    path = graph.find_path(session_id, source, target)
    if path:
        return f"Path found: {' -> '.join(path)}"
    return "No path found."

@mcp.tool()
def analyze_session(session_id: str) -> str:
    """
    Analyzes the structure and health of a graph session.
    Returns:
        JSON string containing checks for:
        - Orphan nodes (disconnected)
        - Broken edges (pointing to missing nodes)
        - Connectivity (fragmentation/components)
        - Node/Edge counts
    """
    logger.info(f"Tool Call: analyze_session(session_id={session_id})")
    report = graph.analyze_structure(session_id)
    return json.dumps(report, indent=2)

@mcp.tool()
def get_session_graph(session_id: str = "default") -> str:
    """
    Retrieves the complete graph structure for a specific session.
    Use this tool to inspect the current state of the graph, including all nodes and edges.
    
    Args:
        session_id: The session ID to query. defaults to "default".
        
    Returns:
        A JSON string representation of the graph: { "elements": { "nodes": [...], "edges": [...] } }
    """
    logger.info(f"Tool Call: get_session_graph(session_id={session_id})")
    return json.dumps(graph.get_graph(session_id), indent=2)

@mcp.tool()
def clear_session_graph(session_id: str) -> str:
    """
    Completely clears all nodes and edges from a specific session.
    Use this tool to reset a session's graph to a blank state while keeping the session active.
    
    Args:
        session_id: The session ID to clear.
    """
    logger.info(f"Tool Call: clear_session_graph(session_id={session_id})")
    graph.clear_graph(session_id)
    return f"Session '{session_id}' cleared."

@mcp.tool()
def load_session(session_id: str, file_path: str) -> str:
    """
    Loads a graph session from an external JSON backup file.
    Use this to restore a previously exported session or import external data.
    
    Args:
        session_id: The ID to assign to the loaded session.
        file_path: Absolute path to the JSON file containing the graph data.
    """
    logger.info(f"Tool Call: load_session(session_id={session_id}, path={file_path})")
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        graph.create_session(session_id)
        
        # Expecting { elements: { nodes: [], edges: [] } } structure
        nodes = data.get("elements", {}).get("nodes", [])
        edges = data.get("elements", {}).get("edges", [])
        
        count = 0
        for node in nodes:
            d = node["data"]
            # Extract metadata (everything except core fields)
            meta = {k:v for k,v in d.items() if k not in ["id", "label", "type"]}
            graph.add_node(session_id, d["id"], d["label"], d["type"], meta)
            count += 1
            
        for edge in edges:
            d = edge["data"]
            graph.add_edge(session_id, d["source"], d["target"], d["type"], d.get("label", ""))
            
        return f"Successfully loaded {count} nodes into session '{session_id}' from {file_path}"
    except Exception as e:
        return f"Failed to load session: {str(e)}"

@mcp.tool()
def export_graph(session_id: str, format: str = "json") -> str:
    """
    Exports the current graph session to a text format.
    
    Args:
        session_id: The session to export.
        format: 'json' (default) or 'markdown' (for structural documentation).
                Note: Markdown format produces a Hierarchical Tree (Files > Classes > Functions > Logic) optimized for Markmap.
        
    Returns:
        The string representation of the graph in the requested format.
    """
    logger.info(f"Tool Call: export_graph(session_id={session_id}, format={format})")
    data = graph.get_graph(session_id)
    
    if format.lower() == "json":
        return json.dumps(data, indent=2)
        
    elif format.lower() == "markdown":
        nodes = data["elements"]["nodes"]

        node_map = {n["data"]["id"]: n["data"] for n in nodes}
        tree = {}
        roots = []
        
        # Build Tree
        logger.debug(f"Building tree structure for session {session_id}")
        for n in nodes:
            d = n["data"]
            # Try to find parent in various fields
            pid = d.get("parentId") or d.get("parent") or d.get("metadata", {}).get("parent")
            
            if pid:
                if pid not in tree: tree[pid] = []
                tree[pid].append(d["id"])
            else:
                logger.debug(f"Found root node: {d['id']}")
                roots.append(d["id"])

        md_lines = []
        
        def process_node(node_id, depth=0):
            if node_id not in node_map: return
            node = node_map[node_id]
            ntype = node["type"]
            label = node["label"]
            
            # Formatting
            args = node.get("args") or node.get("arguments") or node.get("metadata", {}).get("args") or ""
            arg_str = f" - Args: {args}" if args else ""
            
            indent = "  " * depth
            content = f"{indent}- {label}{arg_str}"
            md_lines.append(content)


            # Process Children
            if node_id in tree:
                children = tree[node_id]
                logger.debug(f"Processing {len(children)} children for {node_id}")
                # Sort by line number for flow
                def get_lineno(nid):
                    nd = node_map.get(nid, {})
                    return nd.get("lineno") or nd.get("metadata", {}).get("lineno") or 999999
                
                sorted_children = sorted(children, key=get_lineno)
                
                next_depth = depth + 1
                
                for child in sorted_children:
                    process_node(child, next_depth)

        for root in roots:
            process_node(root)
            
        return "\n".join(md_lines)
    
    elif format.lower() == "canvas":
        # Infinite Canvas / JSON Canvas format (jsoncanvas.org)
        canvas_nodes = []
        for n in data["elements"]["nodes"]:
            nd = n["data"]
            pos = n.get("position", {"x": 0, "y": 0})
            
            content = f"### {nd['label']}\n"
            if nd.get("type"): content += f"**Type**: `{nd['type']}`\n"
            args = nd.get("args") or nd.get("arguments")
            if args: content += f"\n**Args**: `{args}`\n"
            lineno = nd.get("lineno")
            if lineno: content += f"\nLine: {lineno}\n"
                
            canvas_nodes.append({
                "id": nd["id"],
                "type": "text",
                "text": content,
                "x": int(pos.get("x", 0)),
                "y": int(pos.get("y", 0)),
                "width": 260,
                "height": 140
            })
            
        canvas_edges = []
        for e in data["elements"]["edges"]:
            ed = e["data"]
            canvas_edges.append({
                "id": ed.get("id", f"{ed['source']}-{ed['target']}"),
                "fromNode": ed["source"],
                "toNode": ed["target"],
                "label": ed.get("label", "")
            })
            
        return json.dumps({"nodes": canvas_nodes, "edges": canvas_edges}, indent=2)
        
    return "Error: Unsupported format. Use 'json', 'markdown', or 'canvas'."

app = FastAPI(title="VisualSynapse Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@mcp.tool()
def list_root_nodes(session_id: str = "default") -> str:
    """
    Lists only the root nodes (nodes without parents) in a session.
    Use this for initial exploration instead of get_session_graph.
    
    Args:
        session_id: The session ID to query.
        
    Returns:
        JSON string with root node summaries (id, label, type, child_count).
    """
    logger.info(f"Tool Call: list_root_nodes(session={session_id})")
    data = graph.get_graph(session_id)
    nodes = data["elements"]["nodes"]
    
    roots = []
    for n in nodes:
        d = n["data"]
        pid = d.get("parentId") or d.get("parent")
        if not pid:
            roots.append({
                "id": d["id"],
                "label": d.get("label", "unlabeled"),
                "type": d.get("type", "unknown"),
                "child_count": len(d.get("children", []))
            })
    
    return json.dumps({"session": session_id, "root_count": len(roots), "roots": roots}, indent=2)

@mcp.tool()
def get_session_summary(session_id: str = "default") -> str:
    """
    Returns a concise summary of the graph generated by the visualsynapse tool for the given session.
    Use this instead of get_session_graph for overview.
    
    Args:
        session_id: The session ID to summarize.
        
    Returns:
        JSON string with node/edge counts, type distribution, and root nodes list.
    """
    logger.info(f"Tool Call: get_session_summary(session={session_id})")
    data = graph.get_graph(session_id)
    nodes = data["elements"]["nodes"]
    edges = data["elements"]["edges"]
    
    type_counts = {}
    roots = []
    
    for n in nodes:
        d = n["data"]
        node_type = d.get("type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
        
        pid = d.get("parentId") or d.get("parent")
        if not pid:
            roots.append({"id": d["id"], "label": d.get("label"), "type": node_type})
    
    return json.dumps({
        "session": session_id,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_types": type_counts,
        "root_nodes": roots
    }, indent=2)

@mcp.tool()
def get_node_details(session_id: str, node_id: str) -> str:
    """
    Retrieves detailed information about a specific node.
    
    Args:
        session_id: The session ID.
        node_id: The ID of the node to inspect.
        
    Returns:
        JSON string with full node data including children, metadata, and connected edges.
    """
    logger.info(f"Tool Call: get_node_details(session={session_id}, node={node_id})")
    data = graph.get_graph(session_id)
    nodes = data["elements"]["nodes"]
    edges = data["elements"]["edges"]
    
    target_node = None
    for n in nodes:
        if n["data"]["id"] == node_id:
            target_node = n["data"]
            break
    
    if not target_node:
        return json.dumps({"error": f"Node '{node_id}' not found in session '{session_id}'"})
    
    # Find connected edges
    incoming = [e["data"] for e in edges if e["data"]["target"] == node_id]
    outgoing = [e["data"] for e in edges if e["data"]["source"] == node_id]
    
    # Extract position (may be null if not set)
    position = target_node.get("position", None)
    
    return json.dumps({
        "node": target_node,
        "position": position,
        "incoming_edges": len(incoming),
        "outgoing_edges": len(outgoing),
        "edges": {"incoming": incoming[:5], "outgoing": outgoing[:5]}
    }, indent=2)

# Resolve UI_DIST_DIR: Check installed location (wheel) first, then dev location
_ui_dist_wheel = os.path.join(BASE_DIR, "ui/dist")
_ui_dist_dev = os.path.join(os.path.dirname(BASE_DIR), "ui/dist")

if os.path.exists(_ui_dist_wheel) and os.path.isdir(_ui_dist_wheel):
    UI_DIST_DIR = _ui_dist_wheel
else:
    UI_DIST_DIR = _ui_dist_dev

# Models
class CodePayload(BaseModel):
    code: str
    overwrite: bool = False
    language: str = "python"

class PositionPayload(BaseModel):
    x: float
    y: float

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# --- Endpoints ---

@app.get("/sessions")
async def list_sessions_api():
    return graph.list_sessions()

@app.post("/analyze")
async def analyze_code(payload: CodePayload, session_id: str = "default"):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            parser.parse_code,
            payload.code,
            "snippet",
            "full"
        )
        
        if payload.overwrite:
            graph.clear_graph(session_id)
        for node in result["elements"]["nodes"]:
            d = node["data"]
            # Flatten VisualNode attributes for Graph Manager storage
            properties = d.get("data", {}).copy() # Start with dynamic data
            if d.get("parentId"):
                properties["parentId"] = d["parentId"]
            
            graph.add_node(session_id, d["id"], d["label"], d["type"], properties)
        for edge in result["elements"]["edges"]:
            d = edge["data"]
            graph.add_edge(session_id, d["source"], d["target"], d["type"], d.get("label", ""))
        
        await manager.broadcast({"type": "graph_update", "session_id": session_id, "data": graph.get_graph(session_id)})
        return {"status": "success", "session": session_id, "nodes": len(result["elements"]["nodes"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph")
async def get_graph_api(session_id: str = "default", parent_id: Optional[str] = None):
    """Get graph with specified filters for progressive loading."""
    full_graph_data = graph.get_graph(session_id)
    all_nodes = full_graph_data["elements"]["nodes"]
    all_edges = full_graph_data["elements"]["edges"]

    if parent_id is None:
        return full_graph_data

    # Filter by parent if requested
    filtered_nodes = [n for n in all_nodes if n["data"].get("parentId") == parent_id]
    filtered_node_ids = {n["data"]["id"] for n in filtered_nodes}
    filtered_edges = [e for e in all_edges if e["data"]["source"] in filtered_node_ids and e["data"]["target"] in filtered_node_ids]
    
    return {"elements": {"nodes": filtered_nodes, "edges": filtered_edges}}

@app.patch("/api/sessions/{session_id}/nodes/{node_id:path}/position")
async def update_node_position(session_id: str, node_id: str, payload: PositionPayload):
    try:
        graph.update_node_position(session_id, node_id, payload.x, payload.y)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class HighlightPayload(BaseModel):
    color: Optional[str] = None

@app.patch("/api/sessions/{session_id}/nodes/{node_id:path}/highlight")
async def update_node_highlight(session_id: str, node_id: str, payload: HighlightPayload):
    try:
        success = graph.update_node_highlight(session_id, node_id, payload.color)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        await manager.broadcast({"type": "graph_update", "session_id": session_id, "data": graph.get_graph(session_id)})
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update highlight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snippet")
async def get_snippet(file: str, line: int):
    # Try different path locations
    paths_to_try = [file, os.path.join(os.getcwd(), file)]
    
    # Also check if it's in the workspace root
    workspace_root = os.path.dirname(os.getcwd())
    paths_to_try.append(os.path.join(workspace_root, file))
    
    # Try just the basename in the current directory
    paths_to_try.append(os.path.join(os.getcwd(), os.path.basename(file)))

    actual_path = None
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            actual_path = p
            break
            
    if not actual_path:
        return {"error": f"File not found: {file}"}

    try:
        with open(actual_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Line numbers are 1-indexed
        target = line - 1
        start = max(0, target - 10)
        end = min(len(all_lines), target + 11)
        
        snippet = []
        for i in range(start, end):
            snippet.append({
                "number": i + 1,
                "content": all_lines[i].rstrip()
            })
            
        return {"file": actual_path, "lines": snippet}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/graph")
async def clear_graph_api(session_id: str = "default"):
    graph.clear_graph(session_id)
    await manager.broadcast({"type": "graph_update", "session_id": session_id, "data": graph.get_graph(session_id)})
    return {"status": "cleared", "session": session_id}

@app.get("/export")
async def export_graph_api(session_id: str = "default", format: str = "markdown"):
    data = graph.get_graph(session_id)
    
    if format.lower() == "json":
        return {"content": json.dumps(data, indent=2), "format": "json"}
    
    elif format.lower() == "markdown":
        nodes = data["elements"]["nodes"]
        node_map = {n["data"]["id"]: n["data"] for n in nodes}
        tree = {}
        roots = []
        
        for n in nodes:
            d = n["data"]
            pid = d.get("parentId") or d.get("parent") or d.get("metadata", {}).get("parent")
            
            if pid:
                if pid not in tree: tree[pid] = []
                tree[pid].append(d["id"])
            else:
                # Top-level roots (files, folders, logic without parents)
                roots.append(d["id"])

        md_lines = []
        
        def process_node(node_id, depth=0):
            if node_id not in node_map: return
            node = node_map[node_id]
            ntype = node["type"]
            label = node["label"]
            
            args = node.get("args") or node.get("arguments") or node.get("metadata", {}).get("args") or ""
            arg_str = f" - Args: {args}" if args else ""
            # Generic depth-based rendering (Lists for infinite nesting)
            indent = "  " * depth
            content = f"{indent}- **{ntype}**: {label}{arg_str}"
            md_lines.append(content)
            
            if node_id in tree:
                children = tree[node_id]
                children_sorted = sorted(children, key=lambda cid: (node_map[cid]["type"], node_map[cid].get("lineno", 0)))
                for child_id in children_sorted:
                    process_node(child_id, depth + 1)
        
        for root_id in sorted(roots, key=lambda rid: node_map[rid].get("lineno", 0)):
            process_node(root_id, 0)
        
        markdown = "\n".join(md_lines)
        return {"content": markdown, "format": "markdown"}
        
    elif format.lower() == "canvas":

        nodes = data["elements"]["nodes"]
        edges = data["elements"]["edges"]
        
        canvas_nodes = []
        for n in nodes:
            nd = n["data"]
            pos = n.get("position", {"x": 0, "y": 0})
            
            content = f"### {nd['label']}\n"
            if nd.get("type"):
                content += f"**Type**: `{nd['type']}`\n"
            
            args = nd.get("args") or nd.get("arguments")
            if args:
                content += f"\n**Args**: `{args}`\n"
                
            
            lineno = nd.get("lineno")
            if lineno:
                content += f"\nLine: {lineno}\n"
                
            canvas_nodes.append({
                "id": nd["id"],
                "type": "text",
                "text": content,
                "x": int(pos.get("x", 0)),
                "y": int(pos.get("y", 0)),
                "width": 260,
                "height": 140
            })
            
        canvas_edges = []
        for e in edges:
            ed = e["data"]
            canvas_edges.append({
                "id": ed.get("id", f"{ed['source']}-{ed['target']}"),
                "fromNode": ed["source"],
                "toNode": ed["target"],
                "label": ed.get("label", "")
            })
            
        return {
            "content": json.dumps({"nodes": canvas_nodes, "edges": canvas_edges}, indent=2), 
            "format": "canvas"
        }
    
    return {"error": "Unsupported format"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default"):
    await manager.connect(websocket)
    try:
        # Send initial graph state
        await websocket.send_json({"type": "graph_update", "session_id": session_id, "data": graph.get_graph(session_id)})
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if os.path.exists(UI_DIST_DIR):
    app.mount("/", StaticFiles(directory=UI_DIST_DIR, html=True), name="ui")
    logger.info(f"✓ Serving React UI from {UI_DIST_DIR}")
else:
    logger.error(f"FATAL: UI build not found at {UI_DIST_DIR}. Build it first!")

def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the VisualSynapse web UI server."""
    import uvicorn
    
    ui_url = f"http://localhost:{port}/"
    logger.info("=" * 60)
    logger.info("VisualSynapse Server (MCP + UI)")
    logger.info(f"UI: {ui_url}")
    logger.info(f"MCP: Run via `synapse mcp`")
    logger.info("=" * 60)
    
    with open(PORT_FILE, 'w') as f:
        f.write(str(port))
        
    try:
        logger.info(f"Initializing VisualSynapse Web UI on http://localhost:{port}")
        logger.info(">>> RUNNING EDITED VERSION: Persisted Sessions & Enhanced Path Resolution Active <<<")
        config = uvicorn.Config(app, host=host, port=port, log_config=None)
        server = uvicorn.Server(config)
        server.run()
    finally:
        if os.path.exists(PORT_FILE):
            os.remove(PORT_FILE)


def run_mcp_stdio():
    """Run as MCP server via stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    port = int(os.environ.get("VB_PORT", 8080))
    run_server(port=port)
