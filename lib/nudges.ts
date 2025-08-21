export type NudgeAction =
  | { type: "bump"; payload?: { taskId: string } }
  | { type: "burn"; payload?: { taskId: string } }
  | { type: "reschedule"; payload: { taskId: string; minutesDelta: number } }
  | { type: "createTask"; payload: { title: string } }

export type NudgeStatus = "unread" | "read" | "approved" | "dismissed"

export interface Nudge {
  id: string
  title: string
  body?: string
  createdAt: string
  readAt?: string
  status: NudgeStatus
  action?: NudgeAction
}

const KEY = "archangel_nudges_v1"

export function loadNudges(): Nudge[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Nudge[]) : []
  } catch {
    return []
  }
}

export function saveNudges(n: Nudge[]) {
  if (typeof window === "undefined") return
  localStorage.setItem(KEY, JSON.stringify(n))
}
