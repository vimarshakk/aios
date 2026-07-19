"use client";

import {
  useCallback, useRef, useState, useEffect, type ReactNode,
} from "react";

interface ResizablePanelProps {
  width: number;
  minWidth?: number;
  maxWidth?: number;
  side: "left" | "right";
  collapsed?: boolean;
  onResize: (w: number) => void;
  children: ReactNode;
}

export function ResizablePanel({
  width,
  minWidth = 200,
  maxWidth = 480,
  side,
  collapsed = false,
  onResize,
  children,
}: ResizablePanelProps) {
  const [dragging, setDragging] = useState(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setDragging(true);
      startX.current = e.clientX;
      startW.current = width;
    },
    [width],
  );

  useEffect(() => {
    if (!dragging) return;

    const onMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startX.current;
      const newW = side === "left"
        ? startW.current + delta
        : startW.current - delta;
      const clamped = Math.min(Math.max(newW, minWidth), maxWidth);
      onResize(clamped);
    };

    const onMouseUp = () => setDragging(false);

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, [dragging, side, minWidth, maxWidth, onResize]);

  if (collapsed) return null;

  return (
    <div
      style={{ width, flexShrink: 0 }}
      className="h-full flex"
    >
      {/* content */}
      <div className="flex-1 h-full overflow-hidden">{children}</div>
      {/* resize handle */}
      <div
        className={`resize-handle ${dragging ? "resizing" : ""}`}
        onMouseDown={onMouseDown}
      />
    </div>
  );
}
