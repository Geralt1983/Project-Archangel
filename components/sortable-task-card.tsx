"use client"

import type React from "react"

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

  const cardListeners = {
    ...listeners,
    onPointerDown: (e: React.PointerEvent) => {
      // Don't start drag if clicking on buttons or interactive elements
      const target = e.target as HTMLElement
      if (target.closest("button") || target.closest("[data-no-drag]")) {
        return
      }
      listeners?.onPointerDown?.(e as any)
    },
  }

  return (
    <div ref={setNodeRef} style={style} className={isDragging ? "opacity-50" : ""} {...attributes} {...cardListeners}>
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
