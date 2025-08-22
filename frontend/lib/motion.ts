"use client"

import type { Variants } from "framer-motion"

// Card animation variants
export const cardVariants: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    scale: 0.95,
    rotateX: 0,
    rotateY: 0,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    rotateX: 0,
    rotateY: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  hover: {
    y: -4,
    scale: 1.02,
    rotateX: 2,
    rotateY: 3,
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  tap: {
    scale: 0.98,
    rotateX: 0,
    rotateY: 0,
    transition: {
      duration: 0.1,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    y: -20,
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

// Morphing animation for inbox to board transitions
export const morphVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0.8,
    y: 20,
  },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  morph: {
    scale: [1, 1.1, 1.05],
    rotateX: [0, 5, 0],
    rotateY: [0, -3, 0],
    transition: {
      duration: 0.8,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  fly: {
    scale: 0.9,
    opacity: 0.8,
    transition: {
      duration: 1.2,
      ease: [0.22, 0.61, 0.36, 1],
    },
  },
}

// Staggered container animations
export const containerVariants: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

// Breathing animation for idle states
export const breatheVariants: Variants = {
  initial: {
    scale: 1,
    filter: "brightness(1)",
  },
  breathe: {
    scale: [1, 1.02, 1],
    filter: ["brightness(1)", "brightness(1.1)", "brightness(1)"],
    transition: {
      duration: 4,
      repeat: Number.POSITIVE_INFINITY,
      ease: "easeInOut",
    },
  },
}

// Floating animation for orbs and special elements
export const floatVariants: Variants = {
  initial: {
    y: 0,
  },
  float: {
    y: [-2, 2, -2],
    transition: {
      duration: 6,
      repeat: Number.POSITIVE_INFINITY,
      ease: "easeInOut",
    },
  },
}

// Glow animation for interactive elements
export const glowVariants: Variants = {
  initial: {
    boxShadow: "0 0 0 rgba(45, 134, 255, 0)",
  },
  glow: {
    boxShadow: ["0 0 0 rgba(45, 134, 255, 0)", "0 0 20px rgba(45, 134, 255, 0.4)", "0 0 0 rgba(45, 134, 255, 0)"],
    transition: {
      duration: 2,
      repeat: Number.POSITIVE_INFINITY,
      ease: "easeInOut",
    },
  },
}

// Slide up animation for modals and panels
export const slideUpVariants: Variants = {
  initial: {
    opacity: 0,
    y: 50,
    scale: 0.95,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 300,
    },
  },
  exit: {
    opacity: 0,
    y: 30,
    scale: 0.95,
    transition: {
      duration: 0.2,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

// Enhanced stale task crumbling animation with particle effects
export const staleVariants: Variants = {
  initial: {
    borderColor: "rgba(255, 255, 255, 0.1)",
    filter: "brightness(1) saturate(1)",
    boxShadow: "0 0 0 rgba(255, 165, 0, 0)",
  },
  crumble: {
    borderColor: [
      "rgba(255, 255, 255, 0.1)",
      "rgba(255, 165, 0, 0.2)",
      "rgba(255, 107, 53, 0.4)",
      "rgba(139, 69, 19, 0.6)",
      "rgba(101, 67, 33, 0.8)",
    ],
    filter: [
      "brightness(1) saturate(1)",
      "brightness(0.95) saturate(0.9)",
      "brightness(0.9) saturate(0.8)",
      "brightness(0.85) saturate(0.7)",
      "brightness(0.8) saturate(0.6)",
    ],
    boxShadow: [
      "0 0 0 rgba(255, 165, 0, 0)",
      "0 0 5px rgba(255, 165, 0, 0.2)",
      "0 0 10px rgba(255, 107, 53, 0.3)",
      "0 0 15px rgba(139, 69, 19, 0.4)",
      "0 0 20px rgba(101, 67, 33, 0.5)",
    ],
    transition: {
      duration: 12,
      repeat: Number.POSITIVE_INFINITY,
      ease: "easeInOut",
      times: [0, 0.25, 0.5, 0.75, 1],
    },
  },
  refresh: {
    borderColor: "rgba(255, 255, 255, 0.1)",
    filter: "brightness(1) saturate(1)",
    boxShadow: "0 0 0 rgba(255, 165, 0, 0)",
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

// Micro-interaction variants for buttons and interactive elements
export const microVariants: Variants = {
  initial: {
    scale: 1,
    filter: "brightness(1)",
  },
  hover: {
    scale: 1.02,
    filter: "brightness(1.1)",
    transition: {
      duration: 0.2,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  tap: {
    scale: 0.98,
    filter: "brightness(0.95)",
    transition: {
      duration: 0.1,
      ease: "easeOut",
    },
  },
}

// Enhanced glass panel animations
export const panelVariants: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    scale: 0.95,
    filter: "blur(4px)",
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: {
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.98,
    filter: "blur(2px)",
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

// Attention-seeking pulse for urgent elements
export const urgentPulseVariants: Variants = {
  initial: {
    boxShadow: "0 0 0 0 rgba(239, 68, 68, 0)",
  },
  pulse: {
    boxShadow: ["0 0 0 0 rgba(239, 68, 68, 0.4)", "0 0 0 8px rgba(239, 68, 68, 0)", "0 0 0 0 rgba(239, 68, 68, 0)"],
    transition: {
      duration: 2,
      repeat: Number.POSITIVE_INFINITY,
      ease: "easeOut",
    },
  },
}

// Success celebration animation
export const celebrationVariants: Variants = {
  initial: {
    scale: 1,
    rotate: 0,
  },
  celebrate: {
    scale: [1, 1.1, 1],
    rotate: [0, 5, -5, 0],
    transition: {
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

// Spring configuration presets
export const springConfig = {
  gentle: { type: "spring" as const, damping: 25, stiffness: 300 },
  bouncy: { type: "spring" as const, damping: 15, stiffness: 400 },
  snappy: { type: "spring" as const, damping: 30, stiffness: 500 },
}

// Easing presets
export const easings = {
  smooth: [0.16, 1, 0.3, 1] as const,
  bounce: [0.68, -0.55, 0.265, 1.55] as const,
  sharp: [0.4, 0, 0.2, 1] as const,
}
