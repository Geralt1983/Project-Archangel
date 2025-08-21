"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { ThresholdSettings } from "@/lib/settings-data"

interface ThresholdSettingsProps {
  thresholds: ThresholdSettings
  onChange: (thresholds: ThresholdSettings) => void
}

export function ThresholdSettingsComponent({ thresholds, onChange }: ThresholdSettingsProps) {
  const updateThreshold = (field: keyof ThresholdSettings, value: number) => {
    onChange({ ...thresholds, [field]: value })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Alert Thresholds</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="hotTaskHours">Hot Task Threshold (hours)</Label>
            <Input
              id="hotTaskHours"
              type="number"
              min="1"
              value={thresholds.hotTaskHours}
              onChange={(e) => updateThreshold("hotTaskHours", Number.parseInt(e.target.value) || 1)}
            />
            <p className="text-xs text-muted-foreground">Tasks become "hot" after this many hours without progress</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="staleTaskDays">Stale Task Threshold (days)</Label>
            <Input
              id="staleTaskDays"
              type="number"
              min="1"
              value={thresholds.staleTaskDays}
              onChange={(e) => updateThreshold("staleTaskDays", Number.parseInt(e.target.value) || 1)}
            />
            <p className="text-xs text-muted-foreground">Tasks become "stale" after this many days without activity</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="slaWarningHours">SLA Warning (hours)</Label>
            <Input
              id="slaWarningHours"
              type="number"
              min="1"
              value={thresholds.slaWarningHours}
              onChange={(e) => updateThreshold("slaWarningHours", Number.parseInt(e.target.value) || 1)}
            />
            <p className="text-xs text-muted-foreground">Warn about SLA breach this many hours in advance</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="capacityThreshold">Capacity Threshold (%)</Label>
            <Input
              id="capacityThreshold"
              type="number"
              min="0"
              max="100"
              value={thresholds.capacityThresholdPercent}
              onChange={(e) => updateThreshold("capacityThresholdPercent", Number.parseInt(e.target.value) || 0)}
            />
            <p className="text-xs text-muted-foreground">Target capacity utilization percentage</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
