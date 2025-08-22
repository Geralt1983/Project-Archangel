"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Plus, Trash2 } from "lucide-react"
import type { ClientSettings } from "@/lib/settings-data"

interface ClientSettingsTableProps {
  clients: ClientSettings[]
  onChange: (clients: ClientSettings[]) => void
}

export function ClientSettingsTable({ clients, onChange }: ClientSettingsTableProps) {
  const [editingClients, setEditingClients] = useState<ClientSettings[]>(clients)

  const updateClient = (index: number, field: keyof ClientSettings, value: any) => {
    const updated = [...editingClients]
    updated[index] = { ...updated[index], [field]: value }
    setEditingClients(updated)
    onChange(updated)
  }

  const addClient = () => {
    const newClient: ClientSettings = {
      id: `client-${Date.now()}`,
      name: "New Client",
      weight: 0.1,
      defaultSlaTier: "Medium",
      wipClass: "Standard",
    }
    const updated = [...editingClients, newClient]
    setEditingClients(updated)
    onChange(updated)
  }

  const removeClient = (index: number) => {
    const updated = editingClients.filter((_, i) => i !== index)
    setEditingClients(updated)
    onChange(updated)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Client Configuration</h3>
        <Button onClick={addClient} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          Add Client
        </Button>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Client Name</TableHead>
              <TableHead>Weight</TableHead>
              <TableHead>Default SLA Tier</TableHead>
              <TableHead>WIP Class</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {editingClients.map((client, index) => (
              <TableRow key={client.id}>
                <TableCell>
                  <Input
                    value={client.name}
                    onChange={(e) => updateClient(index, "name", e.target.value)}
                    className="w-full"
                  />
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={client.weight}
                    onChange={(e) => updateClient(index, "weight", Number.parseFloat(e.target.value) || 0)}
                    className="w-20"
                  />
                </TableCell>
                <TableCell>
                  <Select
                    value={client.defaultSlaTier}
                    onValueChange={(value) => updateClient(index, "defaultSlaTier", value)}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Low">Low</SelectItem>
                      <SelectItem value="Medium">Medium</SelectItem>
                      <SelectItem value="High">High</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Select value={client.wipClass} onValueChange={(value) => updateClient(index, "wipClass", value)}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Standard">Standard</SelectItem>
                      <SelectItem value="Critical">Critical</SelectItem>
                      <SelectItem value="Flexible">Flexible</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeClient(index)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="text-sm text-muted-foreground">
        Total weight: {editingClients.reduce((sum, client) => sum + client.weight, 0).toFixed(2)}
        {editingClients.reduce((sum, client) => sum + client.weight, 0) !== 1 && (
          <span className="text-yellow-600 ml-2">⚠ Weights should sum to 1.0</span>
        )}
      </div>
    </div>
  )
}
