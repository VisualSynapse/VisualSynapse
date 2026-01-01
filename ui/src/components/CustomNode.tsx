import React, { useState, memo } from 'react';
import { NodeProps, Node, Handle, Position } from '@xyflow/react';
import { Box, ChevronRight, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { NodeData } from '@/types';
import { nodeIcons, nodeColors } from '@/constants/nodeStyles';
import { useGraphStore } from '@/stores/useGraphStore';

export const CustomNode = memo(({ id, data, selected }: NodeProps<Node<NodeData>>) => {
    const Icon = nodeIcons[data.type] || Box;
    const [isHovered, setIsHovered] = useState(false);
    const toggleNode = useGraphStore((state) => state.toggleNode);
    const allNodes = useGraphStore((state) => state.nodes);

    const childCount = React.useMemo(() => {
        // FAST PATH: Use pre-calculated children list from backend if available
        if (Array.isArray(data.children) && data.children.length > 0) {
            return data.children.length;
        }

        // SLOW FALLBACK: Scan all nodes
        return allNodes.filter(n => {
            const parentId = n.data.parentId || (n.data as any).parent;
            return parentId === id;
        }).length;
    }, [allNodes, id, data.children]);

    const hasChildren = childCount > 0;

    const handleToggle = (e: React.MouseEvent) => {
        e.stopPropagation();
        toggleNode(id);
    };

    return (
        <div
            className={cn(
                "group relative px-4 py-3 min-w-[180px] rounded-xl border-2 transition-all duration-300 backdrop-blur-sm",
                selected
                    ? "border-primary/70 shadow-[0_0_30px_rgba(59,130,246,0.4)] bg-primary/10"
                    : "border-border/50 bg-card/80 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)]",
                "hover:scale-105"
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Handle
                type="target"
                position={Position.Top}
                className="!w-3 !h-3 !bg-primary/60 !border-2 !border-primary"
            />

            <div className="flex items-center gap-3">
                <div className={cn(
                    "p-2 rounded-lg transition-all duration-300",
                    `bg-${nodeColors[data.type]}/20`,
                    isHovered && "scale-110"
                )}>
                    <Icon className={cn("w-4 h-4", `text-${nodeColors[data.type]}`)} />
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-foreground truncate">
                            {data.label}
                        </p>
                        {hasChildren && (
                            <Badge
                                variant="outline"
                                className={cn(
                                    "h-5 px-1.5 text-xs cursor-pointer transition-all",
                                    data.expanded
                                        ? "bg-primary/20 text-primary border-primary/40"
                                        : "bg-muted text-muted-foreground border-muted-foreground/30"
                                )}
                                onClick={handleToggle}
                            >
                                {data.expanded ? '−' : '+'} {childCount}
                            </Badge>
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground capitalize mt-0.5">
                        {data.type}
                    </p>
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} className="w-2.5 h-2.5 !bg-primary border-2 border-background" />
        </div>
    );
}, (prev: NodeProps<Node<NodeData>>, next: NodeProps<Node<NodeData>>) => {

    return prev.selected === next.selected &&
        prev.data.label === next.data.label &&
        prev.data.expanded === next.data.expanded &&
        prev.data.isMatch === next.data.isMatch;
});

CustomNode.displayName = 'CustomNode';

export const nodeTypes = {
    custom: CustomNode,
};
