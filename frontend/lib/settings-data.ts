export interface ClientSettings {
  id: string
  name: string
  weight: number
  defaultSlaTier: "Low" | "Medium" | "High"
  wipClass: "Standard" | "Critical" | "Flexible"
}

export interface WipCapSettings {
  status: string
  cap: number | null
  enabled: boolean
}

export interface ThresholdSettings {
  hotTaskHours: number
  staleTaskDays: number
  slaWarningHours: number
  capacityThresholdPercent: number
}

export interface SchedulingSettings {
  workStartHour: number
  workEndHour: number
  meetingBufferMinutes: number
  focusBlockMinutes: number
  hardDeadlineHandling: "strict" | "flexible" | "advisory"
  breakDurationMinutes: number
  maxConsecutiveHours: number
}

export interface ApiSettings {
  clickupToken: string
  archangelBaseUrl: string
  archangelToken: string
  googleCalendarUrl: string
}

export interface AppSettings {
  clients: ClientSettings[]
  wipCaps: WipCapSettings[]
  thresholds: ThresholdSettings
  scheduling: SchedulingSettings
  apiKeys: ApiSettings
}

export const defaultSettings: AppSettings = {
  clients: [
    {
      id: "cardiology",
      name: "Cardiology",
      weight: 0.4,
      defaultSlaTier: "High",
      wipClass: "Critical",
    },
    {
      id: "radiology",
      name: "Radiology",
      weight: 0.35,
      defaultSlaTier: "Medium",
      wipClass: "Standard",
    },
    {
      id: "oncology",
      name: "Oncology",
      weight: 0.25,
      defaultSlaTier: "High",
      wipClass: "Critical",
    },
  ],
  wipCaps: [
    { status: "ready", cap: 5, enabled: true },
    { status: "doing", cap: 3, enabled: true },
    { status: "blocked", cap: null, enabled: false },
    { status: "done", cap: null, enabled: false },
  ],
  thresholds: {
    hotTaskHours: 4,
    staleTaskDays: 3,
    slaWarningHours: 8,
    capacityThresholdPercent: 75,
  },
  scheduling: {
    workStartHour: 9,
    workEndHour: 17,
    meetingBufferMinutes: 15,
    focusBlockMinutes: 120,
    hardDeadlineHandling: "strict",
    breakDurationMinutes: 15,
    maxConsecutiveHours: 4,
  },
  apiKeys: {
    clickupToken: "",
    archangelBaseUrl: "https://api.archangel.example.com",
    archangelToken: "",
    googleCalendarUrl: "",
  },
}
