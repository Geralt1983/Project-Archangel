export type InboxItem = {
  id: string
  title: string
  clientId: string
  estimateMinutes: number
  slaTier: "Low" | "Medium" | "High" | "Critical"
  notes?: string
  createdAt: string
  updatedAt: string
  read: boolean
  selected?: boolean
  triaged: boolean // <-- NEW
}

const STORAGE_KEY = "archangel_inbox_v1"

export function loadInbox(): InboxItem[] {
  if (typeof window === "undefined") return []
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

export function saveInbox(items: InboxItem[]): void {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch (error) {
    console.error("Failed to save inbox:", error)
  }
}

export function addInboxItem(partial: Partial<InboxItem> & { title: string }): InboxItem {
  const item: InboxItem = {
    id: crypto.randomUUID(),
    title: partial.title,
    clientId: partial.clientId || "cardiology",
    estimateMinutes: partial.estimateMinutes || 30,
    slaTier: partial.slaTier || "Medium",
    notes: partial.notes || "",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    read: false,
    triaged: false, // <-- NEW: default to false
    ...partial,
  }
  return item
}

export function updateInboxItem(items: InboxItem[], id: string, patch: Partial<InboxItem>): InboxItem[] {
  return items.map((item) => (item.id === id ? { ...item, ...patch, updatedAt: new Date().toISOString() } : item))
}

export function removeInboxItems(items: InboxItem[], ids: string[]): InboxItem[] {
  return items.filter((item) => !ids.includes(item.id))
}
