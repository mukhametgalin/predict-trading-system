const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  
  return res.json()
}

// Dashboard
export async function getStats() {
  return request<DashboardStats>('/dashboard/stats')
}

// Accounts
export async function getAccounts(platform?: string) {
  const params = platform ? `?platform=${platform}` : ''
  return request<Account[]>(`/accounts${params}`)
}

export async function getAccount(platform: string, id: string) {
  return request<AccountDetail>(`/accounts/${platform}/${id}`)
}

export async function createAccount(data: CreateAccountData) {
  return request<Account>('/accounts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAccount(platform: string, id: string, data: UpdateAccountData) {
  return request<Account>(`/accounts/${platform}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAccount(platform: string, id: string) {
  return request(`/accounts/${platform}/${id}`, { method: 'DELETE' })
}

export async function disableAccount(platform: string, id: string) {
  return request<Account>(`/accounts/${platform}/${id}/disable`, { method: 'POST' })
}

// Trading
export async function executeTrade(data: TradeData) {
  return request<TradeResult>('/trade', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getTrades(accountId?: string, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (accountId) params.set('account_id', accountId)
  return request<TradeSummary[]>(`/trades?${params}`)
}

export async function getOrders(platform: string, accountId: string, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) })
  return request<any[]>(`/orders/${platform}/${accountId}?${params}`)
}

export async function getPositions(platform: string, accountId: string) {
  return request<Position[]>(`/positions/${platform}/${accountId}`)
}

// Markets
export async function getMarkets(platform?: string, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (platform) params.set('platform', platform)
  return request<Market[]>(`/markets?${params}`)
}

export async function syncMarkets(limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) })
  return request<{ inserted: number }>(`/markets/sync?${params}`, {
    method: 'POST',
  })
}

// Strategies
export async function getStrategies() {
  return request<Strategy[]>('/strategies')
}

export async function createStrategy(data: CreateStrategyData) {
  return request<Strategy>('/strategies', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStrategy(id: string, data: UpdateStrategyData) {
  return request<Strategy>(`/strategies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStrategy(id: string) {
  return request(`/strategies/${id}`, { method: 'DELETE' })
}

// Alerts
export async function getAlerts(unreadOnly = false, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (unreadOnly) params.set('unread_only', 'true')
  return request<Alert[]>(`/alerts?${params}`)
}

export async function markAlertRead(id: string) {
  return request(`/alerts/${id}/read`, { method: 'POST' })
}

export async function markAllAlertsRead() {
  return request('/alerts/read-all', { method: 'POST' })
}

// Types
export interface DashboardStats {
  total_accounts: number
  active_accounts: number
  total_trades_24h: number
  total_pnl_24h: number
  active_strategies: number
  pending_alerts: number
}

export interface Account {
  id: string
  name: string
  platform: string
  address: string
  active: boolean
  balance?: number
  positions_count?: number
  pnl_24h?: number
}

export interface AccountDetail extends Account {
  tags: string[]
  notes?: string
  created_at: string
  positions: Position[]
  recent_trades: Trade[]
}

export interface CreateAccountData {
  platform: string
  name: string
  private_key: string
  api_key?: string
  proxy_url?: string
  tags?: string[]
  notes?: string
}

export interface UpdateAccountData {
  active?: boolean
  tags?: string[]
  notes?: string
  proxy_url?: string
}

export interface Position {
  account_id: string
  market_id: string
  outcome_id: string
  side: string
  shares: number
  avg_price: number
  current_value?: number
  pnl?: number
}

export interface Trade {
  trade_id: string
  account_id: string
  market_id: string
  side: string
  price: number
  shares: number
  status: string
  created_at: string
}

export interface TradeSummary {
  id: string
  account_id: string
  account_name: string
  market_id: string
  outcome_id: string
  side: string
  price: number
  shares: number
  order_hash?: string
  status: string
  error?: string
  created_at: string
  filled_at?: string
}

export interface TradeData {
  account_id: string
  market_id: string
  side: 'yes' | 'no'
  price: number
  shares: number
  confirm: boolean
}

export interface TradeResult {
  trade_id: string
  status: string
  message: string
  order_hash?: string
}

export interface Market {
  market_id: string
  platform: string
  question: string
  category: string
  yes_price: number
  no_price: number
  volume_24h: number
  liquidity: number
}

export interface Strategy {
  id: string
  name: string
  type: string
  config: Record<string, unknown>
  enabled: boolean
  created_at: string
  recent_logs?: StrategyLog[]
}

export interface CreateStrategyData {
  name: string
  type: string
  config?: Record<string, unknown>
  enabled?: boolean
}

export interface UpdateStrategyData {
  name?: string
  config?: Record<string, unknown>
  enabled?: boolean
}

export interface StrategyLog {
  id: string
  level: string
  message: string
  data?: Record<string, unknown>
  created_at: string
}

export interface Alert {
  id: string
  type: string
  title: string
  message?: string
  data?: Record<string, unknown>
  read: boolean
  created_at: string
}
