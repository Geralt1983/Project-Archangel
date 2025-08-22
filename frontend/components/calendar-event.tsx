"use client"

import type { CalendarEvent as ScheduleEvent } from "@/lib/schedule-data"
import { cn } from "@/lib/utils"

interface CalendarEventProps {
  event: ScheduleEvent
}

export function CalendarEvent({ event }: CalendarEventProps) {
  const startHour = event.startTime.getHours()
  const startMinute = event.startTime.getMinutes()
  const duration = (event.endTime.getTime() - event.startTime.getTime()) / (1000 * 60)

  const getEventColor = (type: ScheduleEvent["type"]) => {
    switch (type) {
      case "meeting":
        return "bg-blue-100 border-l-blue-500 text-blue-800"
      case "focus":
        return "bg-green-100 border-l-green-500 text-green-800"
      case "break":
        return "bg-yellow-100 border-l-yellow-500 text-yellow-800"
      default:
        return "bg-gray-100 border-l-gray-500 text-gray-800"
    }
  }

  return (
    <div
      className={cn(
        "absolute left-0 right-0 mx-1 rounded border-l-4 opacity-60 pointer-events-none",
        getEventColor(event.type),
      )}
      style={{
        top: `${((startHour - 9) * 60 + startMinute) * (60 / 60)}px`,
        height: `${duration * (60 / 60)}px`,
      }}
    >
      <div className="p-2 h-full">
        <div className="font-medium text-xs leading-tight">{event.title}</div>
        <div className="text-xs opacity-75">
          {event.startTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -
          {event.endTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  )
}
