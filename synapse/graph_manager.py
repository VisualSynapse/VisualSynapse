import logging
import json
import os
import sqlite3
from contextlib import contextmanager
import glob

logger = logging.getLogger("graph_manager")

class GraphManager:
    def __init__(self, sessions_dir="sessions"):
        self.sessions_dir = sessions_dir
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
            
        if not os.path.exists(self._get_db_path("default")):
            self.create_session("default")

    def _get_db_path(self, session_id):
        safe_id = "".join([c for c in session_id if c.isalnum() or c in ('_', '-')])
        if not safe_id: safe_id = "default"
        return os.path.join(self.sessions_dir, f"{safe_id}.db")

    @contextmanager
    def _get_conn(self, session_id):
        path = self._get_db_path(session_id)
        is_new = not os.path.exists(path)
        
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        
        # Always ensure schema is initialized (idempotent)
        self._init_db_schema(conn)
            
        try:
            yield conn
        finally:
            conn.close()

    def _init_db_schema(self, conn):
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            
            -- Session ID is implicit (the file itself), but we store creation time
            INSERT OR IGNORE INTO metadata (key, value) VALUES ('created_at', CURRENT_TIMESTAMP);
            
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                data_json TEXT
            );
            
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source TEXT,
                target TEXT,
                data_json TEXT
            );
        """)
        conn.commit()

    def update_node_position(self, session_id, node_id, x, y):
        """Updates just the position of a node in the JSON blob."""
        with self._get_conn(session_id) as conn:
            cursor = conn.execute("SELECT data_json FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            if not row:
                return False
                
            data = json.loads(row['data_json'])
            data['position'] = {'x': x, 'y': y}
            
            conn.execute(
                "UPDATE nodes SET data_json = ? WHERE id = ?",
                (json.dumps(data), node_id)
            )
            conn.commit()
            return True

    def create_session(self, session_id):
        # Just connecting initializes it via _get_conn logic
        path = self._get_db_path(session_id)
        if os.path.exists(path):
            return False # Already exists
            
        # Force creation
        with self._get_conn(session_id) as conn:
            pass
        return True

    def list_sessions(self):
        # List all .db files in sessions_dir
        files = glob.glob(os.path.join(self.sessions_dir, "*.db"))
        return [os.path.splitext(os.path.basename(f))[0] for f in files]

    def delete_session(self, session_id):
        path = self._get_db_path(session_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def add_node(self, session_id, node_id, label, node_type, metadata=None):
        if metadata is None: metadata = {}
        node_data = {
            "id": node_id,
            "label": label,
            "type": node_type,
            **metadata
        }
        with self._get_conn(session_id) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, type, data_json) VALUES (?, ?, ?)",
                (node_id, node_type, json.dumps(node_data))
            )
            conn.commit()
        return node_id

    def remove_node(self, session_id, node_id):
        with self._get_conn(session_id) as conn:
            cursor = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            conn.execute("DELETE FROM edges WHERE (source = ? OR target = ?)", (node_id, node_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_edge(self, session_id, source, target, edge_type="default", label="", metadata=None):
        if metadata is None: metadata = {}
        edge_id = f"e_{source}_{target}"
        edge_data = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "label": label,
            **metadata
        }
        with self._get_conn(session_id) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO edges (id, source, target, data_json) VALUES (?, ?, ?, ?)",
                (edge_id, source, target, json.dumps(edge_data))
            )
            
            # Auto-set parentId on target node for hierarchy edges
            if edge_type == "contains":
                cursor = conn.execute("SELECT data_json FROM nodes WHERE id = ?", (target,))
                row = cursor.fetchone()
                if row:
                    node_data = json.loads(row['data_json'])
                    if not node_data.get('parentId'):
                        node_data['parentId'] = source
                        conn.execute(
                            "UPDATE nodes SET data_json = ? WHERE id = ?",
                            (json.dumps(node_data), target)
                        )
            
            conn.commit()
        return edge_id

    def remove_edge(self, session_id, edge_id):
        with self._get_conn(session_id) as conn:
            cursor = conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_graph(self, session_id):
        with self._get_conn(session_id) as conn:
            conn.execute("DELETE FROM nodes")
            conn.execute("DELETE FROM edges")
            conn.commit()

    def get_graph(self, session_id):
        with self._get_conn(session_id) as conn:
            node_rows = conn.execute("SELECT data_json FROM nodes").fetchall()
            edge_rows = conn.execute("SELECT data_json FROM edges").fetchall()
            
        nodes = [json.loads(row['data_json']) for row in node_rows]
        edges = [{"data": json.loads(row['data_json'])} for row in edge_rows]
        
        node_map = {n['id']: n for n in nodes}
        
        # STEP 1: Infer parentId from 'contains' type edges for manually added nodes
        for e in edges:
            ed = e["data"]
            if ed.get("type") == "contains":
                child_id = ed.get("target")
                parent_id = ed.get("source")
                if child_id in node_map and parent_id in node_map:
                    child_node = node_map[child_id]
                    if not child_node.get('parentId'):
                        child_node['parentId'] = parent_id
        
        # STEP 2: Build children arrays from parentId
        for n in nodes:
            parent_id = n.get('parentId')
            if parent_id and parent_id in node_map:
                parent = node_map[parent_id]
                if 'children' not in parent:
                    parent['children'] = []
                if n['id'] not in parent['children']:
                    parent['children'].append(n['id'])
                
        final_nodes = [{"data": n} for n in nodes]

        return {
            "elements": {
                "nodes": final_nodes,
                "edges": edges
            }
        }

    def search_nodes(self, session_id, query):
        """Search nodes by matching query against id, label, or type (case-insensitive)."""
        query_lower = query.lower()
        
        with self._get_conn(session_id) as conn:
            cursor = conn.execute("SELECT data_json FROM nodes")
            rows = cursor.fetchall()
        
        results = []
        for r in rows:
            data = json.loads(r['data_json'])
            # Check if query matches id, label, or type
            if (query_lower in data.get('id', '').lower() or 
                query_lower in data.get('label', '').lower() or 
                query_lower in data.get('type', '').lower()):
                results.append(data)
        
        return results

    def get_metrics(self, session_id):
        with self._get_conn(session_id) as conn:
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            
            type_counts_rows = conn.execute(
                "SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type"
            ).fetchall()
            
        type_counts = {row['type']: row['cnt'] for row in type_counts_rows}
        
        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "complexity_ratio": round(edge_count / node_count, 2) if node_count > 0 else 0,
            "node_distribution": type_counts
        }

    def find_path(self, session_id, start_node, end_node):
        graph_data = self.get_graph(session_id)
        edges = graph_data["elements"]["edges"]
        
        adj = {}
        for edge in edges:
            src = edge["data"]["source"]
            tgt = edge["data"]["target"]
            if src not in adj: adj[src] = []
            adj[src].append(tgt)
            
        queue = [[start_node]]
        visited = {start_node}
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == end_node: return path
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return None

    def analyze_structure(self, session_id):
        """Analyzes graph connectivity, orphans, and integrity."""
        graph_data = self.get_graph(session_id)
        nodes = graph_data["elements"]["nodes"]
        edges = graph_data["elements"]["edges"]
        
        node_ids = set(n["data"]["id"] for n in nodes)
        
        # 1. Edge Integrity
        broken_edges = []
        adj = {}
        rev_adj = {} # indegree map
        
        for n in nodes:
            nid = n["data"]["id"]
            adj[nid] = []
            rev_adj[nid] = []
            
        for e in edges:
            data = e["data"]
            src = data["source"]
            tgt = data["target"]
            
            if src not in node_ids or tgt not in node_ids:
                broken_edges.append(data["id"])
            
            if src in node_ids and tgt in node_ids:
                adj[src].append(tgt)
                rev_adj[tgt].append(src)

        # 2. Orphans (Degree 0)
        orphans = []
        roots = [] 
        for nid in node_ids:
            if not adj[nid] and not rev_adj[nid]:
                orphans.append(nid)
            elif not rev_adj[nid]:
                # In-degree 0 but has out-edges -> Root
                roots.append(nid)
                
        # 3. Components (BFS)
        visited = set()
        components = 0
        for nid in node_ids:
            if nid not in visited:
                components += 1
                queue = [nid]
                while queue:
                    curr = queue.pop(0)
                    if curr in visited: continue
                    visited.add(curr)
                    # Undirected traversal
                    neighbors = adj.get(curr, []) + rev_adj.get(curr, [])
                    for nbr in neighbors:
                        if nbr not in visited:
                            queue.append(nbr)
                            
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "broken_edges": broken_edges,
            "orphan_nodes": orphans,
            "root_nodes": roots,
            "components": components,
            "is_fragmented": components > 1
        }
