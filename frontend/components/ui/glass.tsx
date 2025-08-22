import { cn } from "@/lib/utils"
import type { ReactNode } from "react"

interface GlassProps {
  children: ReactNode
  className?: string
}

export function Glass({ children, className }: GlassProps) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/10 bg-white/5 backdrop-blur-md shadow-glass",
        "hover:border-white/15 transition-colors duration-200",
        className,
      )}
    >
      {children}
    </div>
  )
}
