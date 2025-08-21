export interface Client {
  id: string
  name: string
  weight: number
  defaultSlaTier: string
  wipClass: string
  color: string
}

export interface Task {
  id: string
  title: string
  clientId: string
  valueScore: number
  decayLevel: number
  slaTier: string
  estimateMinutes: number
  plannedStart?: string
  plannedEnd?: string
  status: "inbox" | "ready" | "doing" | "blocked" | "done"
  isHot: boolean
  isStale: boolean
  hasSlaRisk: boolean
  autoplanAllowed: boolean
  hardDeadline?: string
  description?: string
  subtasks: string[]
  history: Array<{
    timestamp: string
    action: string
    details: string
  }>
}

export const mockClients: Client[] = [
  {
    id: "cardiology",
    name: "Cardiology",
    weight: 0.4,
    defaultSlaTier: "High",
    wipClass: "Critical",
    color: "bg-red-100 text-red-800 border-red-200",
  },
  {
    id: "radiology",
    name: "Radiology",
    weight: 0.35,
    defaultSlaTier: "Medium",
    wipClass: "Standard",
    color: "bg-blue-100 text-blue-800 border-blue-200",
  },
  {
    id: "oncology",
    name: "Oncology",
    weight: 0.25,
    defaultSlaTier: "High",
    wipClass: "Critical",
    color: "bg-green-100 text-green-800 border-green-200",
  },
]

export const mockTasks: Task[] = [
  {
    id: "1",
    title: "Review patient imaging protocols",
    clientId: "cardiology",
    valueScore: 85,
    decayLevel: 2,
    slaTier: "High",
    estimateMinutes: 120,
    plannedStart: "2024-01-15T09:00:00Z",
    plannedEnd: "2024-01-15T11:00:00Z",
    status: "ready",
    isHot: true,
    isStale: false,
    hasSlaRisk: false,
    autoplanAllowed: true,
    hardDeadline: "2024-01-16T17:00:00Z",
    description: "Comprehensive review of current imaging protocols for cardiac patients",
    subtasks: ["Review current protocols", "Identify gaps", "Document recommendations"],
    history: [
      { timestamp: "2024-01-14T10:00:00Z", action: "Created", details: "Task created by system" },
      {
        timestamp: "2024-01-14T14:30:00Z",
        action: "Prioritized",
        details: "Marked as high priority due to SLA requirements",
      },
    ],
  },
  {
    id: "2",
    title: "Update radiology equipment maintenance schedule",
    clientId: "radiology",
    valueScore: 65,
    decayLevel: 1,
    slaTier: "Medium",
    estimateMinutes: 90,
    status: "doing",
    isHot: false,
    isStale: false,
    hasSlaRisk: false,
    autoplanAllowed: true,
    description: "Quarterly maintenance schedule update for all radiology equipment",
    subtasks: ["Audit current equipment", "Schedule maintenance windows", "Update documentation"],
    history: [
      { timestamp: "2024-01-13T08:00:00Z", action: "Created", details: "Task created by system" },
      { timestamp: "2024-01-14T09:00:00Z", action: "Started", details: "Work began on maintenance scheduling" },
    ],
  },
  {
    id: "3",
    title: "Oncology treatment plan optimization",
    clientId: "oncology",
    valueScore: 95,
    decayLevel: 3,
    slaTier: "High",
    estimateMinutes: 180,
    status: "blocked",
    isHot: true,
    isStale: true,
    hasSlaRisk: true,
    autoplanAllowed: false,
    hardDeadline: "2024-01-15T12:00:00Z",
    description: "Optimize treatment plans for better patient outcomes",
    subtasks: ["Analyze current outcomes", "Research best practices", "Implement changes"],
    history: [
      { timestamp: "2024-01-10T10:00:00Z", action: "Created", details: "Task created by system" },
      { timestamp: "2024-01-12T14:00:00Z", action: "Blocked", details: "Waiting for external consultation" },
    ],
  },
  {
    id: "4",
    title: "Complete cardiology audit report",
    clientId: "cardiology",
    valueScore: 75,
    decayLevel: 0,
    slaTier: "Medium",
    estimateMinutes: 60,
    status: "done",
    isHot: false,
    isStale: false,
    hasSlaRisk: false,
    autoplanAllowed: true,
    description: "Final audit report for cardiology department",
    subtasks: ["Compile findings", "Write executive summary", "Submit report"],
    history: [
      { timestamp: "2024-01-08T09:00:00Z", action: "Created", details: "Task created by system" },
      { timestamp: "2024-01-09T10:00:00Z", action: "Started", details: "Began audit compilation" },
      { timestamp: "2024-01-10T16:00:00Z", action: "Completed", details: "Report submitted successfully" },
    ],
  },
]
