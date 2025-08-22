"use client"

import { useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { type Task, mockClients } from "@/lib/mock-data"
import { Play, Square, Clock, Split, Flame, TrendingUp } from "lucide-react"

interface TaskDrawerProps {
  task: Task | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onTaskUpdate: (taskId: string, updates: Partial<Task>) => void
}

export function TaskDrawer({ task, open, onOpenChange, onTaskUpdate }: TaskDrawerProps) {
  const [editedTask, setEditedTask] = useState<Task | null>(null)

  if (!task) return null

  const currentTask = editedTask || task
  const client = mockClients.find((c) => c.id === currentTask.clientId)

  const handleSave = () => {
    if (editedTask) {
      onTaskUpdate(task.id, editedTask)
      setEditedTask(null)
    }
    onOpenChange(false)
  }

  const handleCancel = () => {
    setEditedTask(null)
    onOpenChange(false)
  }

  const updateField = (field: keyof Task, value: any) => {
    setEditedTask((prev) => ({
      ...(prev || task),
      [field]: value,
    }))
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-left">{currentTask.title}</SheetTitle>
          {client && (
            <Badge variant="outline" className={`w-fit ${client.color}`}>
              {client.name}
            </Badge>
          )}
        </SheetHeader>

        <Tabs defaultValue="details" className="mt-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="subtasks">Subtasks</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="json">JSON</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input id="title" value={currentTask.title} onChange={(e) => updateField("title", e.target.value)} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="valueScore">Value Score</Label>
                  <Input
                    id="valueScore"
                    type="number"
                    value={currentTask.valueScore}
                    onChange={(e) => updateField("valueScore", Number.parseInt(e.target.value))}
                  />
                </div>
                <div>
                  <Label htmlFor="decayLevel">Decay Level</Label>
                  <Input
                    id="decayLevel"
                    type="number"
                    value={currentTask.decayLevel}
                    onChange={(e) => updateField("decayLevel", Number.parseInt(e.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="slaTier">SLA Tier</Label>
                  <Select value={currentTask.slaTier} onValueChange={(value) => updateField("slaTier", value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Low">Low</SelectItem>
                      <SelectItem value="Medium">Medium</SelectItem>
                      <SelectItem value="High">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="estimateMinutes">Estimate (minutes)</Label>
                  <Input
                    id="estimateMinutes"
                    type="number"
                    value={currentTask.estimateMinutes}
                    onChange={(e) => updateField("estimateMinutes", Number.parseInt(e.target.value))}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="hardDeadline">Hard Deadline</Label>
                <Input
                  id="hardDeadline"
                  type="datetime-local"
                  value={currentTask.hardDeadline ? new Date(currentTask.hardDeadline).toISOString().slice(0, 16) : ""}
                  onChange={(e) =>
                    updateField("hardDeadline", e.target.value ? new Date(e.target.value).toISOString() : undefined)
                  }
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="autoplanAllowed"
                  checked={currentTask.autoplanAllowed}
                  onCheckedChange={(checked) => updateField("autoplanAllowed", checked)}
                />
                <Label htmlFor="autoplanAllowed">Autoplan Allowed</Label>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={currentTask.description || ""}
                  onChange={(e) => updateField("description", e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2 pt-4 border-t">
              <Button size="sm" variant="default">
                <Play className="h-4 w-4 mr-1" />
                Start
              </Button>
              <Button size="sm" variant="outline">
                <Square className="h-4 w-4 mr-1" />
                Stop
              </Button>
              <Button size="sm" variant="outline">
                <Clock className="h-4 w-4 mr-1" />
                Defer
              </Button>
              <Button size="sm" variant="outline">
                <Split className="h-4 w-4 mr-1" />
                Split
              </Button>
              <Button size="sm" variant="destructive">
                <Flame className="h-4 w-4 mr-1" />
                Burn
              </Button>
              <Button size="sm" variant="outline">
                <TrendingUp className="h-4 w-4 mr-1" />
                Bump
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="subtasks" className="space-y-2 mt-4">
            {currentTask.subtasks.map((subtask, index) => (
              <div key={index} className="flex items-center space-x-2 p-2 border rounded">
                <input type="checkbox" className="rounded" />
                <span className="text-sm">{subtask}</span>
              </div>
            ))}
            {currentTask.subtasks.length === 0 && <p className="text-muted-foreground text-sm">No subtasks defined</p>}
          </TabsContent>

          <TabsContent value="history" className="space-y-2 mt-4">
            {currentTask.history.map((entry, index) => (
              <div key={index} className="border-l-2 border-primary/20 pl-4 pb-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{entry.action}</span>
                  <span className="text-xs text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                <p className="text-sm text-muted-foreground">{entry.details}</p>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="json" className="mt-4">
            <pre className="bg-muted p-4 rounded text-xs overflow-auto">{JSON.stringify(currentTask, null, 2)}</pre>
          </TabsContent>
        </Tabs>

        {/* Save/Cancel buttons */}
        {editedTask && (
          <div className="flex justify-end space-x-2 pt-4 border-t mt-6">
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save Changes</Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
