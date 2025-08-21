"use client"

import { useState, useEffect } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { InboxCapture } from "./inbox-capture"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { useDndContext } from "@dnd-kit/core"
import { mockClients } from "@/lib/mock-data"
import type { InboxItem } from "@/lib/inbox"
import { InboxDraggableRow } from "@/components/dnd/InboxDraggableRow"

interface InboxSidebarProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  items: InboxItem[]
  onCapture: (payload: {
    title: string
    clientId?: string
    estimateMinutes?: number
    slaTier?: string
    notes?: string
  }) => void
  onPull: (ids: string[], dest: "ready" | "doing") => void
  onArchive: (ids: string[]) => void
  onUpdate: (id: string, patch: Partial<InboxItem>) => void
}

export function InboxSidebar({ open, onOpenChange, items, onCapture, onPull, onArchive, onUpdate }: InboxSidebarProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<InboxItem>>({})
  const [hoverTimeouts, setHoverTimeouts] = useState<{ [key: string]: NodeJS.Timeout }>({})
  const { active } = useDndContext()

  const selectedItems = items.filter((item) => selectedIds.includes(item.id))
  const unreadCount = items.filter((item) => !item.read).length
  const triagedItems = items.filter((item) => item.triaged)
  const allIds = items.map((i) => i.id)

  const handleItemHover = (itemId: string) => {
    if (hoverTimeouts[itemId]) return

    const timeout = setTimeout(() => {
      onUpdate(itemId, { read: true })
      setHoverTimeouts((prev) => {
        const { [itemId]: _, ...rest } = prev
        return rest
      })
    }, 500)

    setHoverTimeouts((prev) => ({ ...prev, [itemId]: timeout }))
  }

  const handleItemLeave = (itemId: string) => {
    if (hoverTimeouts[itemId]) {
      clearTimeout(hoverTimeouts[itemId])
      setHoverTimeouts((prev) => {
        const { [itemId]: _, ...rest } = prev
        return rest
      })
    }
  }

  useEffect(() => {
    return () => {
      Object.values(hoverTimeouts).forEach(clearTimeout)
    }
  }, [hoverTimeouts])

  const handleSelectItem = (itemId: string, checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => [...prev, itemId])
    } else {
      setSelectedIds((prev) => prev.filter((id) => id !== itemId))
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(items.map((item) => item.id))
    } else {
      setSelectedIds([])
    }
  }

  const handleEditItem = (item: InboxItem) => {
    setEditingId(item.id)
    setEditForm(item)
    onUpdate(item.id, { read: true })
  }

  const handleSaveEdit = () => {
    if (editingId && editForm) {
      onUpdate(editingId, editForm)
      setEditingId(null)
      setEditForm({})
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditForm({})
  }

  const handleItemAction = (itemId: string, action: "pull-ready" | "pull-doing" | "archive") => {
    switch (action) {
      case "pull-ready":
        onPull([itemId], "ready")
        break
      case "pull-doing":
        onPull([itemId], "doing")
        break
      case "archive":
        onArchive([itemId])
        break
    }
  }

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") {
        return
      }

      switch (e.key) {
        case "Enter":
          if (selectedIds.length === 1) {
            const item = items.find((i) => i.id === selectedIds[0])
            if (item) handleEditItem(item)
          }
          break
        case "p":
        case "P":
          if (selectedIds.length > 0) {
            onPull(selectedIds, "ready")
            setSelectedIds([])
          }
          break
        case "d":
        case "D":
          if (selectedIds.length > 0) {
            onPull(selectedIds, "doing")
            setSelectedIds([])
          }
          break
        case "Delete":
        case "Backspace":
          if (selectedIds.length > 0) {
            onArchive(selectedIds)
            setSelectedIds([])
          }
          break
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [open, selectedIds, items, onPull, onArchive])

  const getClientName = (clientId: string) => {
    return mockClients.find((c) => c.id === clientId)?.name || clientId
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent side="right" className="w-96 bg-black/40 backdrop-blur-xl border-white/10 flex flex-col">
        <SheetHeader className="space-y-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-white">Inbox</SheetTitle>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-white/10 text-white/90 border-white/20">
                {unreadCount} unread
              </Badge>
              <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-400/40">
                {triagedItems.length} ready
              </Badge>
            </div>
          </div>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10">
              <span className="text-xs text-white/70">{selectedIds.length} selected</span>
              <div className="flex gap-1 ml-auto">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    onPull(selectedIds, "ready")
                    setSelectedIds([])
                  }}
                  className="h-6 px-2 text-xs text-white/80 hover:bg-white/10"
                >
                  Pull to Ready
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    onPull(selectedIds, "doing")
                    setSelectedIds([])
                  }}
                  className="h-6 px-2 text-xs text-white/80 hover:bg-white/10"
                >
                  Pull to Doing
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    onArchive(selectedIds)
                    setSelectedIds([])
                  }}
                  className="h-6 px-2 text-xs text-white/80 hover:bg-white/10"
                >
                  Archive
                </Button>
              </div>
            </div>
          )}
        </SheetHeader>

        <div className="flex-shrink-0">
          <InboxCapture onCapture={onCapture} />
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 mt-4">
          {items.length === 0 ? (
            <div className="text-center py-8 text-white/50 text-sm">
              No items in inbox
              <br />
              <span className="text-xs">Capture something to get started</span>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 px-2 py-1">
                <Checkbox
                  checked={selectedIds.length === items.length}
                  onCheckedChange={handleSelectAll}
                  className="border-white/20"
                />
                <span className="text-xs text-white/60">Select all ({items.length})</span>
              </div>

              <SortableContext items={allIds} strategy={verticalListSortingStrategy}>
                {items.map((item) => (
                  <InboxDraggableRow
                    key={item.id}
                    item={item}
                    onToggleTriaged={(id, b) => onUpdate(id, { triaged: b })}
                    onUpdate={onUpdate}
                    onArchive={(id) => onArchive([id])}
                  />
                ))}
              </SortableContext>
            </>
          )}
        </div>

        <div className="flex-shrink-0 mt-4 p-2 rounded-lg bg-white/5 border border-white/10">
          <div className="text-xs text-white/50 space-y-1">
            <div>
              <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">Enter</kbd> Edit selected
            </div>
            <div>
              <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">P</kbd> Pull to Ready •{" "}
              <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">D</kbd> Pull to Doing •{" "}
              <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">Del</kbd> Archive
            </div>
            <div className="text-green-300">Drag triaged items to board columns</div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
