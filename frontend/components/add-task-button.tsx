"use client"

import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import type { Task } from "@/lib/mock-data"

interface AddTaskButtonProps {
  onCreate: (task: Task) => void
}

export function AddTaskButton({ onCreate }: AddTaskButtonProps) {
  const handleClick = () => {
    const newTask: Task = {
      id: `task-${Date.now()}`,
      title: "New task",
      clientId: "cardiology", // Default to first client
      valueScore: 50,
      decayLevel: 0,
      slaTier: "Medium",
      estimateMinutes: 30,
      status: "ready",
      isHot: false,
      isStale: false,
      hasSlaRisk: false,
      autoplanAllowed: true,
      description: "",
      subtasks: [],
      history: [
        {
          timestamp: new Date().toISOString(),
          action: "Created",
          details: "Task created via New Task button",
        },
      ],
    }

    onCreate(newTask)
  }

  return (
    <Button
      onClick={handleClick}
      className="bg-brand-500 hover:bg-brand-600 text-white border-0 shadow-glass"
      size="sm"
    >
      <Plus className="h-4 w-4 mr-2" />
      New Task
    </Button>
  )
}
