"use client"

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { healthAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading";
import { Activity, Database, Server, Zap, RefreshCw, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { HealthResponse } from "@/lib/types/api";

export default function HealthPage() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(30); // seconds

  // System health query
  const { data: health, isLoading, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: healthAPI.system,
    refetchInterval: autoRefresh ? refreshInterval * 1000 : false,
  });

  // Ingestion health query
  const { data: ingestionHealth } = useQuery({
    queryKey: ["ingestion-health"],
    queryFn: healthAPI.ingestion,
    refetchInterval: autoRefresh ? refreshInterval * 1000 : false,
  });

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case "healthy":
      case "connected":
      case "operational":
        return "bg-neon-green";
      case "degraded":
      case "slow":
        return "bg-yellow-500";
      case "unhealthy":
      case "disconnected":
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case "healthy":
      case "connected":
      case "operational":
        return <CheckCircle className="h-5 w-5 text-neon-green" />;
      case "degraded":
      case "slow":
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case "unhealthy":
      case "disconnected":
      case "error":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading health status..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
            System Health
          </h1>
          <p className="text-muted-foreground mt-2">
            Monitor platform health and performance metrics
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>

          <div className="flex items-center space-x-2">
            <span className="text-sm">Auto-refresh</span>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                autoRefresh ? "bg-neon-cyan" : "bg-gray-600"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  autoRefresh ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Overall Status */}
      {health && (
        <Card className={`border-2 ${health.status === "healthy" ? "border-neon-green/50" : "border-yellow-500/50"}`}>
          <CardContent className="p-6">
            <div className="flex items-center space-x-4">
              {getStatusIcon(health.status)}
              <div className="flex-1">
                <p className="text-2xl font-bold capitalize">{health.status}</p>
                <p className="text-sm text-muted-foreground">Overall System Status</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">Last Updated</p>
                <p className="text-sm font-mono">{new Date(health.timestamp).toLocaleTimeString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Service Status Grid */}
      {health?.services && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(health.services).map(([service, status]: [string, any]) => (
            <Card key={service} className="comic-panel">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    {service.toLowerCase().includes("postgres") && <Database className="h-5 w-5 text-neon-cyan" />}
                    {service.toLowerCase().includes("chroma") && <Server className="h-5 w-5 text-neon-magenta" />}
                    {service.toLowerCase().includes("llm") && <Zap className="h-5 w-5 text-neon-purple" />}
                    {!service.toLowerCase().includes("postgres") &&
                      !service.toLowerCase().includes("chroma") &&
                      !service.toLowerCase().includes("llm") && <Activity className="h-5 w-5 text-neon-green" />}
                    <h3 className="font-semibold">{service}</h3>
                  </div>
                  <div className={`w-3 h-3 rounded-full animate-pulse ${getStatusColor(status.status)}`}></div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Status</span>
                    <span className="font-medium capitalize">{status.status}</span>
                  </div>

                  {status.response_time !== undefined && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Response Time</span>
                      <span className="font-mono text-neon-cyan">{(status.response_time * 1000).toFixed(0)}ms</span>
                    </div>
                  )}

                  {status.version && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Version</span>
                      <span className="font-mono text-xs">{status.version}</span>
                    </div>
                  )}

                  {status.details && (
                    <div className="text-xs text-muted-foreground mt-2">
                      {typeof status.details === "string" ? status.details : JSON.stringify(status.details)}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Ingestion Health */}
      {ingestionHealth && (
        <Card>
          <CardHeader>
            <CardTitle>Ingestion Pipeline Health</CardTitle>
            <CardDescription>Document processing statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Total Documents</p>
                <p className="text-2xl font-bold text-neon-cyan">{ingestionHealth.total_documents || 0}</p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground mb-1">Success Rate</p>
                <p className="text-2xl font-bold text-neon-green">
                  {ingestionHealth.success_rate ? `${(ingestionHealth.success_rate * 100).toFixed(1)}%` : "N/A"}
                </p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground mb-1">Total Chunks</p>
                <p className="text-2xl font-bold text-neon-magenta">{ingestionHealth.total_chunks || 0}</p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground mb-1">Avg Time</p>
                <p className="text-2xl font-bold text-neon-purple">
                  {ingestionHealth.avg_processing_time ? `${ingestionHealth.avg_processing_time.toFixed(1)}s` : "N/A"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Telemetry Charts */}
      {health?.metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Response Times */}
          {health.metrics.response_times && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Average Response Times</CardTitle>
                <CardDescription>Real-time metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={health.metrics.response_times}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" />
                    <XAxis dataKey="time" stroke="#00F0FF" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#00F0FF" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0A0A0F",
                        border: "1px solid #00F0FF",
                        borderRadius: "8px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="avg"
                      stroke="#00F0FF"
                      strokeWidth={2}
                      dot={{ fill: "#00F0FF", r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Request Volume */}
          {health.metrics.request_volume && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Request Volume by Endpoint</CardTitle>
                <CardDescription>Last 24 hours</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={health.metrics.request_volume}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" />
                    <XAxis dataKey="endpoint" stroke="#00F0FF" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={60} />
                    <YAxis stroke="#00F0FF" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0A0A0F",
                        border: "1px solid #FF00FF",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="count" fill="#FF00FF" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Auto-refresh Settings */}
      {autoRefresh && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium">Refresh Interval:</label>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="flex-1 accent-neon-cyan"
              />
              <span className="text-sm font-mono bg-neon-cyan/20 px-3 py-1 rounded text-neon-cyan min-w-[4rem] text-center">
                {refreshInterval}s
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
