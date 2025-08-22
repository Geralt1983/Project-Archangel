"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Bell } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Glass } from "@/components/ui/glass"
import { useNudges } from "@/components/nudges-provider"
import { NudgesPanel } from "@/components/nudges-panel"

const navigationItems = [
  { name: "Dashboard", href: "/dashboard", key: "d" },
  { name: "Board", href: "/", key: "b" },
  { name: "Schedule", href: "/schedule", key: "s" },
  { name: "Nudges", href: "/nudges", key: "n" },
  { name: "Settings", href: "/settings", key: "t" },
]

export function Navigation() {
  const pathname = usePathname()
  const { unreadCount, add: addNudge } = useNudges()
  const [nudgesOpen, setNudgesOpen] = useState(false)

  function seedExampleNudge() {
    addNudge({
      id: crypto.randomUUID(),
      title: "Task is aging. Bump now?",
      body: "This task has been in Ready for 2 days and may need attention.",
      createdAt: new Date().toISOString(),
      status: "unread",
      action: { type: "bump", payload: { taskId: "task-1" } },
    })
  }

  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b border-white/10 backdrop-blur-md">
        <Glass className="rounded-none border-x-0 border-t-0">
          <div className="container flex h-14 items-center">
            <div className="mr-4 hidden md:flex">
              <Link href="/" className="mr-6 flex items-center space-x-2">
                <span className="hidden font-bold sm:inline-block text-white">Project Archangel</span>
              </Link>
              <nav className="flex items-center space-x-6 text-sm font-medium">
                {navigationItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "transition-colors hover:text-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent rounded-md px-2 py-1",
                      pathname === item.href ? "text-white" : "text-white/70",
                    )}
                  >
                    {item.name}
                    <kbd className="ml-1 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-white/20 bg-white/10 px-1.5 font-mono text-[10px] font-medium text-white/80 opacity-100">
                      {item.key}
                    </kbd>
                  </Link>
                ))}
              </nav>
            </div>

            <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
              <div className="w-full flex-1 md:w-auto md:flex-none">
                {/* Mobile navigation */}
                <nav className="flex md:hidden items-center space-x-4">
                  {navigationItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "text-sm font-medium transition-colors hover:text-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent rounded-md px-2 py-1",
                        pathname === item.href ? "text-white" : "text-white/70",
                      )}
                    >
                      {item.name}
                    </Link>
                  ))}
                </nav>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={seedExampleNudge}
                  className="text-xs text-white/60 hover:text-white/80"
                >
                  + Test Nudge
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="relative hover:bg-white/10 text-white/80 hover:text-white focus-visible:ring-brand-500/60"
                  onClick={() => setNudgesOpen(true)}
                  aria-label={`View nudges${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
                >
                  <Bell className="h-4 w-4" />
                  {unreadCount > 0 && (
                    <Badge
                      variant="destructive"
                      className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs bg-red-500 text-white border-0"
                    >
                      {Math.min(unreadCount, 9)}
                    </Badge>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </Glass>
      </header>

      <NudgesPanel
        open={nudgesOpen}
        onOpenChange={setNudgesOpen}
        onApproveActions={{
          bump: (id) => {
            const el = document.querySelector<HTMLElement>(`[data-id="${id}"]`)
            if (el) {
              // Call existing handleBump - this would need to be passed down or accessed via context
              console.log("Bump action for task:", id)
            }
          },
          burn: (id) => {
            console.log("Burn action for task:", id)
          },
          reschedule: (id, minutes) => console.log("Reschedule action:", id, minutes),
          createTask: (title) => {
            console.log("Create task action:", title)
          },
        }}
      />
    </>
  )
}
