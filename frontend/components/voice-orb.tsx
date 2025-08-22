"use client"

import type React from "react"

import { motion, AnimatePresence } from "framer-motion"
import { useState } from "react"
import { Mic, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface VoiceOrbProps {
  onCreateTask?: (title: string) => void
}

export function VoiceOrb({ onCreateTask }: VoiceOrbProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [taskText, setTaskText] = useState("")

  const handleSubmit = () => {
    if (taskText.trim()) {
      onCreateTask?.(taskText.trim())
      setTaskText("")
      setIsOpen(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <>
      {/* Voice Orb Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className="relative w-16 h-16 rounded-full glass-3 flex items-center justify-center group overflow-hidden"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        animate={{
          boxShadow: [
            "0 0 20px rgba(45, 134, 255, 0.3)",
            "0 0 30px rgba(45, 134, 255, 0.5)",
            "0 0 20px rgba(45, 134, 255, 0.3)",
          ],
        }}
        transition={{
          boxShadow: {
            duration: 2,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          },
        }}
      >
        {/* Pulsing background */}
        <motion.div
          className="absolute inset-0 rounded-full bg-gradient-to-r from-brand-500/20 to-brand-400/20"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          }}
        />

        {/* Icon */}
        <Mic className="w-6 h-6 text-white/90 relative z-10" />

        {/* Ripple effect on hover */}
        <motion.div
          className="absolute inset-0 rounded-full bg-white/10"
          initial={{ scale: 0, opacity: 0 }}
          whileHover={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
        />
      </motion.button>

      {/* Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* Backdrop */}
            <motion.div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
            />

            {/* Modal Content */}
            <motion.div
              className="relative glass-4 rounded-3xl p-6 w-full max-w-md space-y-4"
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
            >
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-3 rounded-full glass-2 flex items-center justify-center">
                  <Mic className="w-6 h-6 text-brand-400" />
                </div>
                <h3 className="text-lg font-semibold text-white/90 mb-1">Quick Capture</h3>
                <p className="text-sm text-white/60">Describe your task</p>
              </div>

              <div className="space-y-4">
                <Textarea
                  value={taskText}
                  onChange={(e) => setTaskText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="What needs to be done?"
                  className="min-h-[100px] bg-white/5 border-white/10 text-white/90 placeholder-white/40 resize-none focus:border-brand-400/50 focus:ring-1 focus:ring-brand-400/30"
                  autoFocus
                />

                <div className="flex gap-2 justify-end">
                  <Button
                    variant="ghost"
                    onClick={() => setIsOpen(false)}
                    className="text-white/60 hover:text-white/90 hover:bg-white/10"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    disabled={!taskText.trim()}
                    className="bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Drop to Inbox
                  </Button>
                </div>
              </div>

              <div className="text-xs text-white/40 text-center">Press ⌘+Enter to submit</div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
