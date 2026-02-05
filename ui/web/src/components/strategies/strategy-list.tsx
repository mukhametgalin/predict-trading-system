'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { updateStrategy, type Strategy } from '@/lib/api'
import { RefreshCw } from 'lucide-react'

interface StrategyListProps {
  strategies: Strategy[]
  onRefresh: () => void
}

export function StrategyList({ strategies, onRefresh }: StrategyListProps) {
  const [loading, setLoading] = useState<string | null>(null)

  const handleToggle = async (strategy: Strategy) => {
    setLoading(strategy.id)
    try {
      await updateStrategy(strategy.id, { enabled: !strategy.enabled })
      onRefresh()
    } catch (err) {
      console.error('Failed to toggle strategy:', err)
    } finally {
      setLoading(null)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Strategies</CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {strategies.length === 0 ? (
          <p className="text-muted-foreground">No strategies configured</p>
        ) : (
          <div className="space-y-4">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{strategy.name}</span>
                    <span className="text-xs bg-secondary px-2 py-0.5 rounded">
                      {strategy.type}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {Object.keys(strategy.config).length} config options
                  </p>
                </div>
                <Switch
                  checked={strategy.enabled}
                  disabled={loading === strategy.id}
                  onCheckedChange={() => handleToggle(strategy)}
                />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
