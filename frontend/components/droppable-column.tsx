import { useDroppable } from "@dnd-kit/core"
import type { ReactNode } from "react"

interface DroppableColumnProps {
  id: string
  children: ReactNode
  className?: string
}

export function DroppableColumn({ id, children, className = "" }: DroppableColumnProps) {
  const { isOver, setNodeRef } = useDroppable({
    id,
  })

  return (
    <div ref={setNodeRef} className={`${className} ${isOver ? "bg-muted/50" : ""} transition-colors`}>
      {children}
    </div>
  )
}
