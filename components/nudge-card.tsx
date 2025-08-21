"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, X, Clock, AlertTriangle } from "lucide-react"
import { type Nudge, getPriorityColor, getCategoryIcon } from "@/lib/nudges-data"
import { cn } from "@/lib/utils"

interface NudgeCardProps {
  nudge: Nudge
  onApprove: (nudgeId: string) => void
  onRefuse: (nudgeId: string) => void
  isProcessing?: boolean
}

export function NudgeCard({ nudge, onApprove, onRefuse, isProcessing }: NudgeCardProps) {
  const isActionable = nudge.status === "pending"
  const priorityColor = getPriorityColor(nudge.priority)
  const categoryIcon = getCategoryIcon(nudge.category)

  const getStatusBadge = () => {
    switch (nudge.status) {
      case "approved":
        return (
          <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
            <Check className="h-3 w-3 mr-1" />
            Approved
          </Badge>
        )
      case "refused":
        return (
          <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
            <X className="h-3 w-3 mr-1" />
            Refused
          </Badge>
        )
      default:
        return null
    }
  }

  return (
    <Card
      className={cn(
        "transition-all duration-200",
        isProcessing && "opacity-50",
        !nudge.isRead && "border-l-4 border-l-primary",
      )}
    >
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">{categoryIcon}</span>
              <Badge variant="outline" className={cn("text-xs", priorityColor)}>
                {nudge.priority}
              </Badge>
              {!nudge.isRead && (
                <Badge variant="outline" className="text-xs text-blue-600 border-blue-200 bg-blue-50">
                  New
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              {getStatusBadge()}
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {nudge.createdAt.toLocaleDateString()}
              </div>
            </div>
          </div>

          {/* Reason */}
          <div className="space-y-2">
            <p className="text-sm font-medium leading-relaxed">{nudge.reason}</p>

            {/* Audit Line */}
            <div className="bg-muted/50 rounded p-2 border-l-2 border-muted-foreground/20">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Audit Line</span>
              </div>
              <code className="text-xs font-mono text-muted-foreground break-all">{nudge.auditLine}</code>
            </div>
          </div>

          {/* Metadata */}
          {nudge.metadata && Object.keys(nudge.metadata).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(nudge.metadata).map(([key, value]) => (
                <Badge key={key} variant="secondary" className="text-xs">
                  {key}: {String(value)}
                </Badge>
              ))}
            </div>
          )}

          {/* Actions */}
          {isActionable && (
            <div className="flex gap-2 pt-2 border-t">
              <Button size="sm" onClick={() => onApprove(nudge.id)} disabled={isProcessing} className="flex-1">
                <Check className="h-4 w-4 mr-1" />
                Approve
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onRefuse(nudge.id)}
                disabled={isProcessing}
                className="flex-1"
              >
                <X className="h-4 w-4 mr-1" />
                Refuse
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
