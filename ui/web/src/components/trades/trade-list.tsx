'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import type { TradeSummary } from '@/lib/api'

interface TradeListProps {
  trades: TradeSummary[]
  onRefresh: () => void
}

function fmtTs(ts?: string) {
  if (!ts) return '-'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  return d.toLocaleString()
}

export function TradeList({ trades, onRefresh }: TradeListProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Trades</CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <p className="text-muted-foreground">No trades found</p>
        ) : (
          <div className="space-y-3">
            {trades.map((t) => (
              <div key={t.id} className="p-4 border rounded-lg space-y-1">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">
                    {t.account_name} · {t.side.toUpperCase()} · {(t.price * 100).toFixed(1)}¢ · {t.shares}
                  </div>
                  <div className="text-xs text-muted-foreground">{fmtTs(t.created_at)}</div>
                </div>

                <div className="text-sm text-muted-foreground font-mono break-all">
                  market: {t.market_id}
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-sm">
                    <span className="text-muted-foreground">status:</span> {t.status}
                    {t.error ? <span className="text-red-500"> · {t.error}</span> : null}
                  </div>
                  {t.order_hash ? (
                    <div className="text-xs text-muted-foreground font-mono">
                      hash: {t.order_hash.slice(0, 10)}…{t.order_hash.slice(-8)}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
