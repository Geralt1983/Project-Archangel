"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { mockClients } from "@/lib/mock-data"

interface InboxCaptureProps {
  onCapture: (payload: {
    title: string
    clientId?: string
    estimateMinutes?: number
    slaTier?: string
    notes?: string
  }) => void
}

export function InboxCapture({ onCapture }: InboxCaptureProps) {
  const [title, setTitle] = useState("")
  const [clientId, setClientId] = useState<string>()
  const [estimateMinutes, setEstimateMinutes] = useState<number>()
  const [slaTier, setSlaTier] = useState<string>()
  const [notes, setNotes] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    if (!title.trim()) return

    onCapture({
      title: title.trim(),
      clientId,
      estimateMinutes,
      slaTier,
      notes: notes.trim() || undefined,
    })

    // Clear form
    setTitle("")
    setClientId(undefined)
    setEstimateMinutes(undefined)
    setSlaTier(undefined)
    setNotes("")

    // Focus back to textarea
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px"
    }
  }, [title])

  return (
    <div className="space-y-3 p-4 border-b border-white/10">
      <div className="space-y-2">
        <textarea
          ref={textareaRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What needs to be done? (Cmd/Ctrl+Enter to capture)"
          className="w-full bg-transparent placeholder-white/40 text-white/90 outline-none resize-none text-sm min-h-[36px] max-h-[120px]"
          rows={1}
        />

        {title.trim() && (
          <div className="flex gap-2 flex-wrap">
            <Select value={clientId} onValueChange={setClientId}>
              <SelectTrigger className="w-32 h-7 text-xs bg-white/5 border-white/10">
                <SelectValue placeholder="Client" />
              </SelectTrigger>
              <SelectContent>
                {mockClients.map((client) => (
                  <SelectItem key={client.id} value={client.id} className="text-xs">
                    {client.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={slaTier} onValueChange={setSlaTier}>
              <SelectTrigger className="w-24 h-7 text-xs bg-white/5 border-white/10">
                <SelectValue placeholder="SLA" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Low" className="text-xs">
                  Low
                </SelectItem>
                <SelectItem value="Medium" className="text-xs">
                  Medium
                </SelectItem>
                <SelectItem value="High" className="text-xs">
                  High
                </SelectItem>
                <SelectItem value="Critical" className="text-xs">
                  Critical
                </SelectItem>
              </SelectContent>
            </Select>

            <Input
              type="number"
              value={estimateMinutes || ""}
              onChange={(e) => setEstimateMinutes(e.target.value ? Number.parseInt(e.target.value) : undefined)}
              placeholder="30m"
              className="w-16 h-7 text-xs bg-white/5 border-white/10"
              min="5"
              max="480"
              step="15"
            />

            <Button onClick={handleSubmit} size="sm" className="h-7 text-xs bg-brand-500 hover:bg-brand-600">
              Capture
            </Button>
          </div>
        )}

        {title.trim() && (
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional notes..."
            className="w-full bg-transparent placeholder-white/30 text-white/70 outline-none resize-none text-xs"
            rows={2}
          />
        )}
      </div>
    </div>
  )
}
