'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Position } from '@/lib/api'

interface Props {
  positions: Position[]
}

export function PositionsList({ positions }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <p className="text-muted-foreground">No positions</p>
        ) : (
          <div className="space-y-3">
            {positions.map((p, idx) => (
              <div key={idx} className="p-4 border rounded-lg">
                <div className="font-medium">
                  {p.side.toUpperCase()} · {p.shares} @ {p.avg_price}
                </div>
                <div className="text-sm text-muted-foreground font-mono break-all">
                  market: {p.market_id} · outcome: {p.outcome_id}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
