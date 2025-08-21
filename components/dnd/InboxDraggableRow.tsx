"use client"

import type React from "react"

import { useRef, useState } from "react"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import type { InboxItem } from "@/lib/inbox"
import { cn } from "@/lib/utils"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

type Props = {
  item: InboxItem
  onToggleTriaged: (id: string, triaged: boolean) => void
  onUpdate: (id: string, patch: Partial<InboxItem>) => void
  onArchive?: (id: string) => void
}

export function InboxDraggableRow({ item, onToggleTriaged, onUpdate, onArchive }: Props) {
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } = useSortable({
    id: item.id,
    data: { containerId: "inbox", inboxItem: item },
    disabled: !item.triaged, // only draggable when triaged
  })

  const style = { transform: CSS.Transform.toString(transform), transition } as React.CSSProperties
  const dragProps = item.triaged ? { ...attributes, ...listeners } : {}

  // click vs drag discriminator
  const downXY = useRef<{ x: number; y: number; time: number } | null>(null)
  const DRAG_DISTANCE_PX = 6
  const CLICK_TIME_MS = 300

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState({
    title: item.title,
    estimateMinutes: item.estimateMinutes,
    notes: item.notes ?? "",
  })

  function onPointerDown(e: React.PointerEvent) {
    const t = e.target as HTMLElement
    if (t.closest("[data-no-drag]")) return
    downXY.current = { x: e.clientX, y: e.clientY, time: performance.now() }
  }
  function onPointerUp(e: React.PointerEvent) {
    const start = downXY.current
    downXY.current = null
    if (!start || item.triaged) return // triaged rows prefer drag; clicks for edit happen on controls below
    const dx = e.clientX - start.x
    const dy = e.clientY - start.y
    const dist = Math.hypot(dx, dy)
    const dt = performance.now() - start.time
    const wasClick = dist < DRAG_DISTANCE_PX && dt < CLICK_TIME_MS
    if (wasClick) {
      setEditing(true)
      onUpdate(item.id, { read: true })
    }
  }

  function save() {
    onUpdate(item.id, {
      title: draft.title.trim(),
      estimateMinutes: Number(draft.estimateMinutes) || 30,
      notes: draft.notes,
      read: true,
    })
    setEditing(false)
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...dragProps} // whole row is handle when triaged
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      className={cn(
        "inbox-row rounded-md border border-white/10 bg-white/5 p-2 select-none",
        item.triaged ? "cursor-grab active:cursor-grabbing" : "cursor-default",
        isDragging && "opacity-60",
      )}
    >
      {/* Header row: triage toggle + chips + inline actions */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2" data-no-drag>
          <Switch
            checked={item.triaged}
            onCheckedChange={(b) => onToggleTriaged(item.id, Boolean(b))}
            aria-label="Triaged"
          />
          <Badge variant={item.triaged ? "default" : "secondary"} className="text-[10px]">
            {item.triaged ? "Triaged (drag me)" : "Needs triage"}
          </Badge>
        </div>
        <div className="flex-1 min-w-0">
          <div className="inbox-title truncate">{item.title}</div>
          <div className="inbox-chips text-white/70 text-xs">
            {item.slaTier} · {item.estimateMinutes}m
          </div>
        </div>
        <div className="flex items-center gap-2" data-no-drag>
          {!editing && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setEditing(true)
                onUpdate(item.id, { read: true })
              }}
            >
              Edit
            </Button>
          )}
          {onArchive && (
            <Button size="sm" variant="ghost" onClick={() => onArchive(item.id)}>
              Archive
            </Button>
          )}
        </div>
      </div>

      {/* Inline editor (non-draggable area) */}
      {editing && (
        <div className="mt-3 grid gap-2" data-no-drag>
          <Input
            value={draft.title}
            onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
            placeholder="Task title"
          />
          <div className="flex items-center gap-3">
            <Input
              type="number"
              value={draft.estimateMinutes}
              onChange={(e) => setDraft((d) => ({ ...d, estimateMinutes: Number(e.target.value) }))}
              className="w-24"
              placeholder="Est (m)"
            />
            <span className="text-xs text-white/60">Estimate (minutes)</span>
          </div>
          <Textarea
            value={draft.notes}
            onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
            placeholder="Notes"
            rows={3}
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={save}>
              Save
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setEditing(false)
                setDraft({ title: item.title, estimateMinutes: item.estimateMinutes, notes: item.notes ?? "" })
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
