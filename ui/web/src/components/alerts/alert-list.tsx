'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { markAlertRead, markAllAlertsRead, type Alert } from '@/lib/api'
import { Bell, Check, RefreshCw } from 'lucide-react'

interface AlertListProps {
  alerts: Alert[]
  onRefresh: () => void
}

export function AlertList({ alerts, onRefresh }: AlertListProps) {
  const handleMarkRead = async (id: string) => {
    try {
      await markAlertRead(id)
      onRefresh()
    } catch (err) {
      console.error('Failed to mark alert read:', err)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await markAllAlertsRead()
      onRefresh()
    } catch (err) {
      console.error('Failed to mark all read:', err)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Alerts
        </CardTitle>
        <div className="flex gap-2">
          {alerts.some(a => !a.read) && (
            <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
              <Check className="h-4 w-4 mr-2" />
              Mark All Read
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-muted-foreground">No alerts</p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 border rounded-lg ${
                  alert.read ? 'opacity-60' : 'border-primary'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-secondary px-2 py-0.5 rounded">
                        {alert.type}
                      </span>
                      <span className="font-medium">{alert.title}</span>
                    </div>
                    {alert.message && (
                      <p className="text-sm text-muted-foreground">
                        {alert.message}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  {!alert.read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleMarkRead(alert.id)}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
