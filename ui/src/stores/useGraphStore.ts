import { create } from 'zustand';
import { Node, Edge, applyNodeChanges, applyEdgeChanges, OnNodesChange, OnEdgesChange } from '@xyflow/react';
import { NodeData } from '../types';
import Dagre from '@dagrejs/dagre';

interface GraphState {
    nodes: Node<NodeData>[];
    edges: Edge[];
    expandedNodeIds: Set<string>;
    temporaryHighlight: string | null;

    setGraph: (nodes: Node<NodeData>[], edges: Edge[]) => void;
    updateGraph: (newNodesData: any[], newEdgesData: any[]) => void;
    toggleNode: (nodeId: string) => void;
    expandAll: () => void;
    collapseAll: () => void;
    resetLayout: () => void;
    setTemporaryHighlight: (nodeId: string | null) => void;

    onNodesChange: OnNodesChange<Node<NodeData>>;
    onEdgesChange: OnEdgesChange;


    getVisibleNodes: () => Node<NodeData>[];
    getVisibleEdges: () => Edge[];
}



const NODE_WIDTH = 200;
const NODE_HEIGHT = 60;

// Helper to determine edge style dynamically
const applyEdgeStyling = (edge: Edge, nodeMap: Map<string, Node<NodeData>>, tempHighlight: string | null) => {
    const sourceNode = nodeMap.get(edge.source);
    const targetNode = nodeMap.get(edge.target);

    // 1. Resolve effective colors (Persistent > Temporary)
    // Does the Source imply a color?
    let sourceColor: string | null = sourceNode?.data.highlightColor || null;
    if (tempHighlight && edge.source === tempHighlight) sourceColor = '#06b6d4'; // Cyan-500 for active temp

    // Does the Target imply a color?
    let targetColor: string | null = targetNode?.data.highlightColor || null;
    if (tempHighlight && edge.target === tempHighlight) targetColor = '#06b6d4';


    // 2. Logic: Smart Coloring
    // If Source is colored -> It pushes color to the edge (Flow)
    // If Target is colored -> It also pushes color
    // Conflict? Gradient.

    let stroke = '#64748b'; // Default Slate
    let strokeWidth = 1.5;
    let animated = edge.animated;

    if (sourceColor && targetColor && sourceColor !== targetColor) {
        // Dual Highlight -> Gradient (Not standard SVG support in basic stroke, needs Marker, but for now use Source)
        // Actually, CSS gradients on stroke are tricky in SVG without defs.
        // Fallback: Source wins for flow
        stroke = sourceColor;
        strokeWidth = 3;
        animated = true;
    } else if (sourceColor) {
        stroke = sourceColor;
        strokeWidth = 3;
        animated = true;
    } else if (targetColor) {
        stroke = targetColor;
        strokeWidth = 3;
        animated = true;
    } else {
        // Default Logic based on Type
        const data = edge.data as Record<string, any> || {};
        const t = data.type || 'default';
        const l = (data.label || '').toLowerCase(); // Safe access

        if (t === 'data' || t === 'data_flow') stroke = '#38bdf8';
        else if (t === 'call' || t === 'calls' || l.includes('calls') || l.includes('route')) stroke = '#8b5cf6';
        else if (t === 'inherits' || l.includes('inherits')) stroke = '#10b981';
        else if (t === 'import' || l.includes('import')) stroke = '#f59e0b';
        else if (l === 'contains' || t === 'structure') stroke = '#475569';
    }

    return {
        ...edge,
        animated,
        style: {
            stroke,
            strokeWidth,
        }
    };
};

const applyDagreLayout = (nodes: Node<NodeData>[], edges: Edge[], preservePositions: boolean = true): Node<NodeData>[] => {
    if (nodes.length === 0) return nodes;

    const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100, marginx: 50, marginy: 50 });

    nodes.forEach((node) => {
        g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    });

    edges.forEach((edge) => {
        g.setEdge(edge.source, edge.target);
    });

    nodes.forEach((node) => {
        const parentId = node.data.parentId || (node.data as any).parent;
        if (parentId && nodes.some(n => n.id === parentId)) {
            g.setEdge(parentId, node.id);
        }
    });

    Dagre.layout(g);

    return nodes.map((node) => {
        const nodeWithPosition = g.node(node.id);

        const hasExistingPosition = preservePositions &&
            node.position &&
            (node.position.x !== 0 || node.position.y !== 0);

        if (hasExistingPosition) {
            return node;
        }

        if (nodeWithPosition) {
            return {
                ...node,
                position: {
                    x: nodeWithPosition.x - NODE_WIDTH / 2,
                    y: nodeWithPosition.y - NODE_HEIGHT / 2,
                },
            };
        }
        return node;
    });
};


export const useGraphStore = create<GraphState>((set, get) => ({
    nodes: [],
    edges: [],
    expandedNodeIds: new Set<string>(),
    temporaryHighlight: null,

    setGraph: (nodes, edges) => {
        console.log('[Synapse] setGraph called', { nodeCount: nodes.length, edgeCount: edges.length });

        const layoutedNodes = applyDagreLayout(nodes, edges);
        const nodeMap = new Map(layoutedNodes.map(n => [n.id, n]));

        console.log('[Synapse] Graph loaded, expanding roots only by default.');
        const rootIds = layoutedNodes
            .filter(n => !n.data.parentId && !(n.data as any).parent)
            .map(n => n.id);
        const initialExpanded = new Set(rootIds);

        // Apply initial styling
        const styledEdges = edges.map(e => applyEdgeStyling(e, nodeMap, null));

        set({
            nodes: layoutedNodes,
            edges: styledEdges,
            expandedNodeIds: initialExpanded,
            temporaryHighlight: null
        });
    },

    onNodesChange: (changes) => {
        set({
            nodes: applyNodeChanges(changes, get().nodes),
        });
    },

    onEdgesChange: (changes) => {
        set({
            edges: applyEdgeChanges(changes, get().edges),
        });
    },

    setTemporaryHighlight: (nodeId: string | null) => {
        set((state) => {
            if (state.temporaryHighlight === nodeId) return state; // No change

            // Re-calc edges based on new temp highlight
            const nodeMap = new Map(state.nodes.map(n => [n.id, n]));
            const newEdges = state.edges.map(e => applyEdgeStyling(e, nodeMap, nodeId));

            return {
                temporaryHighlight: nodeId,
                edges: newEdges
            };
        });
    },

    updateGraph: (newNodesData: any[], newEdgesData: any[]) => {
        // Guard against empty updates causing "flashing" / disconnects
        if (!newNodesData || newNodesData.length === 0) {
            console.warn('[Synapse] Received empty graph update, ignoring.');
            return;
        }

        console.log('[Synapse] updateGraph called', { newNodes: newNodesData.length, newEdges: newEdgesData.length });
        set((state) => {
            const nodeMap = new Map(state.nodes.map(n => [n.id, n]));


            const mergedNodes = newNodesData.map((nodeData: any) => {
                const existing = nodeMap.get(nodeData.data?.id || nodeData.id);


                let position = existing?.position || nodeData.position || { x: 0, y: 0 };

                const id = nodeData.data?.id || nodeData.id;

                const isRoot = !nodeData.data?.parentId && !nodeData.data?.parent;

                return {
                    id,
                    type: 'custom',
                    position,
                    data: {
                        ...nodeData.data,
                        expanded: state.expandedNodeIds.has(id) || isRoot,
                        // Persist highlight color (should come from backend, but ensure it's mapped)
                        highlightColor: nodeData.data?.highlightColor
                    }
                } as Node<NodeData>;
            });



            const currentExpanded = new Set(state.expandedNodeIds);
            newNodesData.forEach((n: any) => {
                const id = n.data?.id || n.id;
                const isRoot = !n.data?.parentId && !n.data?.parent;
                if (isRoot) {
                    currentExpanded.add(id);
                }
            });

            // Re-map for Edge Styling
            const freshNodeMap = new Map(mergedNodes.map(n => [n.id, n]));

            const rawEdges = newEdgesData.map((edgeData: any) => ({
                id: edgeData.data?.id || `e-${edgeData.data?.source}-${edgeData.data?.target}`,
                source: edgeData.data?.source,
                target: edgeData.data?.target,
                label: edgeData.data?.label,
                data: edgeData.data,
                // temporary defaults, wil be overwritten by styling
                animated: false,
                style: {},
                labelStyle: { fill: '#666', fontSize: 10, fontFamily: 'system-ui, sans-serif' },
                labelBgStyle: { fill: 'transparent' },
                labelBgPadding: [4, 2] as [number, number],
            }));

            const styledEdges = rawEdges.map((e: any) => applyEdgeStyling(e, freshNodeMap, state.temporaryHighlight));

            const layoutedNodes = applyDagreLayout(mergedNodes as Node<NodeData>[], styledEdges as Edge[]);

            return { nodes: layoutedNodes, edges: styledEdges, expandedNodeIds: currentExpanded };
        });
    },

    toggleNode: (nodeId: string) => {
        set((state) => {
            const nextExpanded = new Set(state.expandedNodeIds);
            const isExpanding = !nextExpanded.has(nodeId);
            console.log(`[Synapse] toggleNode: ${nodeId} -> ${isExpanding ? 'EXPAND' : 'COLLAPSE'}`);

            if (nextExpanded.has(nodeId)) {
                nextExpanded.delete(nodeId);
            } else {
                nextExpanded.add(nodeId);
            }
            return { expandedNodeIds: nextExpanded };
        });
    },

    expandAll: () => {
        console.log('[Synapse] expandAll triggered');
        const { nodes } = get();
        const allIds = new Set(nodes.map((n) => n.id));
        set({ expandedNodeIds: allIds });
    },

    collapseAll: () => {
        console.log('[Synapse] collapseAll triggered');
        set({ expandedNodeIds: new Set() });
    },

    resetLayout: () => {
        console.log('[Synapse] resetLayout triggered');
        const { nodes, edges } = get();
        const resetNodes = nodes.map(n => ({ ...n, position: { x: 0, y: 0 } }));
        const layoutedNodes = applyDagreLayout(resetNodes, edges, false);
        set({ nodes: layoutedNodes });
    },

    getVisibleNodes: () => {
        const { nodes, expandedNodeIds } = get();

        const visibleNodeIds = new Set<string>();
        const nodeMap = new Map(nodes.map(n => [n.id, n]));


        nodes.forEach(node => {
            const parentId = node.data.parentId || node.data.parent as string;
            if (!parentId || (typeof node.data.level === 'number' && node.data.level === 0)) {
                visibleNodeIds.add(node.id);
            }
        });


        const queue = Array.from(visibleNodeIds);

        while (queue.length > 0) {
            const parentId = queue.shift()!;


            if (expandedNodeIds.has(parentId)) {
                const parentNode = nodeMap.get(parentId);


                const children = parentNode?.data.children || (parentNode?.data.data as any)?.children;

                if (Array.isArray(children)) {
                    children.forEach((childId: string) => {
                        if (!visibleNodeIds.has(childId) && nodeMap.has(childId)) {
                            visibleNodeIds.add(childId);
                            queue.push(childId);
                        }
                    });
                } else {

                    nodes.forEach(n => {
                        const pId = n.data.parentId || (n.data as any).parent;
                        if (pId === parentId && !visibleNodeIds.has(n.id)) {
                            visibleNodeIds.add(n.id);
                            queue.push(n.id);
                        }
                    });
                }
            }
        }

        return nodes.filter(n => visibleNodeIds.has(n.id)).map(n => ({
            ...n,
            data: {
                ...n.data,
                expanded: expandedNodeIds.has(n.id)
            }
        }));
    },

    getVisibleEdges: () => {
        const { edges } = get();
        const visibleNodes = get().getVisibleNodes();
        const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

        return edges.filter(e =>
            visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
        );
    }
}));
