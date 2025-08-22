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

  const filteredListeners = Object.keys(listeners || {}).reduce((acc, key) => {
    const originalHandler = (listeners as any)[key]
    acc[key] = (e: any) => {
      // Check if the event target or any parent is a button or has data-no-drag
      const target = e.target as HTMLElement
      const isButton = target.closest("button") || target.tagName === "BUTTON"
      const hasNoDrag = target.closest("[data-no-drag]") || target.hasAttribute("data-no-drag")
      
      if (isButton || hasNoDrag) {
        console.log("[v0] Preventing drag on button/no-drag element")
        // Don't prevent default for buttons - let them handle clicks normally
        if (!isButton) {
          e.preventDefault()
        }
        e.stopPropagation()
        return
      }
      originalHandler?.(e)
    }
    return acc
  }, {} as any)

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? "opacity-50" : ""}
      {...attributes}
      {...filteredListeners}
    >
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
