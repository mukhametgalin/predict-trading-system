'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { TradeSummary } from '@/lib/api'

interface Props {
  orders: any[]
}

export function OrdersList({ orders }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Orders</CardTitle>
      </CardHeader>
      <CardContent>
        {(!orders || orders.length === 0) ? (
          <p className="text-muted-foreground">No orders</p>
        ) : (
          <pre className="text-xs overflow-auto border rounded p-3 bg-muted">{JSON.stringify(orders, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  )
}
