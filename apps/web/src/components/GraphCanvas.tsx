"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { GraphResponse } from "@/types";

// react-force-graph-2d relies on the canvas/DOM, so it must only load client-side.
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-ink-400">
      Initializing graph…
    </div>
  ),
});

interface FGNode {
  id: string;
  title: string;
  tags: string[];
  in_degree: number;
  out_degree: number;
  val: number;
}

interface FGLink {
  source: string;
  target: string;
}

export default function GraphCanvas({
  graph,
  onSelect,
  selectedId,
}: {
  graph: GraphResponse;
  onSelect: (id: string) => void;
  selectedId: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 560 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () =>
      setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    const nodes: FGNode[] = graph.nodes.map((n) => ({
      id: n.id,
      title: n.title,
      tags: n.tags,
      in_degree: n.in_degree,
      out_degree: n.out_degree,
      val: 1 + n.in_degree * 1.4,
    }));
    const ids = new Set(nodes.map((n) => n.id));
    // Keep only edges whose endpoints both exist as nodes.
    const links: FGLink[] = graph.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ source: e.source, target: e.target }));
    return { nodes, links };
  }, [graph]);

  return (
    <div
      ref={containerRef}
      data-testid="graph-canvas"
      className="h-[560px] w-full overflow-hidden rounded-xl border border-ink-200 bg-ink-950"
    >
      <ForceGraph2D
        width={size.width}
        height={size.height}
        graphData={data as any}
        backgroundColor="#020617"
        nodeRelSize={5}
        linkColor={() => "rgba(148,163,184,0.25)"}
        linkDirectionalParticles={1}
        linkDirectionalParticleWidth={1.6}
        linkDirectionalParticleColor={() => "rgba(99,102,241,0.7)"}
        cooldownTicks={120}
        onNodeClick={(node: any) => onSelect(node.id as string)}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const n = node as FGNode & { x: number; y: number };
          const isSelected = selectedId === n.id;
          const radius = Math.max(3, Math.sqrt(n.val) * 2.6);
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = isSelected ? "#a5b4fc" : "#6366f1";
          ctx.fill();
          if (isSelected) {
            ctx.lineWidth = 2 / globalScale;
            ctx.strokeStyle = "#e0e7ff";
            ctx.stroke();
          }
          const label = n.title;
          const fontSize = Math.max(10, 12 / globalScale);
          ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = "rgba(226,232,240,0.85)";
          if (globalScale > 0.7 || isSelected) {
            ctx.fillText(label, n.x, n.y + radius + 1.5);
          }
        }}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          const n = node as FGNode & { x: number; y: number };
          const radius = Math.max(6, Math.sqrt(n.val) * 3);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
      />
    </div>
  );
}
