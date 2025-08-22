"use client"

import { Badge } from "@/components/ui/badge"
import { type ScheduleBlock as ScheduleBlockType, mockClients } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface ScheduleBlockProps {
  block: ScheduleBlockType
  onMove?: (blockId: string, newStart: Date, newEnd: Date) => void
  onResize?: (blockId: string, newStart: Date, newEnd: Date) => void
}

export function ScheduleBlock({ block, onMove, onResize }: ScheduleBlockProps) {
  const client = mockClients.find((c) => c.id === block.clientId)

  const startHour = block.startTime.getHours()
  const startMinute = block.startTime.getMinutes()
  const endHour = block.endTime.getHours()
  const endMinute = block.endTime.getMinutes()

  const duration = (block.endTime.getTime() - block.startTime.getTime()) / (1000 * 60)

  return (
    <div
      className={cn(
        "absolute left-0 right-0 mx-1 rounded border-l-4 bg-card border shadow-sm cursor-move hover:shadow-md transition-shadow",
        client?.color || "border-l-primary",
        block.isFixed && "opacity-75 cursor-not-allowed",
      )}
      style={{
        top: `${((startHour - 9) * 60 + startMinute) * (60 / 60)}px`, // 60px per hour
        height: `${duration * (60 / 60)}px`,
      }}
    >
      <div className="p-2 h-full flex flex-col justify-between">
        <div>
          <div className="font-medium text-xs leading-tight line-clamp-2">{block.title}</div>
          {client && (
            <Badge variant="outline" className={cn("text-xs mt-1", client.color)}>
              {client.name}
            </Badge>
          )}
        </div>

        <div className="text-xs text-muted-foreground">
          {block.startTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -
          {block.endTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  )
}
