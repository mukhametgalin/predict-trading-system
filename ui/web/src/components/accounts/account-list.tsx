'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { closeAllPositions, disableAccount, updateAccount, type Account } from '@/lib/api'
import { RefreshCw } from 'lucide-react'

interface AccountListProps {
  accounts: Account[]
  onRefresh: () => void
}

export function AccountList({ accounts, onRefresh }: AccountListProps) {
  const [loading, setLoading] = useState<string | null>(null)

  const handleCloseAll = async (account: Account, confirm: boolean) => {
    if (confirm) {
      const ok = window.confirm(
        `CONFIRM: Close ALL positions for ${account.name}?\n\nThis will submit MARKET SELL orders with 100bps slippage.`
      )
      if (!ok) return
    }

    setLoading(account.id)
    try {
      const result = await closeAllPositions(account.platform, account.id, confirm, 100)
      if (result.status === 'dry_run' || result.status === 'no_positions') {
        alert(`${result.message}\n\nPlan:\n${JSON.stringify(result.plan || [], null, 2)}`)
      } else {
        alert(`Close-all result: ${result.message}\n\nResults: ${result.results?.length || 0}, Errors: ${result.errors?.length || 0}`)
      }
      onRefresh()
    } catch (err) {
      console.error('Failed to close positions:', err)
      alert(`Error: ${err}`)
    } finally {
      setLoading(null)
    }
  }

  const handleDisable = async (account: Account) => {
    const ok = window.confirm(
      `Disable ${account.name}?\n\nThis will:\n- Disable new trading on this account (kill-switch)\n- Remove it from strategies\n\nNOTE: Exchange-side position closing is not automated yet.`
    )
    if (!ok) return

    setLoading(account.id)
    try {
      await disableAccount(account.platform, account.id)
      onRefresh()
    } catch (err) {
      console.error('Failed to disable account:', err)
    } finally {
      setLoading(null)
    }
  }

  const handleToggle = async (account: Account) => {
    setLoading(account.id)
    try {
      await updateAccount(account.platform, account.id, { active: !account.active })
      onRefresh()
    } catch (err) {
      console.error('Failed to toggle account:', err)
    } finally {
      setLoading(null)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Accounts</CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {accounts.length === 0 ? (
          <p className="text-muted-foreground">No accounts found</p>
        ) : (
          <div className="space-y-4">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{account.name}</span>
                    <span className="text-xs bg-secondary px-2 py-0.5 rounded">
                      {account.platform}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground font-mono">
                    {account.address.slice(0, 10)}...{account.address.slice(-6)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-right">
                    <p className="text-sm">
                      {account.positions_count || 0} positions
                    </p>
                    <p className="text-xs text-muted-foreground">
                      PnL: ${(account.pnl_24h || 0).toFixed(2)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={loading === account.id}
                    onClick={() => handleCloseAll(account, false)}
                  >
                    Close All (dry)
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={loading === account.id}
                    onClick={() => handleCloseAll(account, true)}
                  >
                    Close All
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={loading === account.id || !account.active}
                    onClick={() => handleDisable(account)}
                  >
                    Disable
                  </Button>
                  <Switch
                    checked={account.active}
                    disabled={loading === account.id}
                    onCheckedChange={() => handleToggle(account)}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
