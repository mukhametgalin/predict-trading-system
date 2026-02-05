'use client'

import { useEffect, useState, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StatsCards } from '@/components/dashboard/stats-cards'
import { AccountList } from '@/components/accounts/account-list'
import { PositionsList } from '@/components/positions/positions-list'
import { OrdersList } from '@/components/orders/orders-list'
import { StrategyList } from '@/components/strategies/strategy-list'
import { MarketList } from '@/components/markets/market-list'
import { AlertList } from '@/components/alerts/alert-list'
import { TradeList } from '@/components/trades/trade-list'
import {
  getStats,
  getAccounts,
  getPositions,
  getOrders,
  getStrategies,
  getMarkets,
  getAlerts,
  getTrades,
  type DashboardStats,
  type Account,
  type Strategy,
  type Market,
  type Alert,
  type TradeSummary,
} from '@/lib/api'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [positions, setPositions] = useState<Record<string, any[]>>({})
  const [orders, setOrders] = useState<Record<string, any[]>>({})
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [markets, setMarkets] = useState<Market[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trades, setTrades] = useState<TradeSummary[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const loadStats = useCallback(async () => {
    try {
      const data = await getStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [])

  const loadAccountTelemetry = useCallback(async (accs: Account[]) => {
    const pos: Record<string, any[]> = {}
    const ord: Record<string, any[]> = {}

    await Promise.all(
      accs
        .filter((a) => a.platform === 'predict')
        .map(async (a) => {
          try {
            pos[a.id] = await getPositions(a.platform, a.id)
          } catch {
            pos[a.id] = []
          }
          try {
            ord[a.id] = await getOrders(a.platform, a.id, 50)
          } catch {
            ord[a.id] = []
          }
        })
    )

    setPositions(pos)
    setOrders(ord)
  }, [])

  const loadAccounts = useCallback(async () => {
    try {
      const data = await getAccounts()
      setAccounts(data)
      await loadAccountTelemetry(data)
    } catch (err) {
      console.error('Failed to load accounts:', err)
    }
  }, [loadAccountTelemetry])

  const loadStrategies = useCallback(async () => {
    try {
      const data = await getStrategies()
      setStrategies(data)
    } catch (err) {
      console.error('Failed to load strategies:', err)
    }
  }, [])

  const loadMarkets = useCallback(async () => {
    try {
      const data = await getMarkets(undefined, 20)
      setMarkets(data)
    } catch (err) {
      console.error('Failed to load markets:', err)
    }
  }, [])

  const loadTrades = useCallback(async () => {
    try {
      const data = await getTrades(undefined, 50)
      setTrades(data)
    } catch (err) {
      console.error('Failed to load trades:', err)
    }
  }, [])

  const loadAlerts = useCallback(async () => {
    try {
      const data = await getAlerts(false, 20)
      setAlerts(data)
    } catch (err) {
      console.error('Failed to load alerts:', err)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadStats(),
      loadAccounts(),
      loadStrategies(),
      loadMarkets(),
      loadAlerts(),
      loadTrades(),
    ])
      .catch((err) => {
        console.error('Initial load failed:', err)
        setError(String(err))
      })
      .finally(() => setLoading(false))
  }, [loadStats, loadAccounts, loadStrategies, loadMarkets, loadAlerts, loadTrades])

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws'
    let ws: WebSocket | null = null

    const connect = () => {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('WS message:', message)

          if (message.type === 'trade_events' || message.type === 'fill_events') {
            loadStats()
            loadAccounts()
            loadTrades()
          } else if (message.type === 'account_events') {
            loadAccounts()
          }
        } catch (err) {
          console.error('Failed to parse WS message:', err)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...')
        setTimeout(connect, 3000)
      }

      ws.onerror = (err) => {
        console.error('WebSocket error:', err)
      }
    }

    connect()

    return () => {
      if (ws) ws.close()
    }
  }, [loadStats, loadAccounts, loadTrades])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Predict Trading System</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">
        {stats && <StatsCards stats={stats} />}

        <Tabs defaultValue="accounts" className="space-y-4">
          <TabsList>
            <TabsTrigger value="accounts">Accounts</TabsTrigger>
            <TabsTrigger value="strategies">Strategies</TabsTrigger>
            <TabsTrigger value="positions">Positions</TabsTrigger>
            <TabsTrigger value="orders">Orders</TabsTrigger>
            <TabsTrigger value="markets">Markets</TabsTrigger>
            <TabsTrigger value="trades">Trades</TabsTrigger>
            <TabsTrigger value="alerts">
              Alerts
              {alerts.filter((a) => !a.read).length > 0 && (
                <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {alerts.filter((a) => !a.read).length}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="accounts">
            <AccountList accounts={accounts} onRefresh={loadAccounts} />
          </TabsContent>

          <TabsContent value="strategies">
            <StrategyList strategies={strategies} onRefresh={loadStrategies} />
          </TabsContent>

          <TabsContent value="positions">
            <div className="space-y-4">
              {accounts
                .filter((a) => a.platform === 'predict')
                .map((a) => (
                  <div key={a.id}>
                    <div className="text-sm text-muted-foreground mb-2">{a.name}</div>
                    <PositionsList positions={(positions[a.id] || []) as any} />
                  </div>
                ))}
            </div>
          </TabsContent>

          <TabsContent value="orders">
            <div className="space-y-4">
              {accounts
                .filter((a) => a.platform === 'predict')
                .map((a) => (
                  <div key={a.id}>
                    <div className="text-sm text-muted-foreground mb-2">{a.name}</div>
                    <OrdersList orders={(orders[a.id] || []) as any} />
                  </div>
                ))}
            </div>
          </TabsContent>

          <TabsContent value="markets">
            <MarketList markets={markets} onRefresh={loadMarkets} />
          </TabsContent>

          <TabsContent value="trades">
            <TradeList trades={trades} onRefresh={loadTrades} />
          </TabsContent>

          <TabsContent value="alerts">
            <AlertList alerts={alerts} onRefresh={loadAlerts} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
