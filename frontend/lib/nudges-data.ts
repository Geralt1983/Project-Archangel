export interface Nudge {
  id: string
  reason: string
  auditLine: string
  priority: "urgent" | "normal" | "low"
  category: "deadline" | "wip" | "sla" | "capacity" | "dependency"
  taskId?: string
  clientId?: string
  createdAt: Date
  isRead: boolean
  status: "pending" | "approved" | "refused"
  metadata?: Record<string, any>
}

export const mockNudges: Nudge[] = [
  {
    id: "nudge-1",
    reason: "Task 'Oncology treatment plan optimization' is approaching hard deadline with SLA risk",
    auditLine: "DEADLINE_RISK: Task oncology-001 due 2024-01-15T12:00:00Z, current status: blocked, SLA tier: High",
    priority: "urgent",
    category: "deadline",
    taskId: "3",
    clientId: "oncology",
    createdAt: new Date("2024-01-14T08:00:00Z"),
    isRead: false,
    status: "pending",
    metadata: {
      deadline: "2024-01-15T12:00:00Z",
      hoursRemaining: 4,
      slaTier: "High",
    },
  },
  {
    id: "nudge-2",
    reason: "Ready column exceeds WIP limit (6/5) - consider moving tasks or increasing capacity",
    auditLine: "WIP_VIOLATION: Column 'ready' has 6 tasks, limit: 5, excess: 1, suggested_action: defer_low_priority",
    priority: "urgent",
    category: "wip",
    createdAt: new Date("2024-01-14T10:30:00Z"),
    isRead: false,
    status: "pending",
    metadata: {
      column: "ready",
      currentCount: 6,
      limit: 5,
      excess: 1,
    },
  },
  {
    id: "nudge-3",
    reason: "Cardiology client capacity utilization is below optimal threshold (45%)",
    auditLine: "CAPACITY_UNDERUTILIZED: Client cardiology at 45% capacity, target: 75%, available_hours: 12.5",
    priority: "normal",
    category: "capacity",
    clientId: "cardiology",
    createdAt: new Date("2024-01-13T14:00:00Z"),
    isRead: true,
    status: "pending",
    metadata: {
      currentUtilization: 45,
      targetUtilization: 75,
      availableHours: 12.5,
    },
  },
  {
    id: "nudge-4",
    reason: "Task dependencies detected - 'Review patient imaging protocols' blocks 2 other tasks",
    auditLine:
      "DEPENDENCY_BOTTLENECK: Task cardiology-001 blocks tasks [cardiology-002, cardiology-003], impact_score: 8.5",
    priority: "normal",
    category: "dependency",
    taskId: "1",
    clientId: "cardiology",
    createdAt: new Date("2024-01-12T16:00:00Z"),
    isRead: true,
    status: "approved",
    metadata: {
      blockedTasks: ["cardiology-002", "cardiology-003"],
      impactScore: 8.5,
    },
  },
  {
    id: "nudge-5",
    reason: "SLA breach imminent for High priority tasks in Radiology",
    auditLine: "SLA_BREACH_WARNING: Client radiology has 2 high-priority tasks at risk, breach_window: 6h",
    priority: "low",
    category: "sla",
    clientId: "radiology",
    createdAt: new Date("2024-01-11T09:00:00Z"),
    isRead: true,
    status: "refused",
    metadata: {
      tasksAtRisk: 2,
      breachWindow: "6h",
      slaTier: "High",
    },
  },
]

export function filterNudgesByTab(nudges: Nudge[], tab: "today" | "unread" | "all"): Nudge[] {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)

  switch (tab) {
    case "today":
      return nudges.filter(
        (nudge) => nudge.createdAt >= today && nudge.createdAt < tomorrow && nudge.status === "pending",
      )
    case "unread":
      return nudges.filter((nudge) => !nudge.isRead && nudge.status === "pending")
    case "all":
      return nudges
    default:
      return nudges
  }
}

export function getUrgentNudges(nudges: Nudge[]): Nudge[] {
  return nudges.filter((nudge) => nudge.priority === "urgent" && nudge.status === "pending").slice(0, 3) // Never show more than 3 urgent nudges
}

export function getPriorityColor(priority: Nudge["priority"]): string {
  switch (priority) {
    case "urgent":
      return "text-red-600 bg-red-50 border-red-200"
    case "normal":
      return "text-yellow-600 bg-yellow-50 border-yellow-200"
    case "low":
      return "text-green-600 bg-green-50 border-green-200"
    default:
      return "text-gray-600 bg-gray-50 border-gray-200"
  }
}

export function getCategoryIcon(category: Nudge["category"]): string {
  switch (category) {
    case "deadline":
      return "⏰"
    case "wip":
      return "📊"
    case "sla":
      return "⚡"
    case "capacity":
      return "📈"
    case "dependency":
      return "🔗"
    default:
      return "📋"
  }
}
