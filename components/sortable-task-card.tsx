"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { TaskCard } from "./task-card"
import type { Task } from "@/lib/mock-data"

interface SortableTaskCardProps {
  task: Task
  onClick: () => void
  onBump?: (taskId: string, cardEl: HTMLElement) => void
  onBurn?: (taskId: string) => void
  onSendToReady?: (taskId: string, cardEl: HTMLElement) => void
  compact?: boolean
}

export function SortableTaskCard({
  task,
  onClick,
  onBump,
  onBurn,
  onSendToReady,
  compact = false,
}: SortableTaskCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: {
      type: "task",
      task,
    },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div ref={setNodeRef} style={style} className={isDragging ? "opacity-50" : ""} {...attributes} {...listeners}>
      <TaskCard
        task={task}
        onClick={onClick}
        onBump={onBump}
        onBurn={onBurn}
        onSendToReady={onSendToReady}
        compact={compact}
      />
    </div>
  )
}
