'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import type { Market } from '@/lib/api'

interface MarketListProps {
  markets: Market[]
  onRefresh: () => void
}

export function MarketList({ markets, onRefresh }: MarketListProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Markets</CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {markets.length === 0 ? (
          <p className="text-muted-foreground">No markets found</p>
        ) : (
          <div className="space-y-4">
            {markets.map((market) => (
              <div
                key={market.market_id}
                className="p-4 border rounded-lg space-y-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-secondary px-2 py-0.5 rounded">
                    {market.platform}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {market.category}
                  </span>
                </div>
                <p className="font-medium">{market.question}</p>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-green-600">
                    YES: {(market.yes_price * 100).toFixed(0)}¢
                  </span>
                  <span className="text-red-600">
                    NO: {(market.no_price * 100).toFixed(0)}¢
                  </span>
                  <span className="text-muted-foreground">
                    Vol: ${market.volume_24h.toFixed(0)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
