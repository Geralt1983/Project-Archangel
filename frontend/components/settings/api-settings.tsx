"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Eye, EyeOff, TestTube } from "lucide-react"
import type { ApiSettings } from "@/lib/settings-data"

interface ApiSettingsProps {
  apiKeys: ApiSettings
  onChange: (apiKeys: ApiSettings) => void
}

export function ApiSettingsComponent({ apiKeys, onChange }: ApiSettingsProps) {
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({})

  const updateApiKey = (field: keyof ApiSettings, value: string) => {
    onChange({ ...apiKeys, [field]: value })
  }

  const toggleTokenVisibility = (field: string) => {
    setShowTokens((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  const testConnection = (service: string) => {
    // Mock connection test
    console.log(`Testing connection to ${service}...`)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="clickupToken">ClickUp API Token</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="clickupToken"
                  type={showTokens.clickup ? "text" : "password"}
                  value={apiKeys.clickupToken}
                  onChange={(e) => updateApiKey("clickupToken", e.target.value)}
                  placeholder="pk_..."
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => toggleTokenVisibility("clickup")}
                >
                  {showTokens.clickup ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <Button variant="outline" size="sm" onClick={() => testConnection("ClickUp")}>
                <TestTube className="h-4 w-4 mr-1" />
                Test
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Your ClickUp personal API token for task synchronization</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="archangelBaseUrl">Archangel Base URL</Label>
            <Input
              id="archangelBaseUrl"
              type="url"
              value={apiKeys.archangelBaseUrl}
              onChange={(e) => updateApiKey("archangelBaseUrl", e.target.value)}
              placeholder="https://api.archangel.example.com"
            />
            <p className="text-xs text-muted-foreground">Base URL for the Archangel API service</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="archangelToken">Archangel API Token</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="archangelToken"
                  type={showTokens.archangel ? "text" : "password"}
                  value={apiKeys.archangelToken}
                  onChange={(e) => updateApiKey("archangelToken", e.target.value)}
                  placeholder="arch_..."
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => toggleTokenVisibility("archangel")}
                >
                  {showTokens.archangel ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <Button variant="outline" size="sm" onClick={() => testConnection("Archangel")}>
                <TestTube className="h-4 w-4 mr-1" />
                Test
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Authentication token for Archangel API access</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="googleCalendarUrl">Google Calendar Read-Only URL</Label>
            <div className="flex gap-2">
              <Input
                id="googleCalendarUrl"
                type="url"
                value={apiKeys.googleCalendarUrl}
                onChange={(e) => updateApiKey("googleCalendarUrl", e.target.value)}
                placeholder="https://calendar.google.com/calendar/ical/..."
              />
              <Button variant="outline" size="sm" onClick={() => testConnection("Google Calendar")}>
                <TestTube className="h-4 w-4 mr-1" />
                Test
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">iCal URL for read-only calendar integration</p>
          </div>
        </div>

        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="font-medium mb-2">Security Notice</h4>
          <p className="text-sm text-muted-foreground">
            API tokens are stored securely and encrypted. They are only used for authorized integrations and are never
            shared with third parties.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
