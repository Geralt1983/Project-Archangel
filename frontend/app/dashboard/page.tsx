"use client"

import { useState, useMemo } from "react"
import { motion } from "framer-motion"
import { Navigation } from "@/components/navigation"
import { TaskCard } from "@/components/task-card"
import { ClientDial } from "@/components/client-dial"
import { VoiceOrb } from "@/components/voice-orb"
import { Glass } from "@/components/ui/glass"
import { FadeIn } from "@/components/ui/fade-in"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { mockTasks, mockClients, type Task } from "@/lib/mock-data"
import { containerVariants, cardVariants } from "@/lib/motion"
import { TrendingUp, Clock, AlertTriangle, CheckCircle, Activity, Calendar, Target } from "lucide-react"
import { cn } from "@/lib/utils"

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>(mockTasks)

  // Compute dashboard metrics
  const metrics = useMemo(() => {
    const totalTasks = tasks.length
    const completedTasks = tasks.filter((t) => t.status === "done").length
    const urgentTasks = tasks.filter((t) => t.isHot || t.hasSlaRisk).length
    const staleTasks = tasks.filter((t) => t.isStale).length
    const doingTasks = tasks.filter((t) => t.status === "doing").length

    const totalMinutes = tasks.reduce((sum, task) => sum + task.estimateMinutes, 0)
    const completedMinutes = tasks
      .filter((t) => t.status === "done")
      .reduce((sum, task) => sum + task.estimateMinutes, 0)

    const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0
    const productivityScore = totalMinutes > 0 ? Math.round((completedMinutes / totalMinutes) * 100) : 0

    return {
      totalTasks,
      completedTasks,
      urgentTasks,
      staleTasks,
      doingTasks,
      completionRate,
      productivityScore,
      totalHours: Math.round((totalMinutes / 60) * 10) / 10,
      completedHours: Math.round((completedMinutes / 60) * 10) / 10,
    }
  }, [tasks])

  // Get featured tasks (urgent, recent, or high value)
  const featuredTasks = useMemo(() => {
    return tasks
      .filter((t) => t.status !== "done")
      .sort((a, b) => {
        // Prioritize urgent tasks
        if (a.isHot !== b.isHot) return b.isHot ? 1 : -1
        if (a.hasSlaRisk !== b.hasSlaRisk) return b.hasSlaRisk ? 1 : -1
        // Then by value score
        return b.valueScore - a.valueScore
      })
      .slice(0, 6)
  }, [tasks])

  const handleCreateTask = (title: string) => {
    const newTask: Task = {
      id: crypto.randomUUID(),
      title,
      clientId: mockClients[0].id,
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
      history: [
        {
          timestamp: new Date().toISOString(),
          action: "Created",
          details: "Created via voice capture",
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }

    setTasks((prev) => [newTask, ...prev])
  }

  return (
    <div className="min-h-screen bg-grain">
      <Navigation />

      <main className="container mx-auto py-6 space-y-8">
        {/* Hero Section */}
        <motion.div variants={containerVariants} initial="initial" animate="animate" className="space-y-6">
          <FadeIn>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Command Center</h1>
                <p className="text-lg text-white/70">Your productivity orchestration hub</p>
              </div>

              <div className="flex items-center gap-4">
                <VoiceOrb onCreateTask={handleCreateTask} />
                <Button variant="outline" className="glass-interactive border-white/20 text-white/90 bg-transparent">
                  <Calendar className="w-4 h-4 mr-2" />
                  Schedule
                </Button>
              </div>
            </div>
          </FadeIn>

          {/* Metrics Hero Bar */}
          <FadeIn delay={0.1}>
            <Glass className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <motion.div variants={cardVariants} className="text-center space-y-2">
                  <div className="w-12 h-12 mx-auto rounded-2xl glass-2 flex items-center justify-center">
                    <Target className="w-6 h-6 text-brand-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{metrics.completionRate}%</div>
                  <div className="text-sm text-white/60">Completion Rate</div>
                </motion.div>

                <motion.div variants={cardVariants} className="text-center space-y-2">
                  <div className="w-12 h-12 mx-auto rounded-2xl glass-2 flex items-center justify-center">
                    <Activity className="w-6 h-6 text-green-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{metrics.doingTasks}</div>
                  <div className="text-sm text-white/60">Active Tasks</div>
                </motion.div>

                <motion.div variants={cardVariants} className="text-center space-y-2">
                  <div className="w-12 h-12 mx-auto rounded-2xl glass-2 flex items-center justify-center">
                    <Clock className="w-6 h-6 text-blue-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{metrics.completedHours}h</div>
                  <div className="text-sm text-white/60">Completed Today</div>
                </motion.div>

                <motion.div variants={cardVariants} className="text-center space-y-2">
                  <div
                    className={cn(
                      "w-12 h-12 mx-auto rounded-2xl glass-2 flex items-center justify-center",
                      metrics.urgentTasks > 0 && "bloom-warm",
                    )}
                  >
                    <AlertTriangle
                      className={cn("w-6 h-6", metrics.urgentTasks > 0 ? "text-orange-400" : "text-white/60")}
                    />
                  </div>
                  <div className={cn("text-2xl font-bold", metrics.urgentTasks > 0 ? "text-orange-400" : "text-white")}>
                    {metrics.urgentTasks}
                  </div>
                  <div className="text-sm text-white/60">Urgent Items</div>
                </motion.div>
              </div>
            </Glass>
          </FadeIn>
        </motion.div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Client Dial */}
          <FadeIn delay={0.2}>
            <div className="space-y-6">
              <ClientDial />

              {/* Quick Stats */}
              <Glass className="p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white/90">Quick Stats</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Total Tasks</span>
                    <span className="text-sm font-medium text-white/90">{metrics.totalTasks}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Completed</span>
                    <span className="text-sm font-medium text-green-400">{metrics.completedTasks}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Stale Items</span>
                    <span
                      className={cn(
                        "text-sm font-medium",
                        metrics.staleTasks > 0 ? "text-orange-400" : "text-white/90",
                      )}
                    >
                      {metrics.staleTasks}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Productivity</span>
                    <span className="text-sm font-medium text-brand-400">{metrics.productivityScore}%</span>
                  </div>
                </div>
              </Glass>
            </div>
          </FadeIn>

          {/* Right Column - Featured Tasks */}
          <div className="lg:col-span-2">
            <FadeIn delay={0.3}>
              <Glass className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white/90">Priority Tasks</h3>
                  <Badge variant="outline" className="bg-brand-500/20 text-brand-300 border-brand-400/40">
                    {featuredTasks.length} items
                  </Badge>
                </div>

                <motion.div
                  variants={containerVariants}
                  initial="initial"
                  animate="animate"
                  className="grid grid-cols-1 md:grid-cols-2 gap-4"
                >
                  {featuredTasks.length === 0 ? (
                    <motion.div variants={cardVariants} className="col-span-full text-center py-12">
                      <CheckCircle className="w-12 h-12 mx-auto text-green-400 mb-4" />
                      <p className="text-white/70">All caught up! No priority tasks.</p>
                    </motion.div>
                  ) : (
                    featuredTasks.map((task, index) => (
                      <motion.div
                        key={task.id}
                        variants={cardVariants}
                        transition={{ delay: index * 0.1 }}
                        className="card-3d"
                      >
                        <TaskCard task={task} onClick={() => {}} compact={false} />
                      </motion.div>
                    ))
                  )}
                </motion.div>

                {featuredTasks.length > 0 && (
                  <motion.div variants={cardVariants} className="mt-6 text-center">
                    <Button
                      variant="outline"
                      className="glass-interactive border-white/20 text-white/90 bg-transparent"
                    >
                      <TrendingUp className="w-4 h-4 mr-2" />
                      View All Tasks
                    </Button>
                  </motion.div>
                )}
              </Glass>
            </FadeIn>
          </div>
        </div>

        {/* Bottom Section - Recent Activity */}
        <FadeIn delay={0.4}>
          <Glass className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white/90">Recent Activity</h3>
              <Button variant="ghost" size="sm" className="text-white/60 hover:text-white/90">
                View All
              </Button>
            </div>

            <div className="space-y-3">
              {tasks
                .filter((t) => t.history.length > 0)
                .slice(0, 5)
                .map((task, index) => {
                  const lastActivity = task.history[task.history.length - 1]
                  return (
                    <motion.div
                      key={task.id}
                      variants={cardVariants}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center gap-4 p-3 rounded-lg glass-1 hover:glass-2 transition-all"
                    >
                      <div className="w-8 h-8 rounded-full glass-2 flex items-center justify-center">
                        <Activity className="w-4 h-4 text-brand-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white/90 truncate">{task.title}</p>
                        <p className="text-xs text-white/60">
                          {lastActivity.action} • {new Date(lastActivity.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                      <Badge variant="outline" className="text-xs border-white/20 bg-white/10 text-white/70">
                        {task.status}
                      </Badge>
                    </motion.div>
                  )
                })}
            </div>
          </Glass>
        </FadeIn>
      </main>
    </div>
  )
}
