"use client"

import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { useNudges } from "./nudges-provider"
import type { Nudge } from "@/lib/nudges"

type Props = {
  open: boolean
  onOpenChange: (b: boolean) => void
  onApproveActions: {
    bump: (taskId: string) => void
    burn: (taskId: string) => void
    reschedule: (taskId: string, minutesDelta: number) => void
    createTask: (title: string) => void
  }
}

export function NudgesPanel({ open, onOpenChange, onApproveActions }: Props) {
  const { nudges, unreadCount, markRead, approve, dismiss } = useNudges()
  const [hoverTimeouts, setHoverTimeouts] = useState<{ [key: string]: NodeJS.Timeout }>({})

  function runAction(n: Nudge) {
    if (!n.action) return
    switch (n.action.type) {
      case "bump":
        if (n.action.payload?.taskId) onApproveActions.bump(n.action.payload.taskId)
        break
      case "burn":
        if (n.action.payload?.taskId) onApproveActions.burn(n.action.payload.taskId)
        break
      case "reschedule":
        if (n.action.payload) onApproveActions.reschedule(n.action.payload.taskId, n.action.payload.minutesDelta)
        break
      case "createTask":
        onApproveActions.createTask(n.action.payload?.title ?? "New task")
        break
    }
  }

  const handleMouseEnter = (nudgeId: string) => {
    const timeout = setTimeout(() => markRead(nudgeId), 500)
    setHoverTimeouts((prev) => ({ ...prev, [nudgeId]: timeout }))
  }

  const handleMouseLeave = (nudgeId: string) => {
    const timeout = hoverTimeouts[nudgeId]
    if (timeout) {
      clearTimeout(timeout)
      setHoverTimeouts((prev) => {
        const { [nudgeId]: _, ...rest } = prev
        return rest
      })
    }
  }

  // Clean up timeouts on unmount
  useEffect(() => {
    return () => {
      Object.values(hoverTimeouts).forEach(clearTimeout)
    }
  }, [hoverTimeouts])

  const visibleNudges = nudges.filter((n) => n.status !== "approved" && n.status !== "dismissed")

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[420px] bg-glass-dark border-white/10">
        <SheetHeader>
          <SheetTitle className="text-white">
            Nudges <span className="text-sm text-white/60">({unreadCount} unread)</span>
          </SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3">
          {visibleNudges.map((n) => (
            <div
              key={n.id}
              className="rounded-lg border border-white/10 p-3 bg-white/5 hover:bg-white/10 transition cursor-pointer"
              onMouseEnter={() => handleMouseEnter(n.id)}
              onMouseLeave={() => handleMouseLeave(n.id)}
              onClick={() => markRead(n.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className={`text-sm font-medium ${n.status === "unread" ? "text-white" : "text-white/80"}`}>
                    {n.title}
                  </div>
                  {n.body && <div className="text-xs text-white/70 mt-1">{n.body}</div>}
                  <div className="text-xs text-white/50 mt-1">{new Date(n.createdAt).toLocaleString()}</div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {n.action && (
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        runAction(n)
                        approve(n.id)
                      }}
                      className="bg-brand-500 hover:bg-brand-600 text-white"
                    >
                      Approve
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={(e) => {
                      e.stopPropagation()
                      dismiss(n.id)
                    }}
                    className="bg-white/10 hover:bg-white/20 text-white/80"
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            </div>
          ))}
          {visibleNudges.length === 0 && <div className="text-sm text-white/60 text-center py-8">No nudges</div>}
        </div>
      </SheetContent>
    </Sheet>
  )
}
