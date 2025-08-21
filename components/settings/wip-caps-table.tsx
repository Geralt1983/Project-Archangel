"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import type { WipCapSettings } from "@/lib/settings-data"

interface WipCapsTableProps {
  wipCaps: WipCapSettings[]
  onChange: (wipCaps: WipCapSettings[]) => void
}

export function WipCapsTable({ wipCaps, onChange }: WipCapsTableProps) {
  const updateWipCap = (index: number, field: keyof WipCapSettings, value: any) => {
    const updated = [...wipCaps]
    updated[index] = { ...updated[index], [field]: value }
    onChange(updated)
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">WIP Limits</h3>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>WIP Limit</TableHead>
              <TableHead>Enabled</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {wipCaps.map((wipCap, index) => (
              <TableRow key={wipCap.status}>
                <TableCell className="font-medium capitalize">{wipCap.status}</TableCell>
                <TableCell>
                  <Input
                    type="number"
                    min="0"
                    value={wipCap.cap || ""}
                    onChange={(e) =>
                      updateWipCap(index, "cap", e.target.value ? Number.parseInt(e.target.value) : null)
                    }
                    disabled={!wipCap.enabled}
                    className="w-20"
                    placeholder="No limit"
                  />
                </TableCell>
                <TableCell>
                  <Switch
                    checked={wipCap.enabled}
                    onCheckedChange={(checked) => updateWipCap(index, "enabled", checked)}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
