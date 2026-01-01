import React, { useState, useCallback, useEffect, memo } from 'react';
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import {
    ReactFlow,
    Node,
    Edge,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Panel,
    MiniMap,
    NodeProps,
    Handle,
    Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import {
    FileCode,
    Box,
    Braces,
    GitBranch,
    ChevronRight,
    ChevronDown,
    X,
    Maximize2,
    Minimize2,
    Code2,
    Layers,
    Play,
    Activity,
    RefreshCw,
    FolderKanban,
    Plus,
    Check,
    Search,
    Moon,
    Sun,
    Download,
    FileText,
    LayoutGrid,
    Image as ImageIcon
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useTheme } from '@/context/ThemeContext';
import { useGraphStore } from '@/stores/useGraphStore';
import { useShallow } from 'zustand/react/shallow';



const DropdownMenu = DropdownMenuPrimitive.Root;
const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
const DropdownMenuGroup = DropdownMenuPrimitive.Group;
const DropdownMenuPortal = DropdownMenuPrimitive.Portal;
const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

const DropdownMenuContent = React.forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
    <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
            ref={ref}
            sideOffset={sideOffset}
            className={cn(
                "z-50 min-w-[240px] overflow-hidden rounded-lg border border-border bg-popover/90 backdrop-blur-xl p-1 text-popover-foreground shadow-2xl animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2",
                className
            )}
            {...props}
        />
    </DropdownMenuPrimitive.Portal>
));
DropdownMenuContent.displayName = DropdownMenuPrimitive.Content.displayName;

const DropdownMenuItem = React.forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.Item>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
        inset?: boolean;
    }
>(({ className, inset, ...props }, ref) => (
    <DropdownMenuPrimitive.Item
        ref={ref}
        className={cn(
            "relative flex cursor-default select-none items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
            inset && "pl-8",
            className
        )}
        {...props}
    />
));
DropdownMenuItem.displayName = DropdownMenuPrimitive.Item.displayName;

const DropdownMenuRadioItem = React.forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.RadioItem>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.RadioItem>
>(({ className, children, ...props }, ref) => (
    <DropdownMenuPrimitive.RadioItem
        ref={ref}
        className={cn(
            "relative flex cursor-default select-none items-center rounded-md py-1.5 pl-8 pr-2 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
            className
        )}
        {...props}
    >
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
            <DropdownMenuPrimitive.ItemIndicator>
                <Check className="h-4 w-4" />
            </DropdownMenuPrimitive.ItemIndicator>
        </span>
        {children}
    </DropdownMenuPrimitive.RadioItem>
));
DropdownMenuRadioItem.displayName = DropdownMenuPrimitive.RadioItem.displayName;

const DropdownMenuSeparator = React.forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.Separator>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
    <DropdownMenuPrimitive.Separator
        ref={ref}
        className={cn("-mx-1 my-1 h-px bg-border", className)}
        {...props}
    />
));
DropdownMenuSeparator.displayName = DropdownMenuPrimitive.Separator.displayName;



interface NodeData extends Record<string, unknown> {
    label: string;
    type: string;
    expanded?: boolean;
    filename?: string;
    lineno?: number;
    children?: string[];
    metadata?: Record<string, any>;
    isMatch?: boolean;
}

interface CodeSnippet {
    file: string;
    lines: { number: number; content: string }[];
    error?: string;
}

const nodeIcons: Record<string, any> = {
    file: FileCode,
    class: Box,
    function: Braces,
    logic: GitBranch,
    call_step: Play,
    external: Activity,
    logic_group: Layers,
    data: Code2,
};

const nodeColors: Record<string, string> = {
    file: 'from-slate-500/10 to-slate-600/10 border-slate-500/30',
    class: 'from-emerald-500/10 to-emerald-600/10 border-emerald-500/30',
    function: 'from-violet-500/10 to-violet-600/10 border-violet-500/30',
    logic: 'from-orange-500/10 to-orange-600/10 border-orange-500/30',
    logic_group: 'from-blue-500/10 to-blue-600/10 border-blue-500/30 border-dashed',
    data: 'from-sky-500/10 to-sky-600/10 border-sky-500/30',
};

const CustomNode = memo(({ id, data, selected }: NodeProps<Node<NodeData>>) => {
    const Icon = nodeIcons[data.type] || Box;
    const colorClass = nodeColors[data.type] || 'from-gray-500/10 to-gray-600/10 border-gray-500/30';
    const [isHovered, setIsHovered] = useState(false);
    const hasChildren = data.children && data.children.length > 0;
    const { toggleNode } = useGraphStore();

    return (
        <div
            className={cn(
                "relative pl-3 pr-2 py-2.5 rounded-xl border backdrop-blur-3xl bg-gradient-to-br transition-all duration-300 min-w-[180px] group",
                colorClass,
                data.isMatch ? "ring-2 ring-primary shadow-[0_0_30px_rgba(16,185,129,0.4)] scale-105 z-10 border-primary" : "border-opacity-40",
                selected ? "ring-1 ring-primary/50 border-primary/50" : "",
                isHovered ? "shadow-[0_0_20px_rgba(255,255,255,0.05)] border-opacity-80" : "shadow-md"
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-primary border-2 border-background opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="flex items-center gap-2.5">
                <div className={cn("p-1.5 rounded-md bg-background/40 border border-white/5", isHovered && "bg-background/60")}>
                    <Icon className="w-3.5 h-3.5 text-foreground/80" />
                </div>

                <div className="flex-1 overflow-hidden min-w-0 flex flex-col justify-center">
                    <div className="font-semibold text-[11px] text-foreground/90 truncate leading-tight select-none">{data.label}</div>
                    {data.lineno && (
                        <div className="text-[9px] text-muted-foreground/70 font-mono leading-none mt-0.5">L{data.lineno}</div>
                    )}
                </div>

                {hasChildren && (
                    <div
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleNode(id);
                        }}
                        className={cn(
                            "flex items-center justify-center w-6 h-6 rounded-lg cursor-pointer transition-all active:scale-90",
                            "hover:bg-foreground/10 hover:text-foreground",
                            data.expanded ? "bg-primary/10 text-primary" : "bg-transparent text-muted-foreground/60"
                        )}
                        role="button"
                    >
                        {data.expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </div>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-primary border-2 border-background opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
    );
}, (prev: any, next: any) => {

    return prev.selected === next.selected &&
        prev.data.label === next.data.label &&
        prev.data.expanded === next.data.expanded &&
        prev.data.isMatch === next.data.isMatch;
});

const nodeTypes = {
    custom: CustomNode as any,
};

const Sidebar: React.FC<{ selectedNode: Node<NodeData> | null; codeSnippet: CodeSnippet | null; onClose: () => void }> = ({ selectedNode, codeSnippet, onClose }) => {
    if (!selectedNode) return null;

    return (
        <div className="absolute right-0 top-0 bottom-0 w-[400px] bg-background/80 backdrop-blur-3xl border-l border-border/50 shadow-2xl z-20 flex flex-col animate-in slide-in-from-right duration-500 ease-out">
            <div className="flex items-center justify-between p-6 border-b border-border/50">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                        <Code2 className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                        <h3 className="font-bold text-foreground text-sm tracking-tight">Code Intelligence</h3>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">Inspector</p>
                    </div>
                </div>
                <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-foreground/5 transition-colors">
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-6 space-y-8">
                    <section>
                        <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-70">Node Identity</div>
                        <Card className="p-5 bg-card/40 border-border/50 backdrop-blur-xl hover:border-border/80 transition-colors">
                            <div className="space-y-4">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-xl bg-primary/10 ring-1 ring-primary/20">
                                        {React.createElement(nodeIcons[selectedNode.data.type] || Box, { className: "w-5 h-5 text-primary" })}
                                    </div>
                                    <div>
                                        <div className="font-bold text-foreground tracking-tight">{selectedNode.data.label}</div>
                                        <Badge variant="secondary" className="mt-1.5 text-[9px] font-bold uppercase tracking-wider h-5 flex items-center justify-center border-none">{selectedNode.data.type}</Badge>
                                    </div>
                                </div>
                                <div className="h-px bg-border/50" />
                                <div className="grid grid-cols-2 gap-4 text-[11px]">
                                    <div className="space-y-1">
                                        <p className="text-muted-foreground font-semibold uppercase tracking-wider opacity-60">Source File</p>
                                        <p className="text-foreground font-mono truncate">{(selectedNode.data.filename || (selectedNode.data.metadata as any)?.file)?.split('/').pop() || 'Internal'}</p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-muted-foreground font-semibold uppercase tracking-wider opacity-60">Line Position</p>
                                        <p className="text-foreground font-mono">{selectedNode.data.lineno || (selectedNode.data.metadata as any)?.lineno || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        </Card>
                    </section>

                    {codeSnippet && (
                        <section className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-70">Context Explorer</div>
                            <Card className="bg-card/40 border-border/50 overflow-hidden rounded-xl shadow-inner">
                                <div className="bg-muted/30 px-4 py-2 border-b border-border/50 flex justify-between items-center">
                                    <div className="flex gap-1.5">
                                        <div className="w-2.5 h-2.5 rounded-full bg-rose-500/40" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/40" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/40" />
                                    </div>
                                    <span className="text-[10px] text-muted-foreground font-mono tracking-tight lowercase truncate ml-4 max-w-[200px]">{selectedNode.data.filename || (selectedNode.data.metadata as any)?.file || 'unknown'}</span>
                                </div>
                                <div className="p-2 overflow-x-auto">
                                    {codeSnippet.error ? (
                                        <div className="p-6 text-[11px] text-rose-400 font-mono bg-rose-500/5 rounded-lg">{codeSnippet.error}</div>
                                    ) : (
                                        <pre className="p-4 text-[11px] font-mono text-foreground/80 leading-relaxed">
                                            <code>
                                                {codeSnippet.lines.map((line: any) => (
                                                    <div key={line.number} className={cn("flex gap-6 py-0.5", line.number === selectedNode.data.lineno ? "bg-primary/10 -mx-4 px-4 ring-1 ring-primary/30 text-primary font-bold" : "opacity-60")}>
                                                        <span className="w-8 text-muted-foreground text-right select-none">{line.number}</span>
                                                        <span className="whitespace-pre">{line.content}</span>
                                                    </div>
                                                ))}
                                            </code>
                                        </pre>
                                    )}
                                </div>
                            </Card>
                        </section>
                    )}
                </div>
            </ScrollArea>
        </div>
    );
};




const CodeLogicGraph: React.FC = () => {

    const {
        nodes: allNodes,
        edges: allEdges,
        expandedNodeIds,
        setGraph,
        updateGraph,
        onNodesChange,
        onEdgesChange
    } = useGraphStore(useShallow(state => ({
        nodes: state.nodes,
        edges: state.edges,
        expandedNodeIds: state.expandedNodeIds,
        setGraph: state.setGraph,
        updateGraph: state.updateGraph,
        onNodesChange: state.onNodesChange,
        onEdgesChange: state.onEdgesChange,
    })));

    const { theme, toggleTheme } = useTheme();

    const nodes = React.useMemo(() => {
        // [User Requested Manual Logic] - Explicit BFS for control
        const visibleNodeIds = new Set<string>();
        const nodeMap = new Map(allNodes.map(n => [n.id, n]));

        // 1. Identify Roots
        allNodes.forEach(node => {
            const parentId = node.data.parentId || (node.data as any).parent;
            if (!parentId || (typeof node.data.level === 'number' && node.data.level === 0)) {
                visibleNodeIds.add(node.id);
            }
        });

        // 2. BFS Traversal
        const queue = Array.from(visibleNodeIds);
        while (queue.length > 0) {
            const parentId = queue.shift()!;

            // Only search for children if the parent is marked as expanded
            if (expandedNodeIds.has(parentId)) {
                const parentNode = nodeMap.get(parentId);
                const childrenIds = parentNode?.data.children || (parentNode?.data as any)?.children;

                if (Array.isArray(childrenIds) && childrenIds.length > 0) {
                    // FAST PATH: Backend provided children list
                    childrenIds.forEach((childId: string) => {
                        if (nodeMap.has(childId) && !visibleNodeIds.has(childId)) {
                            visibleNodeIds.add(childId);
                            queue.push(childId);
                        }
                    });
                } else {
                    // SLOW PATH: Scan all nodes for matching parentId (legacy/fallback)
                    allNodes.forEach(n => {
                        const pId = n.data.parentId || (n.data as any).parent;
                        if (pId === parentId && !visibleNodeIds.has(n.id)) {
                            visibleNodeIds.add(n.id);
                            queue.push(n.id);
                        }
                    });
                }
            }
        }

        return allNodes.filter(n => visibleNodeIds.has(n.id)).map(n => ({
            ...n,
            data: {
                ...n.data,
                expanded: expandedNodeIds.has(n.id)
            }
        }));
    }, [allNodes, expandedNodeIds]);

    const edges = React.useMemo(() => {
        return useGraphStore.getState().getVisibleEdges();
    }, [allEdges, nodes]);


    const [selectedNode, setSelectedNode] = useState<Node<NodeData> | null>(null);
    const [codeSnippet, setCodeSnippet] = useState<CodeSnippet | null>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
    const [sessions, setSessions] = useState<string[]>(['default']);
    const [activeSession, setActiveSession] = useState<string>(() => {
        const params = new URLSearchParams(window.location.search);
        return params.get('session') || 'default';
    });
    const [searchQuery, setSearchQuery] = useState("");

    const fetchSessions = useCallback(async () => {
        try {
            const response = await fetch('/sessions');
            const data = await response.json();
            setSessions(data);
        } catch (e) { console.error('Failed to fetch sessions', e); }
    }, []);

    const fetchGraphData = useCallback(async (parentId?: string) => {
        try {
            let url = `/graph?session_id=${activeSession}`;
            if (parentId) url += `&parent_id=${parentId}`;

            const response = await fetch(url);
            const data = await response.json();

            if (data.elements) {

                if (parentId) {
                    updateGraph(data.elements.nodes, data.elements.edges);
                } else {


                    const nodes = data.elements.nodes.map((n: any) => {
                        const savedPos = n.data?.position;
                        if (savedPos && (savedPos.x !== 0 || savedPos.y !== 0)) {
                            console.log(`[Synapse] Restoring saved position for ${n.data.id}:`, savedPos);
                        }
                        return {
                            ...n,
                            id: n.data.id,
                            type: 'custom',
                            position: savedPos || { x: 0, y: 0 }
                        };
                    });
                    const edges = data.elements.edges.map((e: any) => ({
                        ...e,
                        id: e.data.id || `e-${e.data.source}-${e.data.target}`,
                        source: e.data.source,
                        target: e.data.target,
                        label: e.data?.label,
                        animated: true,
                        labelStyle: { fill: '#666', fontSize: 10, fontFamily: 'system-ui, sans-serif' },
                        labelBgStyle: { fill: 'transparent' },
                        labelBgPadding: [4, 2] as [number, number],
                    }));
                    setGraph(nodes, edges);
                }
            }
        } catch (error) {
            console.error('Failed to fetch graph data:', error);
        }
    }, [activeSession, setGraph, updateGraph]);

    const onNodeDragStop = useCallback((event: React.MouseEvent, node: Node) => {
        console.log(`[Synapse] Saving position for ${node.id}:`, node.position);
        fetch(`/api/sessions/${activeSession}/nodes/${node.id}/position`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: node.position.x, y: node.position.y })
        })
            .then(res => res.ok && console.log(`[Synapse] Position saved for ${node.id}`))
            .catch(err => console.error("Failed to save position", err));
    }, [activeSession]);

    const fetchCodeSnippet = useCallback(async (file: string, line: number) => {
        if (!file || !line) return;
        try {
            const response = await fetch(`/snippet?file=${encodeURIComponent(file)}&line=${line}`);
            const data = await response.json();
            setCodeSnippet(data);
        } catch (error) {
            console.error('Failed to fetch code snippet:', error);
            setCodeSnippet(null);
        }
    }, []);

    useEffect(() => {
        fetchSessions();
        fetchGraphData();

        const connectWebSocket = () => {
            try {
                setWsStatus('connecting');
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const ws = new WebSocket(`${protocol}//${window.location.host}/ws?session_id=${activeSession}`);

                ws.onopen = () => setWsStatus('connected');

                ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'graph_update' && message.session_id === activeSession) {
                        if (message.data && message.data.elements) {


                            updateGraph(message.data.elements.nodes, message.data.elements.edges);
                        }
                    }
                };

                ws.onclose = () => {
                    setWsStatus('disconnected');
                    setTimeout(connectWebSocket, 5000);
                };

                return ws;
            } catch (error) {
                setWsStatus('disconnected');
                return null;
            }
        };

        const ws = connectWebSocket();
        return () => ws?.close();
    }, [activeSession, fetchGraphData, fetchSessions, updateGraph]);





    useEffect(() => {


    }, [searchQuery]);

    const handleSessionChange = (newSession: string) => {
        console.log(`[Synapse] Session changed to: ${newSession}`);
        setActiveSession(newSession);
        const url = new URL(window.location.href);
        url.searchParams.set('session', newSession);
        window.history.pushState({}, '', url);
    };

    const handleRefresh = () => {
        console.log('[Synapse] Manual refresh triggered');
        fetchSessions();
        fetchGraphData();
    };

    const onConnect = useCallback(
        (params: Connection) => {
            console.log("[Synapse] Edge connected:", params);
        },
        []
    );

    const onNodeClick = useCallback(
        (_event: React.MouseEvent, node: Node<NodeData>) => {
            console.log(`[Synapse] Node clicked: ${node.id} (${node.data.type})`);
            setSelectedNode(node);

            if (node.data.children && node.data.children.length > 0) {
                useGraphStore.getState().toggleNode(node.id);
            }

            const file = node.data.filename || (node.data.metadata as any)?.file;
            const line = node.data.lineno || (node.data.metadata as any)?.lineno;

            if (file && line) {
                fetchCodeSnippet(file, line);
            }
        },
        [fetchCodeSnippet]
    );

    const onNodeDoubleClick = useCallback(
        (_event: React.MouseEvent, node: Node<NodeData>) => {
            const { toggleNode } = useGraphStore.getState();
            toggleNode(node.id);
        },
        []
    );

    const toggleFullscreen = useCallback(() => setIsFullscreen((prev) => !prev), []);

    const statusColor = {
        connected: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
        disconnected: 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]',
        connecting: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
    };

    return (
        <div className={cn(isFullscreen ? 'fixed inset-0 z-50' : 'relative w-full h-screen', 'bg-background text-foreground transition-colors duration-300 overflow-hidden font-sans selection:bg-primary/30')}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onNodeDoubleClick={onNodeDoubleClick}
                onNodeDragStop={onNodeDragStop}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.1}
                colorMode={theme}
            >
                <Background gap={24} color={theme === 'dark' ? "#ffffff05" : "#00000010"} />
                <Controls position="bottom-right" className="!bg-card/30 !backdrop-blur-xl !border-border/10 !shadow-2xl !fill-foreground/40 !m-8" />

                <Panel position="top-left" className="m-8 flex gap-4">
                    { }

                    <div className="flex items-center gap-1.5 bg-card/30 backdrop-blur-3xl border border-border/10 p-2 rounded-2xl shadow-2xl transition-all hover:border-border/20">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <button className="flex items-center gap-3 rounded-xl px-4 py-2.5 text-xs font-bold transition-all hover:bg-foreground/5 focus:outline-none bg-background/40 border border-border/5 group">
                                    <FolderKanban className="h-4 w-4 text-primary opacity-80 group-hover:scale-110 transition-transform" />
                                    <span className="text-foreground/90 min-w-[80px] text-left truncate tracking-tight">{activeSession}</span>
                                    <ChevronDown className="h-3 w-3 opacity-30 group-hover:opacity-60 transition-opacity" />
                                </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start" className="w-[220px]">
                                <DropdownMenuGroup>
                                    <DropdownMenuRadioGroup value={activeSession} onValueChange={handleSessionChange}>
                                        {sessions.map((s) => (
                                            <DropdownMenuRadioItem key={s} value={s} className="gap-3 py-2.5">
                                                <FolderKanban className="h-3.5 w-3.5 text-primary/60" />
                                                <span className="font-medium tracking-tight">{s}</span>
                                            </DropdownMenuRadioItem>
                                        ))}
                                    </DropdownMenuRadioGroup>
                                </DropdownMenuGroup>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => {
                                    const name = prompt("Enter new session name:");
                                    if (name) { handleSessionChange(name); handleRefresh(); }
                                }} className="gap-3 py-2.5 text-primary">
                                    <Plus className="h-3.5 w-3.5" />
                                    <span className="font-bold tracking-tight">New Analysis</span>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>

                        <div className="w-px h-8 bg-border/20 mx-1" />

                        <Button variant="ghost" size="icon" onClick={handleRefresh} className="w-10 h-10 rounded-xl hover:bg-foreground/5 active:scale-95 transition-all">
                            <RefreshCw className="w-4 h-4 text-foreground/40" />
                        </Button>

                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleTheme}
                            className="w-10 h-10 rounded-xl hover:bg-foreground/5 active:scale-95 transition-all"
                            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                        >
                            {theme === 'dark' ? <Sun className="w-4 h-4 text-foreground/40" /> : <Moon className="w-4 h-4 text-foreground/40" />}
                        </Button>

                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => useGraphStore.getState().resetLayout()}
                            className="w-10 h-10 rounded-xl hover:bg-foreground/5 active:scale-95 transition-all"
                            title="Reset Layout (Auto-arrange)"
                        >
                            <LayoutGrid className="w-4 h-4 text-foreground/40" />
                        </Button>


                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="w-10 h-10 rounded-xl hover:bg-foreground/5 active:scale-95 transition-all"
                                    title="Export"
                                >
                                    <Download className="w-4 h-4 text-foreground/40" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48 bg-card/50 backdrop-blur-xl border-border/10 text-foreground/80 rounded-xl shadow-2xl p-1.5">
                                <DropdownMenuItem
                                    className="text-[11px] font-medium p-2 rounded-lg hover:bg-foreground/5 cursor-pointer flex items-center gap-2 focus:bg-foreground/5 focus:text-foreground"
                                    onClick={async () => {
                                        try {
                                            const res = await fetch(`/export?session_id=${activeSession}&format=markdown`);
                                            const data = await res.json();
                                            const blob = new Blob([data.content], { type: 'text/markdown' });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = `${activeSession}_export.md`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        } catch (e) {
                                            console.error('Export failed:', e);
                                            alert("Export failed.");
                                        }
                                    }}
                                >
                                    <FileText className="w-3.5 h-3.5 opacity-70" />
                                    <span>Export as Markdown</span>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    className="text-[11px] font-medium p-2 rounded-lg hover:bg-foreground/5 cursor-pointer flex items-center gap-2 focus:bg-foreground/5 focus:text-foreground"
                                    onClick={async () => {
                                        try {
                                            const res = await fetch(`/export?session_id=${activeSession}&format=canvas`);
                                            const data = await res.json();
                                            const blob = new Blob([data.content], { type: 'application/json' });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = `${activeSession}.canvas`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        } catch (e) {
                                            console.error('Export failed:', e);
                                            alert("Export failed.");
                                        }
                                    }}
                                >
                                    <Layers className="w-3.5 h-3.5 opacity-70" />
                                    <span>Export as JSON Canvas</span>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    className="text-[11px] font-medium p-2 rounded-lg hover:bg-foreground/5 cursor-pointer flex items-center gap-2 focus:bg-foreground/5 focus:text-foreground"
                                    onClick={async () => {
                                        try {
                                            const flowElement = document.querySelector('.react-flow') as HTMLElement;
                                            if (!flowElement) return;

                                            const dataUrl = await toPng(flowElement, {
                                                backgroundColor: theme === 'dark' ? '#09090b' : '#ffffff',
                                                pixelRatio: 2,
                                                filter: (node) => {
                                                    // Exclude UI controls, panels, and minimap
                                                    if (node.classList && (
                                                        node.classList.contains('react-flow__panel') ||
                                                        node.classList.contains('react-flow__controls') ||
                                                        node.classList.contains('react-flow__minimap')
                                                    )) {
                                                        return false;
                                                    }
                                                    return true;
                                                }
                                            });

                                            const a = document.createElement('a');
                                            a.href = dataUrl;
                                            a.download = `${activeSession}_graph.png`;
                                            a.click();
                                        } catch (e) {
                                            console.error('Image export failed:', e);
                                            alert("Image export failed.");
                                        }
                                    }}
                                >
                                    <ImageIcon className="w-3.5 h-3.5 opacity-70" />
                                    <span>Export as Image (PNG)</span>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>

                    <div className="flex items-center bg-card/30 backdrop-blur-3xl border border-border/10 p-2 rounded-2xl shadow-2xl transition-all hover:border-border/20">
                        <div className="relative group px-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground group-focus-within:text-primary transition-colors" />
                            <input
                                placeholder="Search..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-24 focus:w-48 bg-background/50 border border-border/10 rounded-xl pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/30 transition-all font-medium"
                            />
                        </div>
                    </div>
                </Panel>

                <Panel position="top-right" className="m-8 space-y-4">
                    <div className="flex items-center gap-3 bg-card/30 backdrop-blur-3xl border border-border/10 px-4 py-2 rounded-full shadow-2xl ring-1 ring-border/5">
                        <div className={cn("w-2 h-2 rounded-full animate-pulse", statusColor[wsStatus])} />
                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">{wsStatus}</span>
                    </div>

                    <div className="flex flex-col gap-2 scale-110 origin-top-right">
                        <Button variant="outline" size="icon" onClick={toggleFullscreen} className="w-12 h-12 rounded-2xl bg-card/30 backdrop-blur-3xl border-border/10 shadow-2xl hover:bg-foreground/5 hover:scale-110 transition-all border-opacity-50">
                            {isFullscreen ? <Minimize2 className="w-5 h-5 text-foreground/70" /> : <Maximize2 className="w-5 h-5 text-foreground/70" />}
                        </Button>
                    </div>
                </Panel>

                <Panel position="bottom-left" className="m-8">
                    <div className="bg-card/30 backdrop-blur-3xl border border-border/10 p-4 rounded-2xl shadow-2xl flex gap-6 ring-1 ring-border/5">
                        {[
                            { icon: FileCode, color: 'text-slate-400', label: 'File', bg: 'bg-slate-500/10' },
                            { icon: Box, color: 'text-emerald-500', label: 'Class', bg: 'bg-emerald-500/10' },
                            { icon: Braces, color: 'text-violet-500', label: 'Func', bg: 'bg-violet-500/10' },
                            { icon: GitBranch, color: 'text-orange-500', label: 'Logic', bg: 'bg-orange-500/10' }
                        ].map((item, idx) => (
                            <div key={idx} className="flex items-center gap-2 group cursor-help">
                                <div className={cn("p-1.5 rounded-lg transition-colors", item.bg)}>
                                    <item.icon className={cn("w-3.5 h-3.5", item.color)} />
                                </div>
                                <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest group-hover:text-foreground transition-colors">{item.label}</span>
                            </div>
                        ))}
                    </div>
                </Panel>
            </ReactFlow>

            <Sidebar
                selectedNode={selectedNode}
                codeSnippet={codeSnippet}
                onClose={() => setSelectedNode(null)}
            />
        </div >
    );
};

export default CodeLogicGraph;
