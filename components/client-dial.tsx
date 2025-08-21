"use client"

import { motion } from "framer-motion"
import { mockClients, mockTasks } from "@/lib/mock-data"
import { useMemo } from "react"

interface ClientAttention {
  clientId: string
  name: string
  percentage: number
  color: string
  taskCount: number
}

function computeWeeklyAttention(): ClientAttention[] {
  const clientStats = mockClients.map((client) => {
    const clientTasks = mockTasks.filter((task) => task.clientId === client.id)
    const totalMinutes = clientTasks.reduce((sum, task) => sum + task.estimateMinutes, 0)

    return {
      clientId: client.id,
      name: client.name,
      totalMinutes,
      taskCount: clientTasks.length,
      color: client.color,
    }
  })

  const grandTotal = clientStats.reduce((sum, stat) => sum + stat.totalMinutes, 0)

  return clientStats.map((stat) => ({
    clientId: stat.clientId,
    name: stat.name,
    percentage: grandTotal > 0 ? Math.round((stat.totalMinutes / grandTotal) * 100) : 0,
    color: stat.color,
    taskCount: stat.taskCount,
  }))
}

export function ClientDial() {
  const attentionData = useMemo(() => computeWeeklyAttention(), [])

  let cumulativeAngle = 0
  const segments = attentionData.map((data) => {
    const startAngle = cumulativeAngle
    const endAngle = cumulativeAngle + (data.percentage / 100) * 360
    cumulativeAngle = endAngle

    return {
      ...data,
      startAngle,
      endAngle,
      path: createArcPath(50, 50, 35, startAngle, endAngle),
    }
  })

  return (
    <div className="glass-2 rounded-3xl p-6 space-y-4">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-white/90 mb-1">Client Attention</h3>
        <p className="text-sm text-white/60">Weekly distribution</p>
      </div>

      <div className="flex items-center justify-center">
        <div className="relative">
          <svg width="120" height="120" className="transform -rotate-90">
            {/* Background circle */}
            <circle cx="60" cy="60" r="35" fill="none" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="8" />

            {/* Animated segments */}
            {segments.map((segment, index) => (
              <motion.path
                key={segment.clientId}
                d={segment.path}
                fill="none"
                stroke={getSegmentColor(segment.clientId)}
                strokeWidth="8"
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{
                  duration: 1.2,
                  delay: index * 0.2,
                  ease: [0.16, 1, 0.3, 1],
                }}
              />
            ))}
          </svg>

          {/* Center content */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-white/90">
                {attentionData.reduce((sum, data) => sum + data.taskCount, 0)}
              </div>
              <div className="text-xs text-white/60">tasks</div>
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-2">
        {attentionData.map((data, index) => (
          <motion.div
            key={data.clientId}
            className="flex items-center justify-between text-sm"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: 0.6,
              delay: 0.8 + index * 0.1,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getSegmentColor(data.clientId) }} />
              <span className="text-white/80">{data.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-white/60">{data.taskCount} tasks</span>
              <span className="text-white/90 font-medium">{data.percentage}%</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function createArcPath(cx: number, cy: number, radius: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, radius, startAngle)
  const end = polarToCartesian(cx, cy, radius, endAngle)
  const largeArcFlag = endAngle - startAngle > 180 ? "1" : "0"

  // Handle full circle case
  if (endAngle - startAngle >= 360) {
    const mid = polarToCartesian(cx, cy, radius, startAngle + 180)
    return [
      "M",
      start.x,
      start.y,
      "A",
      radius,
      radius,
      0,
      1,
      1,
      mid.x,
      mid.y,
      "A",
      radius,
      radius,
      0,
      1,
      1,
      start.x,
      start.y,
    ].join(" ")
  }

  return ["M", start.x, start.y, "A", radius, radius, 0, largeArcFlag, 1, end.x, end.y].join(" ")
}

function polarToCartesian(centerX: number, centerY: number, radius: number, angleInDegrees: number) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  }
}

function getSegmentColor(clientId: string): string {
  const client = mockClients.find((c) => c.id === clientId)
  return client?.color || "#6b7280"
}
