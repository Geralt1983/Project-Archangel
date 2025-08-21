"use client"

import { useState } from "react"
import { Navigation } from "@/components/navigation"
import { NudgeCard } from "@/components/nudge-card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Bell, CheckCircle, AlertCircle } from "lucide-react"
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts"
import { mockNudges, filterNudgesByTab, getUrgentNudges, type Nudge } from "@/lib/nudges-data"

export default function NudgesPage() {
  useKeyboardShortcuts()

  const [nudges, setNudges] = useState<Nudge[]>(mockNudges)
  const [processingNudges, setProcessingNudges] = useState<Set<string>>(new Set())
  const [activeTab, setActiveTab] = useState<"today" | "unread" | "all">("today")

  const handleApprove = async (nudgeId: string) => {
    // Optimistic UI update
    setProcessingNudges((prev) => new Set(prev).add(nudgeId))

    // Simulate API call delay
    setTimeout(() => {
      setNudges((prev) =>
        prev.map((nudge) => (nudge.id === nudgeId ? { ...nudge, status: "approved" as const, isRead: true } : nudge)),
      )
      setProcessingNudges((prev) => {
        const newSet = new Set(prev)
        newSet.delete(nudgeId)
        return newSet
      })
    }, 500)
  }

  const handleRefuse = async (nudgeId: string) => {
    // Optimistic UI update
    setProcessingNudges((prev) => new Set(prev).add(nudgeId))

    // Simulate API call delay
    setTimeout(() => {
      setNudges((prev) =>
        prev.map((nudge) => (nudge.id === nudgeId ? { ...nudge, status: "refused" as const, isRead: true } : nudge)),
      )
      setProcessingNudges((prev) => {
        const newSet = new Set(prev)
        newSet.delete(nudgeId)
        return newSet
      })
    }, 500)
  }

  const filteredNudges = filterNudgesByTab(nudges, activeTab)
  const urgentNudges = getUrgentNudges(nudges)
  const unreadCount = nudges.filter((n) => !n.isRead && n.status === "pending").length
  const todayCount = filterNudgesByTab(nudges, "today").length

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case "today":
        return <AlertCircle className="h-4 w-4" />
      case "unread":
        return <Bell className="h-4 w-4" />
      case "all":
        return <CheckCircle className="h-4 w-4" />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="container mx-auto py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Nudges</h1>
            {urgentNudges.length > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                {urgentNudges.length} urgent
              </Badge>
            )}
          </div>
          <div className="text-sm text-muted-foreground">
            {filteredNudges.length} nudge{filteredNudges.length !== 1 ? "s" : ""}
          </div>
        </div>

        {/* Urgent Nudges Alert */}
        {urgentNudges.length > 0 && activeTab !== "today" && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-red-800">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">
                {urgentNudges.length} urgent nudge{urgentNudges.length !== 1 ? "s" : ""} require
                {urgentNudges.length === 1 ? "s" : ""} immediate attention
              </span>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as typeof activeTab)}
          className="space-y-6"
        >
          <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
            <TabsTrigger value="today" className="flex items-center gap-2">
              {getTabIcon("today")}
              Today
              {todayCount > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                >
                  {todayCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="unread" className="flex items-center gap-2">
              {getTabIcon("unread")}
              Unread
              {unreadCount > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                >
                  {unreadCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="all" className="flex items-center gap-2">
              {getTabIcon("all")}
              All
            </TabsTrigger>
          </TabsList>

          <TabsContent value="today" className="space-y-4">
            {filteredNudges.length === 0 ? (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground mb-2">No nudges for today</h3>
                <p className="text-sm text-muted-foreground">All caught up! Check back later for new notifications.</p>
              </div>
            ) : (
              filteredNudges.map((nudge) => (
                <NudgeCard
                  key={nudge.id}
                  nudge={nudge}
                  onApprove={handleApprove}
                  onRefuse={handleRefuse}
                  isProcessing={processingNudges.has(nudge.id)}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="unread" className="space-y-4">
            {filteredNudges.length === 0 ? (
              <div className="text-center py-12">
                <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground mb-2">No unread nudges</h3>
                <p className="text-sm text-muted-foreground">You're all caught up with notifications.</p>
              </div>
            ) : (
              filteredNudges.map((nudge) => (
                <NudgeCard
                  key={nudge.id}
                  nudge={nudge}
                  onApprove={handleApprove}
                  onRefuse={handleRefuse}
                  isProcessing={processingNudges.has(nudge.id)}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="all" className="space-y-4">
            {filteredNudges.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground mb-2">No nudges yet</h3>
                <p className="text-sm text-muted-foreground">
                  Nudges will appear here as the system generates recommendations.
                </p>
              </div>
            ) : (
              filteredNudges.map((nudge) => (
                <NudgeCard
                  key={nudge.id}
                  nudge={nudge}
                  onApprove={handleApprove}
                  onRefuse={handleRefuse}
                  isProcessing={processingNudges.has(nudge.id)}
                />
              ))
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
