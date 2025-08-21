export interface ScheduleBlock {
  id: string
  taskId: string
  title: string
  clientId: string
  startTime: Date
  endTime: Date
  estimateMinutes: number
  isFixed: boolean
}

export interface CalendarEvent {
  id: string
  title: string
  startTime: Date
  endTime: Date
  type: "meeting" | "focus" | "break"
}

export interface WorkingHours {
  start: number // hour in 24h format
  end: number // hour in 24h format
}

export const workingHours: WorkingHours = {
  start: 9,
  end: 17,
}

// Mock scheduled blocks from tasks with plannedStart/plannedEnd
export const mockScheduleBlocks: ScheduleBlock[] = [
  {
    id: "block-1",
    taskId: "1",
    title: "Review patient imaging protocols",
    clientId: "cardiology",
    startTime: new Date("2024-01-15T09:00:00Z"),
    endTime: new Date("2024-01-15T11:00:00Z"),
    estimateMinutes: 120,
    isFixed: false,
  },
  {
    id: "block-2",
    taskId: "2",
    title: "Update radiology equipment maintenance schedule",
    clientId: "radiology",
    startTime: new Date("2024-01-15T14:00:00Z"),
    endTime: new Date("2024-01-15T15:30:00Z"),
    estimateMinutes: 90,
    isFixed: false,
  },
]

// Mock Google Calendar events
export const mockCalendarEvents: CalendarEvent[] = [
  {
    id: "cal-1",
    title: "Team Standup",
    startTime: new Date("2024-01-15T10:00:00Z"),
    endTime: new Date("2024-01-15T10:30:00Z"),
    type: "meeting",
  },
  {
    id: "cal-2",
    title: "Client Review Meeting",
    startTime: new Date("2024-01-16T15:00:00Z"),
    endTime: new Date("2024-01-16T16:00:00Z"),
    type: "meeting",
  },
  {
    id: "cal-3",
    title: "Focus Block",
    startTime: new Date("2024-01-17T09:00:00Z"),
    endTime: new Date("2024-01-17T11:00:00Z"),
    type: "focus",
  },
]

export function getWeekDays(startDate: Date): Date[] {
  const days: Date[] = []
  const start = new Date(startDate)

  // Get Monday of the week
  const dayOfWeek = start.getDay()
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  start.setDate(start.getDate() + mondayOffset)

  for (let i = 0; i < 7; i++) {
    const day = new Date(start)
    day.setDate(start.getDate() + i)
    days.push(day)
  }

  return days
}

export function calculateCapacity(
  date: Date,
  blocks: ScheduleBlock[],
  events: CalendarEvent[],
): {
  totalMinutes: number
  scheduledMinutes: number
  freeMinutes: number
  percentage: number
} {
  const totalMinutes = (workingHours.end - workingHours.start) * 60

  const dayStart = new Date(date)
  dayStart.setHours(0, 0, 0, 0)
  const dayEnd = new Date(date)
  dayEnd.setHours(23, 59, 59, 999)

  const dayBlocks = blocks.filter((block) => block.startTime >= dayStart && block.startTime <= dayEnd)

  const dayEvents = events.filter((event) => event.startTime >= dayStart && event.startTime <= dayEnd)

  const scheduledMinutes =
    dayBlocks.reduce((total, block) => total + (block.endTime.getTime() - block.startTime.getTime()) / (1000 * 60), 0) +
    dayEvents.reduce((total, event) => total + (event.endTime.getTime() - event.startTime.getTime()) / (1000 * 60), 0)

  const freeMinutes = Math.max(0, totalMinutes - scheduledMinutes)
  const percentage = Math.min(100, (scheduledMinutes / totalMinutes) * 100)

  return {
    totalMinutes,
    scheduledMinutes,
    freeMinutes,
    percentage,
  }
}
