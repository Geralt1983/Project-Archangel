"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { mockClients } from "@/lib/mock-data"
import { Plus } from "lucide-react"

interface InboxInputProps {
  onCapture: (title: string, opts: { clientId?: string; estimateMinutes?: number; slaTier?: string }) => void
}

export function InboxInput({ onCapture }: InboxInputProps) {
  const [title, setTitle] = useState("")
  const [clientId, setClientId] = useState<string>("")
  const [estimateMinutes, setEstimateMinutes] = useState<number>(30)
  const [slaTier, setSlaTier] = useState<string>("Medium")
  const [showOptions, setShowOptions] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    if (!title.trim()) return

    onCapture(title.trim(), {
      clientId: clientId || mockClients[0].id,
      estimateMinutes,
      slaTier,
    })

    // Clear form
    setTitle("")
    setClientId("")
    setEstimateMinutes(30)
    setSlaTier("Medium")
    setShowOptions(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === "Escape") {
      textareaRef.current?.blur()
      setShowOptions(false)
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [title])

  return (
    <div className="inbox-bar space-y-3">
      <div className="flex items-start gap-2">
        <textarea
          ref={textareaRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Capture a task... (Cmd/Ctrl+Enter to submit)"
          className="inbox-textarea flex-1 min-h-[40px] max-h-[120px]"
          rows={1}
        />
        <Button
          size="sm"
          onClick={() => setShowOptions(!showOptions)}
          variant="ghost"
          className="text-white/70 hover:text-white hover:bg-white/10"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {showOptions && (
        <div className="grid grid-cols-3 gap-2">
          <Select value={clientId} onValueChange={setClientId}>
            <SelectTrigger className="h-8 text-xs bg-white/5 border-white/10">
              <SelectValue placeholder="Client" />
            </SelectTrigger>
            <SelectContent>
              {mockClients.map((client) => (
                <SelectItem key={client.id} value={client.id}>
                  {client.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            type="number"
            value={estimateMinutes}
            onChange={(e) => setEstimateMinutes(Number(e.target.value))}
            placeholder="Minutes"
            className="h-8 text-xs bg-white/5 border-white/10"
            min={1}
          />

          <Select value={slaTier} onValueChange={setSlaTier}>
            <SelectTrigger className="h-8 text-xs bg-white/5 border-white/10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Low">Low</SelectItem>
              <SelectItem value="Medium">Medium</SelectItem>
              <SelectItem value="High">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}
