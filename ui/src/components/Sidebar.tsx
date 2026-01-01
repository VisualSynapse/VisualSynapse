import React from 'react';
import { Node } from '@xyflow/react';
import { X, Box } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NodeData, CodeSnippet } from '@/types';
import { nodeIcons } from '@/constants/nodeStyles';

interface SidebarProps {
    selectedNode: Node<NodeData> | null;
    codeSnippet: CodeSnippet | null;
    onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ selectedNode, codeSnippet, onClose }) => {
    if (!selectedNode) return null;

    return (
        <div className="absolute right-0 top-0 bottom-0 w-[400px] bg-background/80 backdrop-blur-3xl border-l border-border/50 shadow-2xl z-20 flex flex-col animate-in slide-in-from-right duration-500 ease-out">
            <div className="flex items-center justify-between p-6 border-b border-border/50">
                <div className="flex items-center gap-3">
                    { }
                </div>
                <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-white/5 transition-colors">
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-6 space-y-8">
                    <section>
                        <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-70">Node Identity</div>
                        <Card className="p-5 bg-white/[0.02] border-white/5 backdrop-blur-xl hover:border-white/10 transition-colors">
                            <div className="space-y-4">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-xl bg-primary/10 ring-1 ring-primary/20">
                                        {React.createElement(nodeIcons[selectedNode.data.type] || Box, { className: "w-5 h-5 text-primary" })}
                                    </div>
                                    <div>
                                        <div className="font-bold text-white tracking-tight">{selectedNode.data.label}</div>
                                        <Badge variant="secondary" className="mt-1.5 text-[9px] font-bold uppercase tracking-wider h-5 flex items-center justify-center border-none">{selectedNode.data.type}</Badge>
                                    </div>
                                </div>
                                <div className="h-px bg-white/5" />
                                <div className="grid grid-cols-2 gap-4 text-[11px]">
                                    <div className="space-y-1">
                                        <p className="text-muted-foreground font-semibold uppercase tracking-wider opacity-60">Source File</p>
                                        <p className="text-white font-mono truncate">{selectedNode.data.filename?.split('/').pop() || 'Internal'}</p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-muted-foreground font-semibold uppercase tracking-wider opacity-60">Line Position</p>
                                        <p className="text-white font-mono">{selectedNode.data.lineno || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        </Card>
                    </section>

                    {codeSnippet && (
                        <section className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-70">Context Explorer</div>
                            <Card className="bg-black/40 border-white/5 overflow-hidden rounded-xl">
                                <div className="bg-white/[0.02] px-4 py-2 border-b border-white/5 flex justify-between items-center">
                                    <div className="flex gap-1.5">
                                        <div className="w-2.5 h-2.5 rounded-full bg-rose-500/40" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/40" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/40" />
                                    </div>
                                    <span className="text-[10px] text-white/30 font-mono tracking-tight lowercase truncate ml-4 max-w-[200px]">{selectedNode.data.filename}</span>
                                </div>
                                <div className="p-2 overflow-x-auto">
                                    {codeSnippet.error ? (
                                        <div className="p-6 text-[11px] text-rose-400 font-mono bg-rose-500/5 rounded-lg">{codeSnippet.error}</div>
                                    ) : (
                                        <pre className="p-4 text-[11px] font-mono text-white/70 leading-relaxed">
                                            <code>
                                                {codeSnippet.lines.map((line: any) => (
                                                    <div key={line.number} className={cn("flex gap-6 py-0.5", line.number === selectedNode.data.lineno ? "bg-primary/20 -mx-4 px-4 ring-1 ring-primary/50 text-white font-bold" : "opacity-60")}>
                                                        <span className="w-8 text-white/20 text-right select-none">{line.number}</span>
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
