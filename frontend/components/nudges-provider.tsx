"use client"

import type React from "react"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { Nudge } from "@/lib/nudges"
import { loadNudges, saveNudges } from "@/lib/nudges"

type Ctx = {
  nudges: Nudge[]
  unreadCount: number
  add: (n: Nudge) => void
  markRead: (id: string) => void
  approve: (id: string) => void
  dismiss: (id: string) => void
  replaceAll: (n: Nudge[]) => void
}

const NudgesCtx = createContext<Ctx | null>(null)

export const useNudges = () => {
  const ctx = useContext(NudgesCtx)
  if (!ctx) throw new Error("useNudges outside provider")
  return ctx
}

export function NudgesProvider({ children }: { children: React.ReactNode }) {
  const [nudges, setNudges] = useState<Nudge[]>([])

  useEffect(() => setNudges(loadNudges()), [])
  useEffect(() => saveNudges(nudges), [nudges])

  const unreadCount = useMemo(() => nudges.filter((n) => n.status === "unread").length, [nudges])

  const api: Ctx = {
    nudges,
    unreadCount,
    add: (n) => setNudges((prev) => [n, ...prev]),
    markRead: (id) =>
      setNudges((prev) =>
        prev.map((n) =>
          n.id === id && n.status === "unread" ? { ...n, status: "read", readAt: new Date().toISOString() } : n,
        ),
      ),
    approve: (id) => setNudges((prev) => prev.map((n) => (n.id === id ? { ...n, status: "approved" } : n))),
    dismiss: (id) => setNudges((prev) => prev.map((n) => (n.id === id ? { ...n, status: "dismissed" } : n))),
    replaceAll: (n) => setNudges(n),
  }

  return <NudgesCtx.Provider value={api}>{children}</NudgesCtx.Provider>
}
