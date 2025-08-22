"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export function useKeyboardShortcuts() {
  const router = useRouter()

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only trigger if no input is focused and no modifiers except Alt
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey
      ) {
        return
      }

      switch (event.key.toLowerCase()) {
        case "b":
          event.preventDefault()
          router.push("/")
          break
        case "s":
          event.preventDefault()
          router.push("/schedule")
          break
        case "n":
          event.preventDefault()
          router.push("/nudges")
          break
        case "t":
          event.preventDefault()
          router.push("/settings")
          break
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [router])
}
