"use client"

import { Progress } from "@/components/ui/progress"
import { Clock } from "lucide-react"
import { calculateCapacity, type ScheduleBlock, type CalendarEvent } from "@/lib/schedule-data"

interface CapacityBarProps {
  today: Date
  weekDays: Date[]
  blocks: ScheduleBlock[]
  events: CalendarEvent[]
}

export function CapacityBar({ today, weekDays, blocks, events }: CapacityBarProps) {
  const todayCapacity = calculateCapacity(today, blocks, events)

  // Calculate week capacity
  const weekCapacity = weekDays.reduce(
    (acc, day) => {
      const dayCapacity = calculateCapacity(day, blocks, events)
      return {
        totalMinutes: acc.totalMinutes + dayCapacity.totalMinutes,
        scheduledMinutes: acc.scheduledMinutes + dayCapacity.scheduledMinutes,
        freeMinutes: acc.freeMinutes + dayCapacity.freeMinutes,
      }
    },
    { totalMinutes: 0, scheduledMinutes: 0, freeMinutes: 0 },
  )

  const weekPercentage = Math.min(100, (weekCapacity.scheduledMinutes / weekCapacity.totalMinutes) * 100)

  const formatHours = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }

  return (
    <div className="bg-card rounded-lg border p-4 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-semibold">Capacity Overview</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Today */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Today</span>
            <span className="text-muted-foreground">{formatHours(todayCapacity.freeMinutes)} free</span>
          </div>
          <Progress value={todayCapacity.percentage} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatHours(todayCapacity.scheduledMinutes)} scheduled</span>
            <span>{Math.round(todayCapacity.percentage)}% utilized</span>
          </div>
        </div>

        {/* This Week */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">This Week</span>
            <span className="text-muted-foreground">{formatHours(weekCapacity.freeMinutes)} free</span>
          </div>
          <Progress value={weekPercentage} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatHours(weekCapacity.scheduledMinutes)} scheduled</span>
            <span>{Math.round(weekPercentage)}% utilized</span>
          </div>
        </div>
      </div>
    </div>
  )
}
