"use client"

import { useState, useRef, useEffect } from "react"
import {
  DndContext,
  type DragEndEvent,
  type DragOverEvent,
  DragOverlay,
  type DragStartEvent,
  useSensor,
  useSensors,
  MouseSensor,
  TouchSensor,
  KeyboardSensor,
  type CollisionDetection,
  pointerWithin,
  rectIntersection,
} from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { Navigation } from "@/components/navigation"
import { TaskCard } from "@/components/task-card"
import { SortableTaskCard } from "@/components/sortable-task-card"
import { DroppableColumn } from "@/components/dnd/DroppableColumn"
import { TaskDrawer } from "@/components/task-drawer"
import { Glass } from "@/components/ui/glass"
import { FadeIn } from "@/components/ui/fade-in"
import { mockTasks, mockClients, type Task } from "@/lib/mock-data"
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts"
import { AddTaskButton } from "@/components/add-task-button"
import { InboxInput } from "@/components/inbox-input"
import { InboxSidebar } from "@/components/inbox-sidebar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useNudges } from "@/components/nudges-provider"
import { NudgesPanel } from "@/components/nudges-panel"
import { loadInbox, saveInbox, addInboxItem, updateInboxItem, removeInboxItems, type InboxItem } from "@/lib/inbox"

const columns = [
  { id: "ready", title: "Ready", wipCap: 5 },
  { id: "doing", title: "Doing", wipCap: 3 },
  { id: "blocked", title: "Blocked", wipCap: null },
  { id: "done", title: "Done", wipCap: null },
] as const

type ColumnId = (typeof columns)[number]["id"]

const columnCollision: CollisionDetection = (args) => {
  const pointerHits = pointerWithin(args)
  const rectHits = rectIntersection(args)
  const hits = pointerHits.length ? pointerHits : rectHits

  // Convert droppableContainers to array and find column hit
  const containers = Array.from(args.droppableContainers.values())
  const columnHit = hits.find((h) => {
    const container = containers.find((c) => c.id === h.id)
    return container?.data?.current?.containerId
  })
  if (columnHit) return [columnHit]

  // Fallback: choose nearest column by pointer X
  const cols = containers.filter((dc) => dc.data?.current?.type === "column")
  if (cols.length === 0) return hits

  const px = args.pointerCoordinates?.x ?? 0
  const best = cols
    .map((dc) => {
      const r = dc.rect.current?.translated
      if (!r) return { dc, score: Number.NEGATIVE_INFINITY }
      const cx = r.left + r.width / 2
      const score = -Math.abs(px - cx) // larger is better (closer)
      return { dc, score }
    })
    .sort((a, b) => b.score - a.score)[0]

  return best?.dc ? [{ id: best.dc.id }] : hits
}

let lastPointer = { x: 0, y: 0 }

function resolveDestColumn(over: any): "ready" | "doing" | "blocked" | "done" | null {
  if (!over) return null
  const cid = over.data?.current?.containerId || over.id
  if (cid === "ready" || cid === "doing" || cid === "blocked" || cid === "done") return cid
  return null
}

function nearestColumnByPointer(): "ready" | "doing" | "blocked" | "done" | null {
  const cols = Array.from(document.querySelectorAll<HTMLElement>("[data-droppable]"))
  if (cols.length === 0) return null
  const px = lastPointer.x,
    py = lastPointer.y
  let best: { el: HTMLElement; score: number; id: any } | null = null
  for (const el of cols) {
    const r = el.getBoundingClientRect()
    const cx = r.left + r.width / 2
    const cy = r.top + r.height / 2
    const score = -Math.hypot(px - cx, py - cy)
    const id = el.getAttribute("data-droppable") as any
    if (!best || score > best.score) best = { el, score, id }
  }
  return best?.id === "ready" || best?.id === "doing" || best?.id === "blocked" || best?.id === "done" ? best!.id : null
}

export default function BoardPage() {
  useKeyboardShortcuts()

  const [tasks, setTasks] = useState<Task[]>(mockTasks)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [activeInboxItem, setActiveInboxItem] = useState<InboxItem | null>(null)
  const [dragSource, setDragSource] = useState<"board" | "inbox" | null>(null)

  const [useInboxSidebar, setUseInboxSidebar] = useState(true)
  const [inboxOpen, setInboxOpen] = useState(false)
  const [nudgesOpen, setNudgesOpen] = useState(false)

  const [inbox, setInbox] = useState<InboxItem[]>([])
  const [columnHighlights, setColumnHighlights] = useState<{ [key: string]: boolean }>({})

  const doingAnchorRef = useRef<HTMLDivElement>(null)
  const columnRefs = useRef<{ [key: string]: HTMLDivElement | null }>({})

  const { nudges, add: addNudge, replaceAll } = useNudges()

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 120, tolerance: 5 } }),
    useSensor(KeyboardSensor),
  )

  useEffect(() => {
    setInbox(loadInbox())
  }, [])

  useEffect(() => {
    saveInbox(inbox)
  }, [inbox])

  // Remove nudges that reference tasks which no longer exist
  useEffect(() => {
    const taskIds = new Set(tasks.map((t) => t.id))
    const filtered = nudges.filter((n) => {
      const id = n.action?.payload && "taskId" in n.action.payload ? n.action.payload.taskId : undefined
      return !id || taskIds.has(id)
    })
    if (filtered.length !== nudges.length) replaceAll(filtered)
  }, [tasks, nudges, replaceAll])

  // Animation helpers
  function nextFrame(): Promise<void> {
    return new Promise((resolve) => requestAnimationFrame(() => resolve()))
  }

  async function animateFly(
    sourceEl: HTMLElement,
    targetEl: HTMLElement,
    opts?: { duration?: number; endScale?: number },
  ): Promise<void> {
    const { duration = 520, endScale = 0.98 } = opts || {}

    // Measure elements
    const sourceRect = sourceEl.getBoundingClientRect()
    const targetRect = targetEl.getBoundingClientRect()

    // Create clone
    const clone = sourceEl.cloneNode(true) as HTMLElement
    clone.classList.add("bumpFlyClone")
    clone.style.cssText = `
      position: fixed;
      left: ${sourceRect.left}px;
      top: ${sourceRect.top}px;
      width: ${sourceRect.width}px;
      height: ${sourceRect.height}px;
      z-index: 9999;
      will-change: transform, opacity;
      transition: transform ${duration}ms cubic-bezier(.22,.61,.36,1), opacity ${duration}ms ease;
      border-radius: 12px;
      overflow: hidden;
      pointer-events: none;
    `

    document.body.appendChild(clone)

    // Fade original
    sourceEl.classList.add("bumpFading")

    // Wait two frames
    await nextFrame()
    await nextFrame()

    // Calculate movement
    const dx = targetRect.left + targetRect.width / 2 - (sourceRect.left + sourceRect.width / 2)
    const dy = targetRect.top + targetRect.height / 2 - (sourceRect.top + sourceRect.height / 2)

    // Start animation
    clone.style.transform = `translate(${dx}px, ${dy}px) scale(${endScale})`
    clone.style.opacity = "0.2"

    // Wait for animation to complete
    return new Promise((resolve) => {
      const handleTransitionEnd = () => {
        clone.removeEventListener("transitionend", handleTransitionEnd)
        if (document.body.contains(clone)) {
          document.body.removeChild(clone)
        }
        sourceEl.classList.remove("bumpFading")
        resolve()
      }
      clone.addEventListener("transitionend", handleTransitionEnd)
    })
  }

  const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task)
    setDrawerOpen(true)
  }

  const canEnterDoing = (task: Task): boolean => {
    const doingColumn = columns.find((col) => col.id === "doing")
    if (!doingColumn?.wipCap) return true

    const currentDoingTasks = getTasksByStatus("doing")
    return currentDoingTasks.length < doingColumn.wipCap
  }

  const handleBump = async (taskId: string, el: HTMLElement) => {
    console.log("[v0] handleBump called with taskId:", taskId)
    const task = tasks.find((t) => t.id === taskId)
    if (!task) {
      console.log("[v0] Task not found for bump")
      return
    }

    try {
      const audio = new Audio("/sounds/boing.mp3")
      audio.currentTime = 0
      await audio.play()
    } catch (e) {
      console.log("[v0] Could not play boing sound:", e)
    }

    // Check WIP cap
    if (!canEnterDoing(task)) {
      console.log("[v0] WIP cap exceeded, denying bump")
      el.classList.add("bumpDeny")
      await delay(400)
      el.classList.remove("bumpDeny")
      return
    }

    console.log("[v0] Starting bump animation sequence")
    // Stage 1: Elevate
    el.classList.add("bumpElevate")
    await delay(140)

    // Stage 2: Wiggle
    el.classList.remove("bumpElevate")
    el.classList.add("bumpWiggle")
    await delay(230)

    // Stage 3: Fly
    el.classList.remove("bumpWiggle")
    if (doingAnchorRef.current) {
      console.log("[v0] Flying to doing column")
      await animateFly(el, doingAnchorRef.current)
    }

    // Stage 4: Commit state change
    console.log("[v0] Committing state change")
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: "doing" } : t)))
  }

  const handleTaskUpdate = (taskId: string, updates: Partial<Task>) => {
    setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, ...updates } : task)))
    // Update selected task if it's the one being edited
    if (selectedTask?.id === taskId) {
      setSelectedTask((prev) => (prev ? { ...prev, ...updates } : null))
    }
  }

  const handleBurn = (taskId: string) => {
    console.log("[v0] handleBurn called with taskId:", taskId)
    setTasks((prev) => prev.filter((task) => task.id !== taskId))
    // Close drawer if the burned task was selected
    if (selectedTask?.id === taskId) {
      setDrawerOpen(false)
      setSelectedTask(null)
    }
  }

  const getTasksByStatus = (status: string) => {
    return tasks.filter((task) => task.status === status)
  }

  function onDragStart(e: DragStartEvent) {
    document.body.classList.add("dnd-dragging")

    const { active } = e

    // Check if dragging from inbox
    const inboxItem = inbox.find((item) => item.id === active.id)
    if (inboxItem) {
      if (!inboxItem.triaged) return // Cancel drag for non-triaged items
      setActiveInboxItem(inboxItem)
      setDragSource("inbox")
      return
    }

    // Otherwise it's a board task
    const task = tasks.find((t) => t.id === active.id)
    setActiveTask(task || null)
    setDragSource("board")
  }

  function onDragOver(e: DragOverEvent) {
    if (e.over && e.activatorEvent && "clientX" in e.activatorEvent) {
      lastPointer = { x: e.activatorEvent.clientX, y: e.activatorEvent.clientY }
    }
  }

  function onDragEnd(e: DragEndEvent) {
    document.body.classList.remove("dnd-dragging")
    const { active, over } = e
    if (!active) return

    const src = active.data.current?.containerId
    const dest = resolveDestColumn(over) || nearestColumnByPointer()

    if (src === "inbox" && dest && (dest === "ready" || dest === "doing" || dest === "blocked")) {
      const i = inbox.find((x) => x.id === String(active.id))
      if (!i || !i.triaged) return
      const t: Task = {
        id: crypto.randomUUID(),
        title: i.title,
        clientId: i.clientId,
        valueScore: 50,
        decayLevel: 0,
        slaTier: i.slaTier,
        estimateMinutes: i.estimateMinutes,
        status: dest,
        isHot: false,
        isStale: false,
        hasSlaRisk: false,
        autoplanAllowed: true,
        description: i.notes ?? "",
        subtasks: [],
        history: [
          {
            timestamp: new Date().toISOString(),
            action: "Created",
            details: `Dragged from inbox to ${dest}`,
          },
        ],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      setTasks((prev) => [t, ...prev])
      setInbox((prev) => prev.filter((x) => x.id !== i.id))
    }

    // else let existing board reordering logic run
    if (src !== "inbox") {
      const { active, over } = e
      setActiveTask(null)
      setActiveInboxItem(null)
      setDragSource(null)
      setColumnHighlights({})

      if (!over) return

      const activeId = active.id as string
      const overId = over.id as string

      // Handle board task reordering (existing logic)
      if (activeId === overId) return

      const activeTask = tasks.find((t) => t.id === activeId)
      if (!activeTask) return

      // Determine final column and position
      let targetColumn: ColumnId = activeTask.status as ColumnId
      let targetIndex = 0

      // Check if dropping over a column header
      if (columns.some((col) => col.id === overId)) {
        targetColumn = overId as ColumnId
        const columnTasks = getTasksByStatus(targetColumn)
        targetIndex = columnTasks.length
      } else {
        // Dropping over another task
        const overTask = tasks.find((t) => t.id === overId)
        if (overTask) {
          targetColumn = overTask.status as ColumnId
          const columnTasks = getTasksByStatus(targetColumn)
          targetIndex = columnTasks.findIndex((t) => t.id === overId)
        }
      }

      // Update task status and reorder within column
      setTasks((prev) => {
        const updatedTasks = prev.map((task) => (task.id === activeId ? { ...task, status: targetColumn } : task))

        // Reorder tasks within the target column
        const columnTasks = updatedTasks.filter((t) => t.status === targetColumn)
        const otherTasks = updatedTasks.filter((t) => t.status !== targetColumn)

        const activeTaskInColumn = columnTasks.find((t) => t.id === activeId)
        const otherColumnTasks = columnTasks.filter((t) => t.id !== activeId)

        if (activeTaskInColumn) {
          otherColumnTasks.splice(targetIndex, 0, activeTaskInColumn)
        }

        return [...otherTasks, ...otherColumnTasks]
      })

      // TODO: Call Archangel.enforceWip() to check WIP limits
      // TODO: Update ClickUp via API
      console.log(`Moved task ${activeId} to ${targetColumn} at position ${targetIndex}`)
    }
  }

  function onDragCancel() {
    document.body.classList.remove("dnd-dragging")
    setActiveTask(null)
    setActiveInboxItem(null)
    setDragSource(null)
  }

  const handleSendToReady = (taskId: string) => {
    setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, status: "ready" } : task)))
  }

  const handleCreateTask = (t: Task) => {
    setTasks((prev) => [t, ...prev]) // prepend into Ready list
    setSelectedTask(t)
    setDrawerOpen(true)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if not focused in input/textarea
      if (document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") {
        return
      }

      if (e.key === "i" && useInboxSidebar) {
        e.preventDefault()
        setInboxOpen(!inboxOpen)
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [inboxOpen, useInboxSidebar])

  const handleCapture = async (payload: {
    title: string
    clientId?: string
    estimateMinutes?: number
    slaTier?: string
    notes?: string
  }) => {
    const rewrittenTitle = await rewriteTitle(payload.title)

    const newItem = addInboxItem({
      title: rewrittenTitle,
      clientId: payload.clientId || mockClients[0].id,
      estimateMinutes: payload.estimateMinutes || 30,
      slaTier: (payload.slaTier as any) || "Medium",
      notes: payload.notes,
      triaged: false, // Default to false
    })

    setInbox((prev) => [newItem, ...prev])
  }

  const pullToBoard = (ids: string[], dest: "ready" | "doing") => {
    const pulled = inbox.filter((i) => ids.includes(i.id))

    // Create real board tasks from inbox items
    const newTasks = pulled.map((item) => ({
      id: crypto.randomUUID(),
      title: item.title,
      clientId: item.clientId,
      valueScore: 50,
      decayLevel: 0,
      slaTier: item.slaTier,
      estimateMinutes: item.estimateMinutes,
      status: dest,
      isHot: false,
      isStale: false,
      hasSlaRisk: false,
      autoplanAllowed: true,
      description: item.notes || "",
      subtasks: [],
      history: [
        {
          timestamp: new Date().toISOString(),
          action: "Created",
          details: `Pulled from inbox to ${dest}`,
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }))

    setTasks((prev) => [...newTasks, ...prev])

    // Remove from inbox
    setInbox((prev) => removeInboxItems(prev, ids))
  }

  const archiveInbox = (ids: string[]) => {
    setInbox((prev) => removeInboxItems(prev, ids))
  }

  const updateInbox = (id: string, patch: Partial<InboxItem>) => {
    setInbox((prev) => updateInboxItem(prev, id, patch))
  }

  const inboxCount = inbox.filter((i) => !i.read).length

  return (
    <div className="min-h-screen">
      <Navigation onOpenNudges={() => setNudgesOpen(true)} />
      <main className="container mx-auto py-6">
        <FadeIn>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-bold tracking-tight text-white">Board</h1>
              {inboxCount > 0 && (
                <Badge variant="outline" className="bg-brand-500/20 text-brand-300 border-brand-400/40">
                  Inbox: {inboxCount}
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Button
                  variant={!useInboxSidebar ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setUseInboxSidebar(false)}
                  className="text-xs"
                >
                  Top Capture
                </Button>
                <Button
                  variant={useInboxSidebar ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setUseInboxSidebar(true)}
                  className="text-xs border-white/20 bg-white/10 text-white/90 hover:bg-white/20"
                >
                  Sidebar
                </Button>
              </div>

              {useInboxSidebar && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setInboxOpen(true)}
                  className="text-xs border-white/20 bg-white/10 text-white/90 hover:bg-white/20"
                >
                  Inbox ({inbox.length}) - Press i
                </Button>
              )}

              <AddTaskButton onCreate={handleCreateTask} />
            </div>
          </div>
        </FadeIn>

        {!useInboxSidebar && (
          <FadeIn delay={0.1}>
            <div className="mb-6">
              <InboxInput onCapture={handleCapture} />
            </div>
          </FadeIn>
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={columnCollision}
          onDragStart={onDragStart}
          onDragOver={onDragOver}
          onDragEnd={onDragEnd}
          onDragCancel={onDragCancel}
        >
          {/* Kanban Board */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {columns.map((column, index) => {
              const columnTasks = getTasksByStatus(column.id)
              const isOverWipCap = column.wipCap && columnTasks.length > column.wipCap
              const isHighlighted = columnHighlights[column.id]

              return (
                <FadeIn key={column.id} delay={index * 0.1}>
                  <Glass>
                    <DroppableColumn id={column.id} className="space-y-3">
                      {/* Column Header */}
                      <div className="p-4 border-b border-white/10">
                        <div className="flex items-center justify-between">
                          <h2 className="font-semibold text-sm text-white/80 uppercase tracking-wide">
                            {column.title}
                          </h2>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-medium ${isOverWipCap ? "text-red-400" : "text-white/70"}`}>
                              {columnTasks.length}
                            </span>
                            {column.wipCap && <span className="text-xs text-white/50">/ {column.wipCap}</span>}
                          </div>
                        </div>
                        {isOverWipCap && <div className="mt-1 text-xs text-red-400">Over WIP limit</div>}
                      </div>

                      <div className="p-4 min-h-[200px]">
                        {/* Doing fly anchor */}
                        {column.id === "doing" && <div id="doing-fly-anchor" ref={doingAnchorRef} className="h-0" />}

                        <SortableContext
                          items={columnTasks.map((task) => task.id)}
                          strategy={verticalListSortingStrategy}
                        >
                          <FadeIn delay={0.2 + index * 0.1}>
                            <div className="space-y-3">
                              {columnTasks.length === 0 ? (
                                <p className="text-sm text-white/50 text-center py-8">No tasks</p>
                              ) : (
                                columnTasks.map((task) => (
                                  <SortableTaskCard
                                    key={task.id}
                                    task={task}
                                    onClick={() => handleTaskClick(task)}
                                    onBump={handleBump}
                                    onBurn={handleBurn}
                                    onSendToReady={handleSendToReady}
                                    compact={task.status === "done"}
                                  />
                                ))
                              )}
                            </div>
                          </FadeIn>
                        </SortableContext>
                      </div>
                    </DroppableColumn>
                  </Glass>
                </FadeIn>
              )
            })}
          </div>

          {/* Inbox sidebar renders inside DndContext so rows are draggable */}
          <InboxSidebar
            open={inboxOpen}
            onOpenChange={setInboxOpen}
            items={inbox}
            onCapture={handleCapture}
            onPull={pullToBoard}
            onArchive={archiveInbox}
            onUpdate={updateInbox}
          />

          <DragOverlay>
            {activeTask ? (
              <div className="rotate-3 scale-105">
                <TaskCard task={activeTask} onClick={() => {}} />
              </div>
            ) : activeInboxItem ? (
              <div className="rotate-3 scale-105">
                <div className="p-3 rounded-lg bg-black/60 backdrop-blur-xl border border-white/20 text-white">
                  <div className="font-medium text-sm">{activeInboxItem.title}</div>
                  <div className="flex gap-1 mt-1">
                    <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/60 text-xs">
                      {mockClients.find((c) => c.id === activeInboxItem.clientId)?.name}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/60 text-xs">
                      {activeInboxItem.slaTier}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/60 text-xs">
                      {activeInboxItem.estimateMinutes}m
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        <NudgesPanel
          open={nudgesOpen}
          onOpenChange={setNudgesOpen}
          onApproveActions={{
            bump: (id) => {
              const el = document.querySelector<HTMLElement>(`[data-id="${id}"]`)
              if (el) handleBump(id, el)
            },
            burn: (id) => handleBurn(id),
            reschedule: (id, minutes) => console.log("reschedule", id, minutes),
            createTask: (title) =>
              handleCreateTask({
                id: crypto.randomUUID(),
                title,
                clientId: "cardiology",
                valueScore: 50,
                decayLevel: 0,
                slaTier: "Medium",
                estimateMinutes: 30,
                status: "ready",
                isHot: false,
                isStale: false,
                hasSlaRisk: false,
                autoplanAllowed: true,
                description: "",
                subtasks: [],
                history: [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
              }),
          }}
        />

        {/* Task Drawer */}
        <TaskDrawer
          task={selectedTask}
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          onTaskUpdate={handleTaskUpdate}
        />
      </main>
    </div>
  )
}

async function rewriteTitle(raw: string): Promise<string> {
  if (!raw || typeof raw !== "string") {
    return "Untitled Task"
  }
  return raw.trim()
}
