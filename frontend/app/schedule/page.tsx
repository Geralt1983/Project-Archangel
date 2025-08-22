"use client"

import { useState } from "react"
import { Navigation } from "@/components/navigation"
import { CapacityBar } from "@/components/capacity-bar"
import { ScheduleBlock } from "@/components/schedule-block"
import { CalendarEvent } from "@/components/calendar-event"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react"
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts"
import {
  getWeekDays,
  workingHours,
  mockScheduleBlocks,
  mockCalendarEvents,
  type ScheduleBlock as ScheduleBlockType,
} from "@/lib/schedule-data"

export default function SchedulePage() {
  useKeyboardShortcuts()

  const [currentWeek, setCurrentWeek] = useState(new Date())
  const [showCalendarEvents, setShowCalendarEvents] = useState(false)
  const [scheduleBlocks, setScheduleBlocks] = useState<ScheduleBlockType[]>(mockScheduleBlocks)

  const weekDays = getWeekDays(currentWeek)
  const today = new Date()

  const navigateWeek = (direction: "prev" | "next") => {
    const newWeek = new Date(currentWeek)
    newWeek.setDate(currentWeek.getDate() + (direction === "next" ? 7 : -7))
    setCurrentWeek(newWeek)
  }

  const handleBlockMove = (blockId: string, newStart: Date, newEnd: Date) => {
    setScheduleBlocks((prev) =>
      prev.map((block) => (block.id === blockId ? { ...block, startTime: newStart, endTime: newEnd } : block)),
    )
  }

  const getHourSlots = () => {
    const slots = []
    for (let hour = workingHours.start; hour < workingHours.end; hour++) {
      slots.push(hour)
    }
    return slots
  }

  const isToday = (date: Date) => {
    return date.toDateString() === today.toDateString()
  }

  const getBlocksForDay = (date: Date) => {
    const dayStart = new Date(date)
    dayStart.setHours(0, 0, 0, 0)
    const dayEnd = new Date(date)
    dayEnd.setHours(23, 59, 59, 999)

    return scheduleBlocks.filter((block) => block.startTime >= dayStart && block.startTime <= dayEnd)
  }

  const getEventsForDay = (date: Date) => {
    const dayStart = new Date(date)
    dayStart.setHours(0, 0, 0, 0)
    const dayEnd = new Date(date)
    dayEnd.setHours(23, 59, 59, 999)

    return mockCalendarEvents.filter((event) => event.startTime >= dayStart && event.startTime <= dayEnd)
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="container mx-auto py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Schedule</h1>

          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Switch id="calendar-events" checked={showCalendarEvents} onCheckedChange={setShowCalendarEvents} />
              <Label htmlFor="calendar-events" className="text-sm">
                Show Calendar Events
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => navigateWeek("prev")}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentWeek(new Date())}>
                <Calendar className="h-4 w-4 mr-1" />
                Today
              </Button>
              <Button variant="outline" size="sm" onClick={() => navigateWeek("next")}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Capacity Bar */}
        <CapacityBar today={today} weekDays={weekDays} blocks={scheduleBlocks} events={mockCalendarEvents} />

        {/* Week Grid */}
        <div className="bg-card rounded-lg border overflow-hidden">
          {/* Week Header */}
          <div className="grid grid-cols-8 border-b bg-muted/50">
            <div className="p-3 text-sm font-medium text-muted-foreground">Time</div>
            {weekDays.map((day, index) => (
              <div
                key={index}
                className={`p-3 text-center border-l ${isToday(day) ? "bg-primary/10 font-semibold" : ""}`}
              >
                <div className="text-sm font-medium">{day.toLocaleDateString("en-US", { weekday: "short" })}</div>
                <div className={`text-xs ${isToday(day) ? "text-primary" : "text-muted-foreground"}`}>
                  {day.getDate()}
                </div>
              </div>
            ))}
          </div>

          {/* Time Grid */}
          <div className="grid grid-cols-8">
            {/* Time Column */}
            <div className="border-r">
              {getHourSlots().map((hour) => (
                <div key={hour} className="h-[60px] border-b p-2 text-xs text-muted-foreground">
                  {hour.toString().padStart(2, "0")}:00
                </div>
              ))}
            </div>

            {/* Day Columns */}
            {weekDays.map((day, dayIndex) => (
              <div key={dayIndex} className="border-r relative">
                {/* Hour slots */}
                {getHourSlots().map((hour) => (
                  <div
                    key={hour}
                    className={`h-[60px] border-b ${
                      isToday(day) ? "bg-primary/5" : ""
                    } hover:bg-muted/50 transition-colors`}
                  />
                ))}

                {/* Schedule blocks for this day */}
                {getBlocksForDay(day).map((block) => (
                  <ScheduleBlock key={block.id} block={block} onMove={handleBlockMove} />
                ))}

                {/* Calendar events for this day (if enabled) */}
                {showCalendarEvents &&
                  getEventsForDay(day).map((event) => <CalendarEvent key={event.id} event={event} />)}
              </div>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 flex items-center gap-6 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-card border border-primary/20 rounded"></div>
            <span>Scheduled Tasks</span>
          </div>
          {showCalendarEvents && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-100 border-l-2 border-l-blue-500 rounded"></div>
                <span>Meetings</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-100 border-l-2 border-l-green-500 rounded"></div>
                <span>Focus Blocks</span>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
