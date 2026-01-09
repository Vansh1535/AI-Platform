"use client"

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { documentsAPI, analyticsAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading";
import { useToast } from "@/components/ui/use-toast";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { BarChart3, TrendingUp, Database, Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import type { Document, CSVInsights } from "@/lib/types/api";

export default function AnalyticsPage() {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [useLLM, setUseLLM] = useState(true);
  const [showInsights, setShowInsights] = useState(false);
  const { toast } = useToast();

  // Fetch CSV documents
  const { data: docsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsAPI.list({ limit: 100, offset: 0 }),
  });

  const csvDocs = docsData?.documents.filter((doc: Document) => doc.format === "csv") || [];

  // Fetch analytics
  const { data: analytics, isLoading, error } = useQuery({
    queryKey: ["analytics", selectedDocId, useLLM],
    queryFn: () => analyticsAPI.csvInsights(selectedDocId!, useLLM),
    enabled: !!selectedDocId,
    retry: 1,
    onError: (err: any) => {
      toast({
        title: "Analytics Error",
        description: err.response?.data?.detail || "Failed to fetch analytics",
        variant: "destructive",
      });
    },
  });

  const handleDocChange = (docId: string) => {
    setSelectedDocId(docId);
    setShowInsights(false);
  };

  if (csvDocs.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card>
          <CardContent className="p-12 text-center">
            <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">No CSV files found</p>
            <p className="text-sm text-muted-foreground mt-2">Upload a CSV file to view analytics</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          CSV Analytics
        </h1>
        <p className="text-muted-foreground mt-2">
          Automated data profiling with AI-powered insights
        </p>
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Select CSV File</label>
              <select
                value={selectedDocId || ""}
                onChange={(e) => handleDocChange(e.target.value)}
                className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
              >
                <option value="">Choose a file...</option>
                {csvDocs.map((doc: Document) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Enable LLM Insights</label>
              <button
                onClick={() => setUseLLM(!useLLM)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  useLLM ? "bg-neon-cyan" : "bg-gray-600"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    useLLM ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analytics Display */}
      {!selectedDocId ? (
        <Card>
          <CardContent className="p-12 text-center">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">Select a CSV file to view analytics</p>
          </CardContent>
        </Card>
      ) : isLoading ? (
        <LoadingState message="Analyzing CSV data..." />
      ) : error ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-red-400">Error loading analytics. Make sure backend is running.</p>
          </CardContent>
        </Card>
      ) : analytics ? (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="comic-panel">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">Rows</p>
                <p className="text-2xl font-bold text-neon-cyan">{analytics.basic_stats.row_count.toLocaleString()}</p>
              </CardContent>
            </Card>
            
            <Card className="comic-panel">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">Columns</p>
                <p className="text-2xl font-bold text-neon-magenta">{analytics.basic_stats.column_count}</p>
              </CardContent>
            </Card>
            
            <Card className="comic-panel">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">Null Values</p>
                <p className="text-2xl font-bold text-neon-purple">{analytics.basic_stats.null_count.toLocaleString()}</p>
              </CardContent>
            </Card>
            
            <Card className="comic-panel">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">Duplicates</p>
                <p className="text-2xl font-bold text-neon-pink">{analytics.basic_stats.duplicate_rows}</p>
              </CardContent>
            </Card>
          </div>

          {/* Column Statistics */}
          {analytics.column_stats && analytics.column_stats.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Column Statistics</CardTitle>
                <CardDescription>Statistical summary of numeric columns</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b border-neon-cyan/30">
                      <tr>
                        <th className="text-left p-3 font-medium text-neon-cyan">Column</th>
                        <th className="text-left p-3 font-medium text-neon-cyan">Mean</th>
                        <th className="text-left p-3 font-medium text-neon-cyan">Median</th>
                        <th className="text-left p-3 font-medium text-neon-cyan">Std Dev</th>
                        <th className="text-left p-3 font-medium text-neon-cyan">Min</th>
                        <th className="text-left p-3 font-medium text-neon-cyan">Max</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.column_stats.map((col: any, idx: number) => (
                        <tr key={idx} className="border-b border-neon-cyan/10">
                          <td className="p-3 font-medium">{col.column_name}</td>
                          <td className="p-3">{col.mean?.toFixed(2) || "-"}</td>
                          <td className="p-3">{col.median?.toFixed(2) || "-"}</td>
                          <td className="p-3">{col.std?.toFixed(2) || "-"}</td>
                          <td className="p-3">{col.min?.toFixed(2) || "-"}</td>
                          <td className="p-3">{col.max?.toFixed(2) || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Data Quality */}
          {analytics.quality && (
            <Card>
              <CardHeader>
                <CardTitle>Data Quality</CardTitle>
                <CardDescription>Overall data health indicators</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">Completeness</span>
                    <span className="text-sm font-mono text-neon-cyan">{(analytics.quality.completeness * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-base-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-neon-cyan"
                      style={{ width: `${analytics.quality.completeness * 100}%` }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm">Uniqueness</span>
                    <span className="text-sm font-mono text-neon-magenta">{(analytics.quality.uniqueness * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-base-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-neon-magenta"
                      style={{ width: `${analytics.quality.uniqueness * 100}%` }}
                    ></div>
                  </div>
                </div>

                {analytics.quality.outlier_percentage !== undefined && (
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm">Outliers</span>
                      <span className="text-sm font-mono text-neon-purple">{analytics.quality.outlier_percentage.toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-base-bg rounded-full overflow-hidden">
                      <div
                        className="h-full bg-neon-purple"
                        style={{ width: `${Math.min(analytics.quality.outlier_percentage, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Correlations Chart */}
          {analytics.correlations && analytics.correlations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Column Correlations</CardTitle>
                <CardDescription>Relationships between numeric columns</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analytics.correlations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" />
                    <XAxis dataKey="pair" stroke="#00F0FF" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#00F0FF" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0A0A0F",
                        border: "1px solid #00F0FF",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="correlation" radius={[8, 8, 0, 0]}>
                      {analytics.correlations.map((entry: any, index: number) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={Math.abs(entry.correlation) > 0.7 ? "#39FF14" : "#00F0FF"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* LLM Insights */}
          {useLLM && analytics.llm_insights && (
            <Card className="border-neon-magenta/50">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-5 w-5 text-neon-magenta" />
                    <CardTitle>AI-Powered Insights</CardTitle>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowInsights(!showInsights)}
                  >
                    {showInsights ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>
                <CardDescription>Generated by LLM analysis</CardDescription>
              </CardHeader>
              
              {showInsights && (
                <CardContent className="space-y-4">
                  {analytics.llm_insights.summary && (
                    <div>
                      <h4 className="text-sm font-semibold text-neon-cyan mb-2">Summary</h4>
                      <p className="text-sm leading-relaxed">{analytics.llm_insights.summary}</p>
                    </div>
                  )}

                  {analytics.llm_insights.key_findings && analytics.llm_insights.key_findings.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-neon-cyan mb-2">Key Findings</h4>
                      <ul className="space-y-2">
                        {analytics.llm_insights.key_findings.map((finding: string, idx: number) => (
                          <li key={idx} className="flex items-start space-x-2">
                            <TrendingUp className="h-4 w-4 text-neon-magenta mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {analytics.llm_insights.recommendations && analytics.llm_insights.recommendations.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-neon-cyan mb-2">Recommendations</h4>
                      <ul className="space-y-2">
                        {analytics.llm_insights.recommendations.map((rec: string, idx: number) => (
                          <li key={idx} className="flex items-start space-x-2">
                            <Sparkles className="h-4 w-4 text-neon-green mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
