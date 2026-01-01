import {
    FileCode,
    Box,
    Braces,
    GitBranch,
    Play,
    Activity,
    Layers,
    Code2,
} from 'lucide-react';

export const nodeIcons: Record<string, any> = {
    file: FileCode,
    class: Box,
    function: Braces,
    logic: GitBranch,
    call_step: Play,
    external: Activity,
    logic_group: Layers,
    data: Code2,
};

export const nodeColors: Record<string, string> = {
    file: 'from-slate-500/10 to-slate-600/10 border-slate-500/30',
    class: 'from-emerald-500/10 to-emerald-600/10 border-emerald-500/30',
    function: 'from-violet-500/10 to-violet-600/10 border-violet-500/30',
    logic: 'from-orange-500/10 to-orange-600/10 border-orange-500/30',
    logic_group: 'from-blue-500/10 to-blue-600/10 border-blue-500/30 border-dashed',
    data: 'from-sky-500/10 to-sky-600/10 border-sky-500/30',
};
