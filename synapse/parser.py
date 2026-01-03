
import logging
import json
import os
from tree_sitter import Language, Parser, Query, QueryCursor
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from synapse.visual_base_models import VisualNode, VisualEdge, NodeType, EdgeType

logger = logging.getLogger("synapse.parser")

# This will be overridden by main.py but kept for standalone testing
class MockGraph:
    def add_node(self, *args): pass
    def add_edge(self, *args): pass
    def clear_graph(self): pass
    def get_graph(self): return {"elements": {"nodes": [], "edges": []}}

# Generic mapping of tree-sitter node types to VisualSynapse types
# To add a new language: 
# 1. Install 'tree-sitter-<lang>' 
# 2. Add 'import tree-sitter-<lang>' in ASTParser.__init__
# 3. Add mapping here matching Tree-sitter node types to VisualSynapse categories.
LANGUAGE_MAPS = {
    "python": {
        "class": ["class_definition"],
        "function": ["function_definition"],
        "logic": ["if_statement", "for_statement", "while_statement", "with_statement", "try_statement"],
        "loop": ["for_statement", "while_statement"],
        "branch": ["elif_clause", "else_clause", "try_statement", "except_clause"],
        "call": ["call"],
        "assignment": ["assignment"]
    },
    "javascript": {
        "class": ["class_declaration"],
        "function": ["function_declaration", "arrow_function", "method_definition"],
        "logic": ["if_statement", "for_statement", "while_statement", "try_statement", "switch_statement"],
        "loop": ["for_statement", "while_statement", "do_statement", "for_in_statement"],
        "branch": ["elif_clause", "else_clause", "try_statement", "catch_clause", "switch_case"],
        "call": ["call_expression"],
        "assignment": ["assignment_expression"]
    },
    "typescript": {
        "class": ["class_declaration"],
        "function": ["function_declaration", "arrow_function", "method_definition"],
        "logic": ["if_statement", "for_statement", "while_statement", "try_statement", "switch_statement"],
        "loop": ["for_statement", "while_statement", "do_statement", "for_in_statement"],
        "branch": ["elif_clause", "else_clause", "try_statement", "catch_clause", "switch_case"],
        "call": ["call_expression"],
        "assignment": ["assignment_expression"]
    },
    "tsx": {
        "class": ["class_declaration"],
        "function": ["function_declaration", "arrow_function", "method_definition", "function"],
        "logic": ["if_statement", "for_statement", "while_statement", "try_statement", "switch_statement"],
        "loop": ["for_statement", "while_statement", "do_statement", "for_in_statement"],
        "branch": ["elif_clause", "else_clause", "try_statement", "catch_clause", "switch_case"],
        "call": ["call_expression", "jsx_element", "jsx_self_closing_element"],
        "assignment": ["assignment_expression"]
    }
}

class ASTParser:
    """Static code analyzer using Tree-sitter to parse code into a graph."""
    
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.id_counter = 0
        self.parsers = {}
        self.languages = {}
        self.method_to_class = {}

    def _get_language(self, lang_key: str) -> Language:
        """Lazy load language parser only when needed."""
        if lang_key in self.languages:
            return self.languages[lang_key]
            
        logger.info(f"Loading Tree-sitter grammar for {lang_key}")
        try:
            if lang_key == "python":
                import tree_sitter_python
                lang = Language(tree_sitter_python.language())
            elif lang_key == "javascript":
                import tree_sitter_javascript
                lang = Language(tree_sitter_javascript.language())
            elif lang_key == "typescript":
                import tree_sitter_typescript
                lang = Language(tree_sitter_typescript.language_typescript())
            elif lang_key == "tsx":
                import tree_sitter_typescript
                lang = Language(tree_sitter_typescript.language_tsx())
            else:
                raise ValueError(f"Unsupported language: {lang_key}")
                
            self.languages[lang_key] = lang
            logger.info(f"Successfully loaded {lang_key} grammar")
            return lang
        except ImportError:
            missing_pkg = f"tree-sitter-{lang_key}"
            raise ImportError(
                f"Language '{lang_key}' requires the '{missing_pkg}' package. "
                f"Please install it using: pip install {missing_pkg}"
            )

    def parse_code(self, code_str: str, filename: str = "", detail_level: str = "full") -> Dict[str, Any]:
        """Parse code string and return graph representation."""
        logger.info(f"Analyzing code from {filename or 'snippet'} (detail: {detail_level})")
        self.nodes = []
        self.edges = []
        self.id_counter = 0
        self.method_to_class = {}
        self.current_filename = filename
        self.detail_level = detail_level

        # Detect language
        logger.debug(f"Detecting language for: {filename}")
        ext = filename.split('.')[-1] if '.' in filename else "python"
        lang_key = "python"
        if ext in ["js", "jsx"]: lang_key = "javascript"
        elif ext == "ts": lang_key = "typescript"
        elif ext == "tsx": lang_key = "tsx"
        
        self.current_lang = lang_key
        self.current_map = LANGUAGE_MAPS.get(lang_key, LANGUAGE_MAPS["python"])
        
        # Get appropriate language and parser
        lang_obj = self._get_language(lang_key)
        parser = Parser(lang_obj)

        # Add File Root Node
        logger.info(f"Initialized graph structure for {filename}")
        file_label = filename.split('/')[-1] if filename else "Code"
        file_id = f"file_{file_label}"
        self._add_node(file_id, file_label, "file")
        self.file_root_id = file_id

        try:
            tree = parser.parse(bytes(code_str, "utf8"))
            logger.debug(f"Tree-sitter AST generated for {filename}")
        except Exception as e:
            logger.error(f"Tree-sitter parsing failed for {filename}: {e}")
            return {"error": f"Parsing Error: {e}"}

        root_node = tree.root_node
        
        logger.debug("Phase 1: Building class/function structural tree")
        code_bytes = bytes(code_str, "utf8")

        self._visit_structure(root_node, parent_id=file_id)
        
        # Phase 2: Control Flow
        if detail_level in ["full", "medium"]:
            # Use specific queries to extract major logic blocks
            logger.debug(f"Phase 2: Querying logic patterns (Language: {lang_key})")
            self._query_logic(root_node, lang_key, code_bytes)
        
        # 3. Post-process: Add hierarchy metadata for drill-down
        logger.info(f"Post-processing: Building hierarchy for {len(self.nodes)} nodes")
        self._add_hierarchy_metadata()
        
        logger.info(f"Parsing complete: {len(self.nodes)} nodes, {len(self.edges)} edges")

        return {
            "elements": {
                "nodes": self.nodes,
                "edges": self.edges
            }
        }
    
    def _add_hierarchy_metadata(self):
        """Builds virtual parent groups and children lists for hierarchical drill-down."""
        
        logger.debug("Filtering and grouping function children by type")
        function_children = {}  # container_id -> {"logic": [], "data": [], "other": []}
        
        for node_dict in self.nodes:
            node = node_dict['data']
            parent_id = node.get('parentId')
            node_type = node.get('type')
            
            if parent_id:
                parent_node = next((n['data'] for n in self.nodes if n['data']['id'] == parent_id), None)
                if parent_node and parent_node['type'] in ['file', 'class', 'function']:
                    if parent_id not in function_children:
                        function_children[parent_id] = {"logic": [], "data": [], "other": []}
                    
                    if node_type in ['call_step', 'logic', 'merge', 'external']:
                        logger.debug(f"Grouping logic node {node['id']} under parent {parent_id}")
                        function_children[parent_id]["logic"].append(node_dict)
                    elif node_type == 'data':
                        logger.debug(f"Grouping data node {node['id']} under parent {parent_id}")
                        function_children[parent_id]["data"].append(node_dict)
                    else:
                        function_children[parent_id]["other"].append(node_dict)
        
        logger.debug("Creating virtual group nodes (logic_group/data_group)")
        for container_id, children_by_type in function_children.items():
            # Create Logic Group
            if children_by_type["logic"]:
                logic_group_id = f"{container_id}_logic_group"
                self._add_node(
                    logic_group_id, 
                    f"Logic ({len(children_by_type['logic'])})", 
                    "logic_group",
                    parent=container_id
                )
                for logic_node_dict in children_by_type["logic"]:
                    logic_node_dict['data']['parentId'] = logic_group_id
            
            # Create Data Group
            if children_by_type["data"]:
                data_group_id = f"{container_id}_data_group"
                self._add_node(
                    data_group_id,
                    f"Data ({len(children_by_type['data'])})",
                    "data_group",
                    parent=container_id
                )
                for data_node_dict in children_by_type["data"]:
                    data_node_dict['data']['parentId'] = data_group_id
        
        logger.debug("Mapping children IDs back to parents for UI drill-down")
        for node_dict in self.nodes:
            node = node_dict['data']
            parent_id = node.get('parentId')
            
            if parent_id:
                parent_node_dict = next((n for n in self.nodes if n['data']['id'] == parent_id), None)
                if parent_node_dict:
                    parent_data = parent_node_dict['data']
                    if 'children' not in parent_data:
                        parent_data['children'] = []
                    
                    if node['id'] not in parent_data['children']:
                        parent_data['children'].append(node['id'])
                    else:
                        logger.debug(f"Skipping duplicate child {node['id']} for parent {parent_id}")

    def _get_id(self, prefix: str) -> str:
        self.id_counter += 1
        return f"{prefix}_{self.id_counter}"

    def _add_node(self, node_id: str, label: str, type: str, parent: Optional[str] = None, lineno: Optional[int] = None, is_library: bool = False, filename: str = ""):
        # Standardized node addition
        if any(n['data']['id'] == node_id for n in self.nodes):
            logger.debug(f"Attempted to add duplicate node: {node_id}")
            return
        
        final_filename = filename if filename else getattr(self, 'current_filename', "")
        
        node = VisualNode(
            id=node_id,
            type=type,
            label=label,
            parentId=parent,
            data={
                "id": node_id,
                "label": label,
                "type": type,
                "parentId": parent,
                "lineno": lineno,
                "file": final_filename,
                "is_library": is_library
            }
        )
        logger.debug(f"Node added: [{type}] {label} (ID: {node_id})")
        self.nodes.append({"data": node.model_dump(by_alias=True)})

        # Automatically add containment edge if parent exists
        if parent:
            self._add_edge(parent, node_id, type="contains", label="contains")

    def _add_edge(self, source: str, target: str, type: str = "flow", label: str = ""):
        edge = VisualEdge(
            id=f"e_{source}_{target}_{self.id_counter}",
            source=source,
            target=target,
            type=type,
            label=label
        )
        logger.debug(f"Edge added: {source} --({type}:{label})--> {target}")
        self.id_counter += 1
        self.edges.append({"data": edge.model_dump(by_alias=True)})

    def _get_text(self, node) -> str:
        if not node: return ""
        return node.text.decode('utf8')

    def _visit_structure(self, node, parent_id=None, parent_class=None):
        """Builds class/function tree first."""
        node_type = node.type
        
        if node_type in self.current_map["class"]:
            name_node = node.child_by_field_name('name')
            if name_node:
                class_name = self._get_text(name_node)
                logger.info(f"Parser: Found class '{class_name}' at line {node.start_point[0] + 1}")
                self._add_node(class_name, class_name, "class", parent=parent_id, lineno=node.start_point[0] + 1)
                
                # Register methods/child structures
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        if child.type in self.current_map["function"]:
                            m_name_node = child.child_by_field_name('name')
                            if m_name_node:
                                m_name = self._get_text(m_name_node)
                                self.method_to_class[m_name] = class_name
                self._visit_structure(child, parent_id=class_name, parent_class=class_name)
            

        elif node_type in self.current_map["function"]:
            name_node = node.child_by_field_name('name')
            func_name = None
            
            if name_node:
                func_name = self._get_text(name_node)
            else:
                parent = node.parent
                if parent and parent.type == 'variable_declarator':
                    p_name = parent.child_by_field_name('name')
                    if p_name:
                        func_name = self._get_text(p_name)
            
            if func_name:
                node_id = f"{parent_class}.{func_name}" if parent_class else func_name
                logger.debug(f"Parser: Found function '{node_id}' at line {node.start_point[0] + 1}")
                self._add_node(node_id, func_name, "function", parent=parent_id if parent_id else parent_class, lineno=node.start_point[0] + 1)
                parent_id = node_id
        
        for child in node.children:
            self._visit_structure(child, parent_id=parent_id, parent_class=parent_class)

    def _query_logic(self, root_node, lang_key: str, code_bytes: bytes):
        """
        Walks the AST to extract logic nodes with proper branching:
        - if/elif/else with TRUE/FALSE edge labels
        - for/while loops with body edges
        - assignments and function calls
        """
        
        def find_parent_scope(node):
            curr = node
            while curr:
                if curr.type in self.current_map["function"]:
                    name_node = curr.child_by_field_name('name')
                    if name_node:
                        func_name = name_node.text.decode('utf8')
                        for n in self.nodes:
                            if n['data']['type'] == 'function' and n['data']['label'] == func_name:
                                return n['data']['id']
                if curr.type == 'program' or curr.type == 'module':
                    return self.file_root_id
                curr = curr.parent
            return self.file_root_id

        processed_nodes = set()
        created_node_ids = {}  # ast_node.id -> our_node_id
        
        # Node type mappings per language
        logic_types = {
            "python": {
                "if": "if_statement",
                "elif": "elif_clause", 
                "else": "else_clause",
                "for": "for_statement",
                "while": "while_statement",
                "call": "call",
                "assignment": "assignment",
                "block": "block",
            },
            "javascript": {
                "if": "if_statement",
                "elif": None,
                "else": "else_clause",
                "for": "for_statement",
                "while": "while_statement",
                "call": "call_expression",
                "assignment": "assignment_expression",
                "block": "statement_block",
            },
            "typescript": {
                "if": "if_statement",
                "elif": None,
                "else": "else_clause",
                "for": "for_statement",
                "while": "while_statement",
                "call": "call_expression",
                "assignment": "assignment_expression",
                "block": "statement_block",
            },
            "tsx": {
                "if": "if_statement",
                "elif": None,
                "else": "else_clause",
                "for": "for_statement",
                "while": "while_statement",
                "call": "call_expression",
                "assignment": "assignment_expression",
                "block": "statement_block",
            }
        }
        
        types = logic_types.get(lang_key, logic_types["python"])
        
        def get_node_text(node, max_len=50):
            if not node:
                return ""
            return node.text.decode('utf8')[:max_len].replace('\n', ' ')
        
        def create_node(node_id, label, node_type, parent_scope, lineno, ast_node):
            self._add_node(node_id, label, node_type, parent=parent_scope, lineno=lineno)
            created_node_ids[ast_node.id] = node_id
            return node_id
        
        def get_first_child_node_id(block_node, check_self=False):
            """Find the first meaningful node and return its created node_id.
            If check_self=True, check if this node itself has an ID first."""
            if not block_node:
                return None
            # Check if this node itself was created
            if check_self and block_node.id in created_node_ids:
                return created_node_ids[block_node.id]
            # Check direct children
            for child in block_node.children:
                if child.id in created_node_ids:
                    return created_node_ids[child.id]
                # Only recurse into wrapper nodes like expression_statement, NOT into if bodies
                if child.type in ['expression_statement', 'module', 'program']:
                    result = get_first_child_node_id(child, check_self=True)
                    if result:
                        return result
            return None
        
        def get_last_child_node_id(block_node, check_self=False):
            """Find the last meaningful node in a block."""
            if not block_node:
                return None
            if check_self and block_node.id in created_node_ids:
                return created_node_ids[block_node.id]
            for child in reversed(block_node.children):
                if child.id in created_node_ids:
                    return created_node_ids[child.id]
                if child.type in ['expression_statement', 'module', 'program']:
                    result = get_last_child_node_id(child, check_self=True)
                    if result:
                        return result
            return None
        
        def get_node_or_first_child(ast_node):
            """Get this node's ID if it was created, or find first created child."""
            if ast_node.id in created_node_ids:
                return created_node_ids[ast_node.id]
            return get_first_child_node_id(ast_node, check_self=True)

        # Pass 1: Create all nodes
        def walk_create_nodes(node, depth=0):
            if node.id in processed_nodes:
                return
            
            node_type = node.type
            lineno = node.start_point[0] + 1
            parent_scope = find_parent_scope(node)
            
            if node_type == types["if"]:
                processed_nodes.add(node.id)
                cond_node = node.child_by_field_name('condition')
                cond_text = get_node_text(cond_node) if cond_node else "?"
                
                logic_id = self._get_id("if")
                create_node(logic_id, f"L{lineno}: if ({cond_text})", "logic", parent_scope, lineno, node)
                logger.debug(f"Created if node at L{lineno}")
                
                for child in node.children:
                    walk_create_nodes(child, depth + 1)
                return
            
            if types.get("elif") and node_type == types["elif"]:
                processed_nodes.add(node.id)
                cond_node = node.child_by_field_name('condition')
                cond_text = get_node_text(cond_node) if cond_node else "?"
                
                logic_id = self._get_id("elif")
                create_node(logic_id, f"L{lineno}: elif ({cond_text})", "branch", parent_scope, lineno, node)
                logger.debug(f"Created elif node at L{lineno}")
                
                for child in node.children:
                    walk_create_nodes(child, depth + 1)
                return
            
            if node_type == types["else"]:
                processed_nodes.add(node.id)
                
                logic_id = self._get_id("else")
                create_node(logic_id, f"L{lineno}: else", "branch", parent_scope, lineno, node)
                logger.debug(f"Created else node at L{lineno}")
                
                for child in node.children:
                    walk_create_nodes(child, depth + 1)
                return
            
            if node_type == types["for"]:
                processed_nodes.add(node.id)
                item_node = node.child_by_field_name('left')
                iter_node = node.child_by_field_name('right')
                
                if not item_node:
                    item_node = node.child_by_field_name('init')
                    iter_node = node.child_by_field_name('condition')
                
                item_text = get_node_text(item_node) if item_node else ""
                iter_text = get_node_text(iter_node) if iter_node else ""
                
                label = f"L{lineno}: for {item_text}"
                if iter_text:
                    label += f" in {iter_text}"
                
                logic_id = self._get_id("for")
                create_node(logic_id, label, "logic", parent_scope, lineno, node)
                logger.debug(f"Created for node at L{lineno}")
                
                for child in node.children:
                    walk_create_nodes(child, depth + 1)
                return
            
            if node_type == types["while"]:
                processed_nodes.add(node.id)
                cond_node = node.child_by_field_name('condition')
                cond_text = get_node_text(cond_node) if cond_node else "?"
                
                logic_id = self._get_id("while")
                create_node(logic_id, f"L{lineno}: while ({cond_text})", "logic", parent_scope, lineno, node)
                logger.debug(f"Created while node at L{lineno}")
                
                for child in node.children:
                    walk_create_nodes(child, depth + 1)
                return
            
            if node_type == types["assignment"]:
                processed_nodes.add(node.id)
                left_node = node.child_by_field_name('left')
                right_node = node.child_by_field_name('right')
                
                var_name = get_node_text(left_node, 30) if left_node else "?"
                value_text = get_node_text(right_node, 40) if right_node else "?"
                
                logic_id = self._get_id("assign")
                create_node(logic_id, f"L{lineno}: {var_name} = {value_text}", "data", parent_scope, lineno, node)
                logger.debug(f"Created assignment node at L{lineno}")
                return
            
            if node_type == types["call"]:
                processed_nodes.add(node.id)
                func_node = node.child_by_field_name('function')
                args_node = node.child_by_field_name('arguments')
                
                func_name = get_node_text(func_node, 30) if func_node else "?"
                args_text = get_node_text(args_node, 40) if args_node else "()"
                
                logic_id = self._get_id("call")
                create_node(logic_id, f"L{lineno}: {func_name}{args_text}", "call_step", parent_scope, lineno, node)
                logger.debug(f"Created call node at L{lineno}")
                return
            
            for child in node.children:
                walk_create_nodes(child, depth + 1)
        
        # Pass 2: Create edges with proper branching
        def walk_create_edges(node, prev_node_id=None):
            node_type = node.type
            my_node_id = created_node_ids.get(node.id)
            
            if node_type == types["if"]:
                if_node_id = my_node_id
                
                # Connect previous to this if
                if prev_node_id:
                    self._add_edge(prev_node_id, if_node_id, type="flow", label="next")
                
                branch_exits = []  # collect exit points of all branches
                
                # Find consequence (true block) and alternatives
                consequence = node.child_by_field_name('consequence')
                if consequence:
                    first_in_true = get_first_child_node_id(consequence)
                    if first_in_true:
                        self._add_edge(if_node_id, first_in_true, type="flow", label="true")
                    last_in_true = get_last_child_node_id(consequence)
                    if last_in_true:
                        branch_exits.append(last_in_true)
                    # Recurse into true block
                    walk_create_edges(consequence, None)
                
                # Find elif/else clauses
                last_branch_node = if_node_id
                for child in node.children:
                    if types.get("elif") and child.type == types["elif"]:
                        elif_node_id = created_node_ids.get(child.id)
                        if elif_node_id:
                            self._add_edge(last_branch_node, elif_node_id, type="flow", label="false")
                            
                            # elif's consequence
                            elif_body = child.child_by_field_name('consequence')
                            if elif_body:
                                first_in_elif = get_first_child_node_id(elif_body)
                                if first_in_elif:
                                    self._add_edge(elif_node_id, first_in_elif, type="flow", label="true")
                                last_in_elif = get_last_child_node_id(elif_body)
                                if last_in_elif:
                                    branch_exits.append(last_in_elif)
                                walk_create_edges(elif_body, None)
                            
                            last_branch_node = elif_node_id
                    
                    elif child.type == types["else"]:
                        else_node_id = created_node_ids.get(child.id)
                        if else_node_id:
                            self._add_edge(last_branch_node, else_node_id, type="flow", label="false")
                            
                            # else's body
                            for else_child in child.children:
                                if else_child.type == types.get("block", "block"):
                                    first_in_else = get_first_child_node_id(else_child)
                                    if first_in_else:
                                        self._add_edge(else_node_id, first_in_else, type="flow", label="body")
                                    last_in_else = get_last_child_node_id(else_child)
                                    if last_in_else:
                                        branch_exits.append(last_in_else)
                                    walk_create_edges(else_child, None)
                            
                            last_branch_node = else_node_id
                
                # Return the branch exits for the caller to connect to next statement
                return branch_exits if branch_exits else [if_node_id]
            
            elif node_type == types["for"] or node_type == types["while"]:
                loop_node_id = my_node_id
                
                if prev_node_id:
                    self._add_edge(prev_node_id, loop_node_id, type="flow", label="next")
                
                # Find body
                body = node.child_by_field_name('body')
                if body:
                    first_in_body = get_first_child_node_id(body)
                    if first_in_body:
                        self._add_edge(loop_node_id, first_in_body, type="flow", label="iterate")
                    walk_create_edges(body, None)
                
                return [loop_node_id]
            
            elif my_node_id:
                # Regular node (assignment, call, etc)
                if prev_node_id:
                    self._add_edge(prev_node_id, my_node_id, type="flow", label="next")
                return [my_node_id]
            
            else:
                # Container node - process children sequentially
                pending_exits = []  # exits from previous child that need to connect to next
                
                for child in node.children:
                    # Get this child's node ID, or first created node inside it
                    child_first = get_node_or_first_child(child)
                    
                    # Connect all pending exits to this child's first node
                    if child_first and pending_exits:
                        for exit_node in pending_exits:
                            label = "merge" if len(pending_exits) > 1 else "next"
                            self._add_edge(exit_node, child_first, type="flow", label=label)
                        pending_exits = []
                    
                    # Process this child and collect its exits
                    exits = walk_create_edges(child, None)
                    if exits:
                        pending_exits = exits
                
                return pending_exits
        
        # Execute passes
        walk_create_nodes(root_node)
        walk_create_edges(root_node)



    def generate_markdown(self, code_str: str, filename: str = "") -> str:
        """Generates a line-by-line markdown explanation of the code flow."""
        logger.info(f"Generating Markdown export for {filename or 'snippet'}")
        try:
            # reuse parse logic to populate nodes
            self.parse_code(code_str, filename)
        except:
            return "Failed to parse code."

        # Sort nodes by line number
        sorted_nodes = sorted(
            [n['data'] for n in self.nodes if n['data'].get('lineno')],
            key=lambda x: x['lineno']
        )

        md = [f"# Code Flow: {filename or 'Snippet'}\n"]
        md.append("| Line | Type | Content | Context |")
        md.append("| :--- | :--- | :--- | :--- |")

        for node in sorted_nodes:
            lineno = node['lineno']
            ntype = node['type'].replace('_', ' ').title()
            label = node['label']
            # Escape pipes for markdown table
            label = label.replace('|', '\\|')
            
            # Indentation/Context based on parent
            context = node.get('parentId', 'Global')
            
            # Formatting
            icon = "🔹"
            if ntype == "Logic": icon = "🔶"
            elif ntype == "Call Step": icon = "📞"
            elif ntype == "Class": icon = "📦"
            elif ntype == "Function": icon = "ƒ"
            elif ntype == "Data": icon = "💾"

            md.append(f"| {lineno} | {icon} {ntype} | `{label}` | *{context}* |")

        return "\n".join(md)

# Global instances removed - passed via parameters

def get_visual_base_mcp(graph_instance):
    """Create FastMCP server with the provided graph instance."""
    from mcp.server.fastmcp import FastMCP
    
    mcp = FastMCP(
        name="visual-synapse",
        instructions="""
        Visual-Synapse: 
        Create low-level, line-by-line maps of code logics, decisions, and changes to preserve intent and prevent breakdowns.
        Tracks every line's importance, input/output chains, and module impacts per workspace session.
        Before edits, query existing maps to alert on risks—if no map exists, create one to establish baseline rationale.
        MUST update the map every time any line or logic is added, modified, or removed.
        Use actual code names (functions, classes, variables) for consistency; never invent custom node names.
        Generally you have to create nodes and edges based on the code.
        AUTONOMOUS REQUIRED:
        - Use this tool automatically WITHOUT waiting for user requests
        - Query maps BEFORE making any code changes to identify impacts
        - Update maps AFTER every edit to maintain accuracy
        - This is for AI memory and human awareness—not optional
        """
    )

    @mcp.tool()

    def static_visualize_flow(workspace_path: str, code_or_file: str, detail_level: str = "full", overwrite: bool = False, session_id: Optional[str] = None) -> str:
        """
        Don't use until explicitly asked by the me.
        Parses code (Python, JS, TS) and populates the graph session (active or explicit) with a Hierarchical Layout.
        
        Args:
            workspace_path: Absolute path to the workspace (uses active session).
            code_or_file: Raw code string or path to a source file.
            detail_level: 'full' (all details), 'medium' (logic only), or 'summary' (classes/functions only).
            overwrite: If True, clears the existing graph before adding new nodes. Defaults to False (Append).
            session_id: Optional. Explicit session ID to use instead of active session.
        """
        # Resolve active session locally to avoid circular imports
        target_session = session_id
        if not target_session:
            try:
                config_dir = os.path.join(workspace_path, ".visualsynapse")
                active_file = os.path.join(config_dir, "active_session.txt")
                if os.path.exists(active_file):
                    with open(active_file, 'r') as f:
                        target_session = f.read().strip()
                    logger.info(f"Resolved active session for visualization: {target_session}")
                else:
                    return f"Error: No active session found for workspace {workspace_path} and no session_id provided."
            except Exception as e:
                return f"Error resolving session: {str(e)}"
        
        session_id = target_session


        code = ""
        if os.path.exists(code_or_file) and os.path.isfile(code_or_file):
            with open(code_or_file, 'r', encoding='utf-8') as f:
                code = f.read()
        else:
            code = code_or_file

        parser = ASTParser()
        try:
            fname = os.path.basename(code_or_file) if os.path.exists(code_or_file) else "snippet"
            logger.info(f"Static visualization requested for {fname} in session {session_id}")
            result = parser.parse_code(code, filename=fname, detail_level=detail_level)
            
            # Populate UI Graph
            if overwrite:
                graph_instance.clear_graph(session_id)
            for node in result["elements"]["nodes"]:
                d = node["data"]
                # Filter unknown types if necessary, or let GraphManager handle defaulting
                graph_instance.add_node(session_id, d["id"], d["label"], d["type"], {k:v for k,v in d.items() if k not in ["id", "label", "type"]})
            for edge in result["elements"]["edges"]:
                d = edge["data"]
                graph_instance.add_edge(session_id, d["source"], d["target"], d["type"], d.get("label", ""))

            base_dir = os.path.dirname(os.path.abspath(__file__))
            port_file = os.path.join(base_dir, ".ui_port")
            port = "8080"
            if os.path.exists(port_file):
                try:
                    with open(port_file, 'r') as f:
                        port = f.read().strip()
                except:
                    pass
            
            ui_url = f"http://localhost:{port}/?session={session_id}"
            
            if detail_level == "summary":
                structures = [n["data"]["label"] for n in result["elements"]["nodes"] if n["data"]["type"] in ["class", "function"]]
                return f"Parsed {len(result['elements']['nodes'])} nodes into session '{session_id}'. Structures: {', '.join(structures)}. View at {ui_url}"
            
            return f"Populated session '{session_id}' with {len(result['elements']['nodes'])} nodes. Visualization: {ui_url}"
        except Exception as e:
            return f"Analysis failed: {str(e)}"
            


    return mcp

