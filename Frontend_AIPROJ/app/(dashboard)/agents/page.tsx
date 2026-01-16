"use client"

import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentAPI, ragAPI, mlAPI, documentsAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { Bot, MessageSquare, Brain, Send, Loader2, Check, X, Zap, FileText, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  metadata?: {
    user_message?: string;
    iterations?: number;
    trace?: Array<{
      iteration: number;
      tool: string;
      arguments?: any;
      result?: string;
    }>;
  };
}

interface ToolCall {
  tool: string;
  status: "running" | "success" | "error";
  result?: any;
  error?: string;
}

// Generate unique message ID
let messageCounter = 0;
const generateMessageId = () => {
  messageCounter++;
  return `msg-${Date.now()}-${messageCounter}`;
};

export default function AgentsPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "👋 Hi! I'm your AI Assistant. I can help you with:\n\n• Document Q&A - Ask questions about your documents\n• Data Analysis - Analyze CSV files and get insights\n• ML Predictions - Make predictions using trained models\n• Research - Find information across multiple documents\n\nWhat would you like to do?",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Fix hydration issue - only render timestamps on client
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Fetch documents for context
  const { data: documentsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsAPI.list({ limit: 100, offset: 0 }),
    refetchInterval: 10000, // Refresh every 10s
  });

  // Fetch available tools
  const { data: toolsData } = useQuery({
    queryKey: ["agent-tools"],
    queryFn: () => agentAPI.tools(),
    refetchInterval: 30000,
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Agent execution mutation
  const agentMutation = useMutation({
    mutationFn: async (task: string) => {
      return await agentAPI.run(task);
    },
    onSuccess: (data) => {
      // Format the response in a user-friendly way
      const answer = (data as any).answer || (data as any).result || "Task completed successfully!";
      const userMessage = (data as any).user_message || "";
      
      const assistantMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: answer,
        timestamp: new Date(),
        metadata: {
          user_message: userMessage,
          iterations: (data as any).iterations || 0,
          trace: (data as any).trace || [],
        },
        toolCalls: (data as any).trace?.map((step: any) => ({
          tool: step.tool || "unknown",
          status: "success" as const,
          result: typeof step.result === 'string' ? step.result : JSON.stringify(step.result),
        })) || [],
      };
      setMessages(prev => [...prev, assistantMessage]);
      setIsProcessing(false);
    },
    onError: (error: any) => {
      const errorMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: `❌ Error: ${error.response?.data?.detail || error.message || "Failed to execute task"}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsProcessing(false);
      toast({
        title: "Agent Error",
        description: error.response?.data?.detail || "Failed to execute task",
        variant: "destructive",
      });
    },
  });

  // Handle intelligent routing based on user input
  const handleSendMessage = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = {
      id: generateMessageId(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsProcessing(true);

    const lowerInput = input.toLowerCase();

    try {
      // Intelligent routing based on intent
      if (lowerInput.includes("document") || lowerInput.includes("what") || lowerInput.includes("who") || 
          lowerInput.includes("when") || lowerInput.includes("find") || lowerInput.includes("search")) {
        // Route to RAG Q&A
        const response = await ragAPI.answer({ query: input, top_k: 5 });
        const assistantMessage: Message = {
          id: generateMessageId(),
          role: "assistant",
          content: response.answer,
          timestamp: new Date(),
          toolCalls: [{
            tool: "Document Q&A",
            status: "success",
            result: `Used ${response.used_chunks} document chunks`,
          }],
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else if (lowerInput.includes("analyze") || lowerInput.includes("csv") || lowerInput.includes("data") ||
                 lowerInput.includes("insight") || lowerInput.includes("statistics")) {
        // Route to analytics
        const docs = documentsData?.documents?.filter(d => d.format === 'csv') || [];
        if (docs.length === 0) {
          throw new Error("No CSV documents found. Please upload a CSV file first.");
        }
        // For demo, use first CSV
        const assistantMessage: Message = {
          id: generateMessageId(),
          role: "assistant",
          content: `I found ${docs.length} CSV file(s). To analyze them, please go to the Document Intelligence page and use the Analytics tab, or upload a CSV file first.`,
          timestamp: new Date(),
          toolCalls: [{
            tool: "CSV Analytics",
            status: "success",
            result: `Found ${docs.length} CSV files`,
          }],
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else if (lowerInput.includes("predict") || lowerInput.includes("model") || lowerInput.includes("ml")) {
        // Route to ML
        const assistantMessage: Message = {
          id: generateMessageId(),
          role: "assistant",
          content: "To make ML predictions, please go to the ML page and input your feature values. The model supports Iris dataset predictions.",
          timestamp: new Date(),
          toolCalls: [{
            tool: "ML Prediction",
            status: "success",
          }],
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        // Use general agent for other tasks
        agentMutation.mutate(input);
        return; // Let mutation handle the response
      }
      setIsProcessing(false);
    } catch (error: any) {
      const errorMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: `❌ ${error.message || "Failed to process your request"}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-magenta bg-clip-text text-transparent flex items-center gap-2">
            <Bot className="h-8 w-8" />
            AI Agents
          </h1>
          <p className="text-muted-foreground mt-2">
            Intelligent agents that leverage Document Q&A, ML, and Analytics
          </p>
        </div>
        <div className="flex items-center gap-6">
          {documentsData && (
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-neon-cyan"></div>
                <span className="text-muted-foreground">{documentsData.documents?.length || 0} Documents</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-neon-purple"></div>
                <span className="text-muted-foreground">{documentsData.documents?.filter(d => d.format === 'csv').length || 0} CSV Files</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-neon-magenta"></div>
                <span className="text-muted-foreground">{toolsData?.tools?.length || 0} Tools</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Pre-built Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-shrink-0">
        <Card className="cursor-pointer hover:border-neon-cyan transition-all" onClick={() => setInput("Analyze all my documents and give me key insights")}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-neon-cyan" />
              Document Analyst
            </CardTitle>
            <CardDescription>
              Analyzes documents and extracts key insights
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="cursor-pointer hover:border-neon-purple transition-all" onClick={() => setInput("What data patterns can you find in my CSV files?")}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-neon-purple" />
              Data Scientist
            </CardTitle>
            <CardDescription>
              Analyzes CSV data and finds patterns
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="cursor-pointer hover:border-neon-magenta transition-all" onClick={() => setInput("Help me find information about revenue in my documents")}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-neon-magenta" />
              Research Assistant
            </CardTitle>
            <CardDescription>
              Searches and synthesizes information
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Chat Interface */}
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Chat Interface
          </CardTitle>
          <CardDescription>
            Natural language interaction with AI agents
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-base-bg rounded-lg">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-fade-in",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg p-4",
                    message.role === "user"
                      ? "bg-neon-cyan/20 border border-neon-cyan/30"
                      : "bg-base-surface border border-neon-purple/30"
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="flex items-center gap-2 mb-2">
                      <Bot className="h-4 w-4 text-neon-purple" />
                      <span className="text-xs text-neon-purple font-medium">AI Assistant</span>
                    </div>
                  )}
                  
                  {/* User Message (if present) */}
                  {message.metadata?.user_message && (
                    <div className="mb-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded text-xs text-yellow-400">
                      <span className="font-medium">ℹ️ Note:</span> {message.metadata.user_message}
                    </div>
                  )}
                  
                  {/* Main Answer */}
                  <div className="prose prose-sm max-w-none">
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                  </div>
                  
                  {/* Tool Execution Steps */}
                  {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-neon-purple/20 space-y-3">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                        <Zap className="h-3 w-3" />
                        Execution Steps ({message.metadata?.iterations || message.toolCalls.length})
                      </p>
                      {message.toolCalls.map((tool, idx) => (
                        <div key={idx} className="bg-base-bg/50 rounded p-2 space-y-1">
                          <div className="flex items-center gap-2 text-xs">
                            {tool.status === "success" ? (
                              <Check className="h-3 w-3 text-green-400 flex-shrink-0" />
                            ) : tool.status === "error" ? (
                              <X className="h-3 w-3 text-red-400 flex-shrink-0" />
                            ) : (
                              <Loader2 className="h-3 w-3 animate-spin text-neon-cyan flex-shrink-0" />
                            )}
                            <span className="text-neon-cyan font-medium">Step {idx + 1}:</span>
                            <span className="text-white">{tool.tool}</span>
                          </div>
                          {tool.result && tool.result.length < 200 && (
                            <p className="text-xs text-muted-foreground pl-5 italic">
                              {tool.result}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {isMounted && (
                    <p className="text-xs text-muted-foreground mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex gap-3 animate-fade-in">
                <div className="bg-base-surface border border-neon-purple/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Loader2 className="h-4 w-4 text-neon-purple animate-spin" />
                    <span className="text-xs text-neon-purple font-medium">Thinking...</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-neon-purple rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-neon-purple rounded-full animate-pulse" style={{ animationDelay: "0.2s" }}></div>
                    <div className="w-2 h-2 bg-neon-purple rounded-full animate-pulse" style={{ animationDelay: "0.4s" }}></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2 flex-shrink-0">
            <Input
              placeholder="Ask me anything... (e.g., 'What is the revenue in my documents?')"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isProcessing}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!input.trim() || isProcessing}
              size="icon"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
