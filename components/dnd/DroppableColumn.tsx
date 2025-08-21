"use client"
import { useDroppable } from "@dnd-kit/core"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function DroppableColumn({
  id,
  className,
  children,
}: { id: "ready" | "doing" | "blocked" | "done"; className?: string; children: ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({
    id,
    data: { containerId: id, type: "column" },
  })
  return (
    <div
      ref={setNodeRef}
      data-droppable={id}
      className={cn(
        // This element must cover the whole column area (header + list)
        "min-h-[60vh] h-full",
        isOver && "drop-target drop-target-accept",
        className,
      )}
    >
      {children}
    </div>
  )
}
