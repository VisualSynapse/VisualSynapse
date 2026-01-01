from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class NodeType(str, Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    LOGIC = "logic"
    LOGIC_GROUP = "logic_group"
    DATA_GROUP = "data_group"
    CALL_STEP = "call_step"
    DATA = "data"
    EXTERNAL = "external"
    MERGE = "merge"

class EdgeType(str, Enum):
    FLOW = "flow"       # Control flow (next step)
    CALLS = "calls"     # Function call
    DEFINES = "defines" # Hierarchy (File -> Class)
    IMPORTS = "imports" # Dependency

class VisualNode(BaseModel):
    id: str
    type: str # Using str instead of NodeType for flexibility with React Flow defaults
    label: str
    parentId: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # React Flow specific
    position: Optional[Dict[str, float]] = None

class VisualEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "default" # Using str for React Flow compatibility
    label: Optional[str] = ""
    data: Dict[str, Any] = Field(default_factory=dict)

class GraphData(BaseModel):
    nodes: List[VisualNode]
    edges: List[VisualEdge]
