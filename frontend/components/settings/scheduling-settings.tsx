"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { SchedulingSettings } from "@/lib/settings-data"

interface SchedulingSettingsProps {
  scheduling: SchedulingSettings
  onChange: (scheduling: SchedulingSettings) => void
}

export function SchedulingSettingsComponent({ scheduling, onChange }: SchedulingSettingsProps) {
  const updateScheduling = (field: keyof SchedulingSettings, value: any) => {
    onChange({ ...scheduling, [field]: value })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scheduling Preferences</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="workStartHour">Work Start Hour</Label>
            <Select
              value={scheduling.workStartHour.toString()}
              onValueChange={(value) => updateScheduling("workStartHour", Number.parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 24 }, (_, i) => (
                  <SelectItem key={i} value={i.toString()}>
                    {i.toString().padStart(2, "0")}:00
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="workEndHour">Work End Hour</Label>
            <Select
              value={scheduling.workEndHour.toString()}
              onValueChange={(value) => updateScheduling("workEndHour", Number.parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 24 }, (_, i) => (
                  <SelectItem key={i} value={i.toString()}>
                    {i.toString().padStart(2, "0")}:00
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="meetingBuffer">Meeting Buffer (minutes)</Label>
            <Input
              id="meetingBuffer"
              type="number"
              min="0"
              step="5"
              value={scheduling.meetingBufferMinutes}
              onChange={(e) => updateScheduling("meetingBufferMinutes", Number.parseInt(e.target.value) || 0)}
            />
            <p className="text-xs text-muted-foreground">Buffer time before/after meetings</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="focusBlock">Focus Block Size (minutes)</Label>
            <Input
              id="focusBlock"
              type="number"
              min="30"
              step="30"
              value={scheduling.focusBlockMinutes}
              onChange={(e) => updateScheduling("focusBlockMinutes", Number.parseInt(e.target.value) || 30)}
            />
            <p className="text-xs text-muted-foreground">Default duration for focus blocks</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="breakDuration">Break Duration (minutes)</Label>
            <Input
              id="breakDuration"
              type="number"
              min="5"
              step="5"
              value={scheduling.breakDurationMinutes}
              onChange={(e) => updateScheduling("breakDurationMinutes", Number.parseInt(e.target.value) || 5)}
            />
            <p className="text-xs text-muted-foreground">Standard break length</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="maxConsecutive">Max Consecutive Hours</Label>
            <Input
              id="maxConsecutive"
              type="number"
              min="1"
              max="8"
              value={scheduling.maxConsecutiveHours}
              onChange={(e) => updateScheduling("maxConsecutiveHours", Number.parseInt(e.target.value) || 1)}
            />
            <p className="text-xs text-muted-foreground">Maximum hours of work without a break</p>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="deadlineHandling">Hard Deadline Handling</Label>
          <Select
            value={scheduling.hardDeadlineHandling}
            onValueChange={(value) => updateScheduling("hardDeadlineHandling", value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="strict">Strict - Never miss deadlines</SelectItem>
              <SelectItem value="flexible">Flexible - Allow minor overruns</SelectItem>
              <SelectItem value="advisory">Advisory - Warn but don't block</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">How to handle tasks approaching hard deadlines</p>
        </div>
      </CardContent>
    </Card>
  )
}
