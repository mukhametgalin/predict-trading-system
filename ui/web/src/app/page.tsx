'use client'

import { useEffect, useState, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StatsCards } from '@/components/dashboard/stats-cards'
import { AccountList } from '@/components/accounts/account-list'
import { StrategyList } from '@/components/strategies/strategy-list'
import { MarketList } from '@/components/markets/market-list'
import { AlertList } from '@/components/alerts/alert-list'
import {
  getStats,
  getAccounts,
  getStrategies,
  getMarkets,
  getAlerts,
  type DashboardStats,
  type Account,
  type Strategy,
  type Market,
  type Alert,
} from '@/lib/api'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [markets, setMarkets] = useState<Market[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const data = await getStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [])

  const loadAccounts = useCallback(async () => {
    try {
      const data = await getAccounts()
      setAccounts(data)
    } catch (err) {
      console.error('Failed to load accounts:', err)
    }
  }, [])

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

  const loadAlerts = useCallback(async () => {
    try {
      const data = await getAlerts(false, 20)
      setAlerts(data)
    } catch (err) {
      console.error('Failed to load alerts:', err)
    }
  }, [])

  useEffect(() => {
    loadStats()
    loadAccounts()
    loadStrategies()
    loadMarkets()
    loadAlerts()
  }, [loadStats, loadAccounts, loadStrategies, loadMarkets, loadAlerts])

  // WebSocket connection for real-time updates
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
          
          // Refresh relevant data on events
          if (message.type === 'trade_events' || message.type === 'fill_events') {
            loadStats()
            loadAccounts()
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
      if (ws) {
        ws.close()
      }
    }
  }, [loadStats, loadAccounts])

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
            <TabsTrigger value="markets">Markets</TabsTrigger>
            <TabsTrigger value="alerts">
              Alerts
              {alerts.filter(a => !a.read).length > 0 && (
                <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {alerts.filter(a => !a.read).length}
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

          <TabsContent value="markets">
            <MarketList markets={markets} onRefresh={loadMarkets} />
          </TabsContent>

          <TabsContent value="alerts">
            <AlertList alerts={alerts} onRefresh={loadAlerts} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
