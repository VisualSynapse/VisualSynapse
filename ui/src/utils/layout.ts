 
export const calculateNodePosition = (data: any, allNodes: any[]) => {
    const level = data.level || 0;
    const spacingX = 350;
    const spacingY = 200;

     
    let peers = allNodes.filter((n: any) => (n.data.level || 0) === level);

     
    peers.sort((a: any, b: any) => {
        const lineA = a.data.metadata?.lineno || a.data.lineno || 0;
        const lineB = b.data.metadata?.lineno || b.data.lineno || 0;
        return lineA - lineB;
    });

     
    const myIndex = peers.findIndex((n: any) => n.data.id === data.id);
    const safeIndex = myIndex === -1 ? 0 : myIndex;

     
    let y = level * spacingY;

     
    let x = safeIndex * spacingX;

     
    x += level * 20;

    return { x, y };
};
