"use client"

import type React from "react"
import { useRef, useState, useMemo, useEffect } from "react"
import { motion, useMotionValue, useTransform, AnimatePresence } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Clock, AlertTriangle, Flame, Timer, ArrowUp, Trash2 } from "lucide-react"
import { type Task, mockClients } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { cardVariants, staleVariants, microVariants, urgentPulseVariants } from "@/lib/motion"

interface TaskCardProps {
  task: Task
  onClick: () => void
  onBump?: (taskId: string, cardEl: HTMLElement) => void
  onBurn?: (taskId: string) => void
  onSendToReady?: (taskId: string, cardEl: HTMLElement) => void
  compact?: boolean
}

function createEmbersFrom(element: HTMLElement, count: number, duration: number) {
  const rect = element.getBoundingClientRect()
  const embers: HTMLElement[] = []

  for (let i = 0; i < count; i++) {
    const ember = document.createElement("div")
    ember.className = "ember"

    const size = Math.random() * 3 + 1
    const hue = 15 + Math.random() * 30 // Orange to red range

    ember.style.cssText = `
      position: fixed;
      width: ${size}px;
      height: ${size}px;
      background: radial-gradient(circle, hsl(${hue}, 100%, 60%) 0%, hsl(${hue + 10}, 90%, 50%) 50%, transparent 100%);
      border-radius: 50%;
      pointer-events: none;
      z-index: 9999;
      left: ${rect.left + Math.random() * rect.width}px;
      top: ${rect.bottom - 10}px;
      box-shadow: 0 0 ${size * 2}px hsl(${hue}, 100%, 60%);
    `

    document.body.appendChild(ember)
    embers.push(ember)

    const startTime = Date.now()
    const startX = Number.parseFloat(ember.style.left)
    const startY = Number.parseFloat(ember.style.top)
    const velocityX = (Math.random() - 0.5) * 120
    const velocityY = -Math.random() * 100 - 80
    const gravity = 50
    const wind = 20
    const rotation = Math.random() * 720

    function animateEmber() {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const t = elapsed / 1000

      const currentX = startX + velocityX * t + wind * t * t * 0.5
      const currentY = startY + velocityY * t + gravity * t * t * 0.5
      const opacity = Math.max(0, 1 - progress * progress)
      const scale = Math.max(0, 1 - progress * 0.7)

      ember.style.left = `${currentX}px`
      ember.style.top = `${currentY}px`
      ember.style.opacity = opacity.toString()
      ember.style.transform = `scale(${scale}) rotate(${rotation * progress}deg)`

      if (progress < 1) {
        requestAnimationFrame(animateEmber)
      } else {
        if (document.body.contains(ember)) {
          document.body.removeChild(ember)
        }
      }
    }

    requestAnimationFrame(animateEmber)
  }
}

export function TaskCard({ task, onClick, onBump, onBurn, onSendToReady, compact = false }: TaskCardProps) {
  const [isBurning, setIsBurning] = useState(false)
  const [isAsh, setIsAsh] = useState(false)
  const [isInteracted, setIsInteracted] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const client = mockClients.find((c) => c.id === task.clientId)
  const isUrgent = task.hasSlaRisk || task.isHot

  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const rotateX = useTransform(mouseY, [-100, 100], [5, -5])
  const rotateY = useTransform(mouseX, [-100, 100], [-5, 5])

  const boingSound = useMemo(() => {
    if (typeof window !== "undefined") {
      const audio = new Audio("/sounds/boing.mp3")
      audio.preload = "auto"
      return audio
    }
    return null
  }, [])

  useEffect(() => {
    if (isInteracted && task.isStale) {
      const timer = setTimeout(() => setIsInteracted(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [isInteracted, task.isStale])

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!cardRef.current) return

    if (task.isStale && !isInteracted) {
      setIsInteracted(true)
    }

    const rect = cardRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    mouseX.set(e.clientX - centerX)
    mouseY.set(e.clientY - centerY)
  }

  const handleMouseLeave = () => {
    mouseX.set(0)
    mouseY.set(0)
  }

  const handleBurnClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (isBurning) return

    setIsBurning(true)

    // Create ember burst
    const cardElement = e.currentTarget.closest(".card") as HTMLElement
    if (cardElement) {
      const emberCount = isUrgent ? 120 : 80
      createEmbersFrom(cardElement, emberCount, 1800)
    }

    // Add ash class after 500ms
    setTimeout(() => {
      setIsAsh(true)
    }, 500)

    // Call onBurn after 1400ms total
    setTimeout(() => {
      console.log("onBurn", task.id)
      onBurn?.(task.id)
    }, 1400)
  }

  const handleBumpClick = (e: React.MouseEvent) => {
    e.stopPropagation()

    if (boingSound) {
      boingSound.currentTime = 0
      boingSound.play().catch(() => {})
    }

    if (task.isStale) {
      setIsInteracted(true)
    }

    if (cardRef.current && onBump) {
      onBump(task.id, cardRef.current)
    }
  }

  const handleSendToReadyClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (cardRef.current && onSendToReady) {
      onSendToReady(task.id, cardRef.current)
    }
  }

  const handleCardClick = () => {
    if (task.isStale) {
      setIsInteracted(true)
    }
    onClick()
  }

  return (
    <motion.div
      ref={cardRef}
      variants={cardVariants}
      initial="initial"
      animate="animate"
      whileHover="hover"
      whileTap="tap"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        perspective: 1000,
        transformStyle: "preserve-3d",
      }}
    >
      <motion.div
        style={{
          rotateX: compact ? 0 : rotateX,
          rotateY: compact ? 0 : rotateY,
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <Card
          className={cn(
            "card cursor-pointer transition-all duration-200 border-white/10 bg-white/5 backdrop-blur-xs shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent rounded-2xl relative overflow-hidden",
            compact ? "card-compact" : "card-normal",
            isBurning && "burning",
            isAsh && "ash",
          )}
          onClick={handleCardClick}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault()
              handleCardClick()
            }
          }}
          data-id={task.id}
          data-client={task.clientId}
          aria-label={`Task: ${task.title}. Client: ${client?.name}. Status: ${task.status}${task.isStale ? ". Stale task" : ""}${isUrgent ? ". Urgent" : ""}`}
        >
          <AnimatePresence>
            {task.isStale && (
              <motion.div
                className="absolute inset-0 rounded-2xl pointer-events-none"
                variants={staleVariants}
                initial="initial"
                animate={isInteracted ? "refresh" : "crumble"}
                exit="refresh"
                style={{
                  border: "1px solid",
                  borderColor: "rgba(255, 255, 255, 0.1)",
                }}
              />
            )}
          </AnimatePresence>

          {isUrgent && (
            <motion.div
              className="absolute inset-0 rounded-2xl pointer-events-none"
              variants={urgentPulseVariants}
              initial="initial"
              animate="pulse"
            />
          )}

          {/* Burn overlay */}
          <div className="burn-overlay" />

          {/* Char overlay */}
          <div className="char" />

          <CardContent className="p-3 space-y-2 relative z-10">
            {/* Title */}
            <motion.h3
              className="font-medium text-sm leading-tight line-clamp-2 text-white"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              {task.title}
            </motion.h3>

            {/* Meta content - hidden when compact */}
            {!compact && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                {/* Client tag */}
                {client && (
                  <motion.div variants={microVariants} whileHover="hover" whileTap="tap">
                    <Badge
                      variant="outline"
                      className={cn("text-xs border-white/20 bg-white/10 text-white/90", client.color)}
                    >
                      {client.name}
                    </Badge>
                  </motion.div>
                )}

                {/* Metrics row */}
                <div className="flex items-center justify-between text-xs text-white/70">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white/90">VS: {task.valueScore}</span>
                    <span>D{task.decayLevel}</span>
                    <motion.span
                      variants={microVariants}
                      whileHover="hover"
                      className={cn(
                        "px-1.5 py-0.5 rounded text-xs font-medium cursor-default",
                        task.slaTier === "High"
                          ? "bg-red-500/20 text-red-300 border border-red-400/30"
                          : task.slaTier === "Medium"
                            ? "bg-yellow-500/20 text-yellow-300 border border-yellow-400/30"
                            : "bg-green-500/20 text-green-300 border border-green-400/30",
                      )}
                    >
                      {task.slaTier}
                    </motion.span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{task.estimateMinutes}m</span>
                  </div>
                </div>

                {/* Planned times */}
                {task.plannedStart && task.plannedEnd && (
                  <div className="text-xs text-white/70">
                    <div className="flex items-center gap-1">
                      <Timer className="h-3 w-3" />
                      <span>
                        {new Date(task.plannedStart).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -
                        {new Date(task.plannedEnd).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                )}

                {/* Status badges */}
                <div className="flex flex-wrap gap-1">
                  {task.isHot && (
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.3, type: "spring", stiffness: 300 }}
                      variants={microVariants}
                      whileHover="hover"
                    >
                      <Badge
                        variant="destructive"
                        className="text-xs px-1.5 py-0 bg-red-500/30 text-red-200 border-red-400/40"
                      >
                        <Flame className="h-2.5 w-2.5 mr-1" />
                        Hot
                      </Badge>
                    </motion.div>
                  )}
                  {task.isStale && (
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.35, type: "spring", stiffness: 300 }}
                      variants={microVariants}
                      whileHover="hover"
                    >
                      <Badge
                        variant="outline"
                        className="text-xs px-1.5 py-0 text-orange-300 border-orange-400/40 bg-orange-500/20"
                      >
                        Stale
                      </Badge>
                    </motion.div>
                  )}
                  {task.hasSlaRisk && (
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.4, type: "spring", stiffness: 300 }}
                      variants={microVariants}
                      whileHover="hover"
                    >
                      <Badge
                        variant="outline"
                        className="text-xs px-1.5 py-0 text-red-300 border-red-400/40 bg-red-500/20"
                      >
                        <AlertTriangle className="h-2.5 w-2.5 mr-1" />
                        SLA Risk
                      </Badge>
                    </motion.div>
                  )}
                  {task.autoplanAllowed && (
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.45, type: "spring", stiffness: 300 }}
                      variants={microVariants}
                      whileHover="hover"
                    >
                      <Badge
                        variant="outline"
                        className="text-xs px-1.5 py-0 text-brand-300 border-brand-400/40 bg-brand-500/20"
                      >
                        Autoplan
                      </Badge>
                    </motion.div>
                  )}
                </div>

                {/* Action buttons */}
                <motion.div
                  className="flex items-center justify-end gap-1 pt-1"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  {task.status === "inbox" ? (
                    <>
                      <motion.div variants={microVariants} whileHover="hover" whileTap="tap">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-green-400/70 hover:text-green-300 hover:bg-green-500/10 transition-all duration-200"
                          onClick={handleSendToReadyClick}
                        >
                          <ArrowUp className="h-3 w-3 mr-1" />
                          Ready
                        </Button>
                      </motion.div>
                      <motion.div variants={microVariants} whileHover="hover" whileTap="tap">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-red-400/70 hover:text-red-300 hover:bg-red-500/10 transition-all duration-200"
                          onClick={handleBurnClick}
                          disabled={isBurning}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          Burn
                        </Button>
                      </motion.div>
                    </>
                  ) : (
                    <>
                      <motion.div variants={microVariants} whileHover="hover" whileTap="tap">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-white/70 hover:text-white hover:bg-white/10 transition-all duration-200"
                          onClick={handleBumpClick}
                        >
                          <ArrowUp className="h-3 w-3 mr-1" />
                          Bump
                        </Button>
                      </motion.div>
                      <motion.div variants={microVariants} whileHover="hover" whileTap="tap">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-red-400/70 hover:text-red-300 hover:bg-red-500/10 transition-all duration-200"
                          onClick={handleBurnClick}
                          disabled={isBurning}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          Burn
                        </Button>
                      </motion.div>
                    </>
                  )}
                </motion.div>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
