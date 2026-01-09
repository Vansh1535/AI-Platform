"use client"

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { Sparkles, Play, Zap, CheckCircle, XCircle, Loader2 } from "lucide-react";
import type { AgentResponse } from "@/lib/types/api";

export default function AgentPage() {
  const [prompt, setPrompt] = useState("");
  const [maxIterations, setMaxIterations] = useState(5);
  const [verbose, setVerbose] = useState(true);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const { toast } = useToast();

  // Fetch available tools
  const { data: toolsData } = useQuery({
    queryKey: ["agent-tools"],
    queryFn: agentAPI.getTools,
  });

  // Run agent mutation
  const runMutation = useMutation({
    mutationFn: (data: { prompt: string; max_iterations?: number; verbose?: boolean }) =>
      agentAPI.run(data.prompt, data.max_iterations, data.verbose),
    onSuccess: (data: AgentResponse) => {
      setResult(data);
      toast({
        title: "Agent Complete",
        description: data.success ? "Task completed successfully" : "Task failed",
        variant: data.success ? "success" : "destructive",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Agent Failed",
        description: error.response?.data?.detail || "Failed to run agent",
        variant: "destructive",
      });
    },
  });

  const handleRun = () => {
    if (!prompt.trim()) {
      toast({
        title: "Empty Prompt",
        description: "Please enter a task for the agent",
        variant: "destructive",
      });
      return;
    }
    setResult(null);
    runMutation.mutate({ prompt, max_iterations: maxIterations, verbose });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          AI Agent Orchestrator
        </h1>
        <p className="text-muted-foreground mt-2">
          Multi-step AI agent with tool use and reasoning
        </p>
      </div>

      {/* Available Tools */}
      {toolsData && toolsData.tools && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Available Tools</CardTitle>
            <CardDescription>The agent can use these tools to complete tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {toolsData.tools.map((tool: any, idx: number) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 rounded-full bg-neon-cyan/20 border border-neon-cyan/50 text-sm"
                >
                  <Zap className="inline h-3 w-3 mr-1" />
                  {tool.name}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Task</CardTitle>
          <CardDescription>Describe what you want the agent to do</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Task Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Example: Search my documents for information about revenue growth and summarize the findings..."
              rows={4}
              className="w-full px-4 py-3 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none resize-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Max Iterations</label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(Number(e.target.value))}
                  className="flex-1 accent-neon-cyan"
                />
                <span className="text-sm font-mono bg-neon-cyan/20 px-3 py-1 rounded text-neon-cyan min-w-[3rem] text-center">
                  {maxIterations}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Maximum reasoning steps the agent can take
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Verbose Mode</label>
              <div className="flex items-center space-x-2 mt-2">
                <button
                  onClick={() => setVerbose(!verbose)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    verbose ? "bg-neon-cyan" : "bg-gray-600"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      verbose ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
                <span className="text-sm">Show reasoning trace</span>
              </div>
            </div>
          </div>

          <Button
            onClick={handleRun}
            disabled={runMutation.isPending}
            className="w-full"
          >
            {runMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Agent Running...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Agent
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Execution Flow */}
      {runMutation.isPending && (
        <Card className="border-neon-cyan/50">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <Loader2 className="h-6 w-6 text-neon-cyan animate-spin" />
              <div>
                <p className="font-medium">Agent is thinking...</p>
                <p className="text-sm text-muted-foreground">Processing your request</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Result Display */}
      {result && (
        <>
          {/* Final Answer */}
          <Card className={result.success ? "border-neon-green/50" : "border-red-500/50"}>
            <CardHeader>
              <div className="flex items-center space-x-2">
                {result.success ? (
                  <CheckCircle className="h-5 w-5 text-neon-green" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <CardTitle>{result.success ? "Task Complete" : "Task Failed"}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold text-neon-cyan mb-2">Response</h4>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.response}</p>
              </div>

              {result.metadata && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-neon-cyan/30">
                  <div>
                    <p className="text-xs text-muted-foreground">Iterations</p>
                    <p className="text-lg font-bold text-neon-cyan">{result.metadata.iterations}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Duration</p>
                    <p className="text-lg font-bold text-neon-magenta">
                      {result.metadata.execution_time?.toFixed(2)}s
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Tools Used</p>
                    <p className="text-lg font-bold text-neon-purple">
                      {result.metadata.tools_used?.length || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-mono text-muted-foreground">
                      {result.metadata.model_name || "N/A"}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Execution Trace */}
          {verbose && result.trace && result.trace.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Execution Trace</CardTitle>
                <CardDescription>Step-by-step agent reasoning</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {result.trace.map((step: any, idx: number) => (
                  <div key={idx} className="comic-panel p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-neon-cyan">
                        Iteration {step.iteration}
                      </h4>
                      <span className="text-xs text-muted-foreground">
                        {step.timestamp}
                      </span>
                    </div>

                    {step.tool_name && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Tool Used</p>
                        <div className="inline-flex items-center space-x-2 px-2 py-1 rounded bg-neon-cyan/20 border border-neon-cyan/50">
                          <Zap className="h-3 w-3 text-neon-cyan" />
                          <span className="text-sm font-medium">{step.tool_name}</span>
                        </div>
                      </div>
                    )}

                    {step.tool_input && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Input</p>
                        <pre className="text-xs bg-base-bg p-2 rounded overflow-x-auto">
                          {typeof step.tool_input === "string"
                            ? step.tool_input
                            : JSON.stringify(step.tool_input, null, 2)}
                        </pre>
                      </div>
                    )}

                    {step.tool_output && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Output</p>
                        <p className="text-sm bg-base-bg p-2 rounded">{step.tool_output}</p>
                      </div>
                    )}

                    {step.reasoning && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Reasoning</p>
                        <p className="text-sm italic text-neon-magenta">{step.reasoning}</p>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
