export interface NodeData {
    label: string;
    type: string;
    parentId?: string;
    expanded?: boolean;
    filename?: string;
    lineno?: number;
    children?: string[];
    metadata?: Record<string, any>;
    isMatch?: boolean;
    level?: number;
    id?: string;
    position?: { x: number; y: number };
    highlightColor?: string;
    [key: string]: unknown;
}

export interface CodeSnippet {
    file: string;
    lines: { number: number; content: string }[];
    number: number;
    content: string;
    error?: string;
}
