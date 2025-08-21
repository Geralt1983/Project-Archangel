"use client"

import { useState } from "react"
import { Navigation } from "@/components/navigation"
import { ClientSettingsTable } from "@/components/settings/client-settings-table"
import { WipCapsTable } from "@/components/settings/wip-caps-table"
import { ThresholdSettingsComponent } from "@/components/settings/threshold-settings"
import { SchedulingSettingsComponent } from "@/components/settings/scheduling-settings"
import { ApiSettingsComponent } from "@/components/settings/api-settings"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Save, RotateCcw } from "lucide-react"
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts"
import { defaultSettings, type AppSettings } from "@/lib/settings-data"

export default function SettingsPage() {
  useKeyboardShortcuts()

  const [settings, setSettings] = useState<AppSettings>(defaultSettings)
  const [hasChanges, setHasChanges] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const updateSettings = (updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }))
    setHasChanges(true)
  }

  const handleSave = async () => {
    setIsSaving(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setHasChanges(false)
    setIsSaving(false)
    console.log("Settings saved:", settings)
  }

  const handleReset = () => {
    setSettings(defaultSettings)
    setHasChanges(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="container mx-auto py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          {hasChanges && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Unsaved changes</span>
              <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
            </div>
          )}
        </div>

        <div className="space-y-8">
          {/* Client Settings */}
          <section>
            <ClientSettingsTable clients={settings.clients} onChange={(clients) => updateSettings({ clients })} />
          </section>

          <Separator />

          {/* WIP Caps */}
          <section>
            <WipCapsTable wipCaps={settings.wipCaps} onChange={(wipCaps) => updateSettings({ wipCaps })} />
          </section>

          <Separator />

          {/* Thresholds */}
          <section>
            <ThresholdSettingsComponent
              thresholds={settings.thresholds}
              onChange={(thresholds) => updateSettings({ thresholds })}
            />
          </section>

          <Separator />

          {/* Scheduling */}
          <section>
            <SchedulingSettingsComponent
              scheduling={settings.scheduling}
              onChange={(scheduling) => updateSettings({ scheduling })}
            />
          </section>

          <Separator />

          {/* API Settings */}
          <section>
            <ApiSettingsComponent apiKeys={settings.apiKeys} onChange={(apiKeys) => updateSettings({ apiKeys })} />
          </section>
        </div>

        {/* Save/Cancel Actions */}
        <div className="sticky bottom-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t mt-8 pt-4">
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleReset} disabled={!hasChanges || isSaving}>
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset to Defaults
            </Button>
            <Button onClick={handleSave} disabled={!hasChanges || isSaving}>
              <Save className="h-4 w-4 mr-1" />
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
