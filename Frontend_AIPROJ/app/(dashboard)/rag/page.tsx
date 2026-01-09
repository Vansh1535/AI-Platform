"use client"

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ragAPI } from "@/lib/api/endpoints";
import { useChatStore } from "@/lib/store/chat";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Search, MessageSquare, Send, Sparkles, FileText } from "lucide-react";
import { getConfidenceColor } from "@/lib/utils";
import type { SearchResult, AnswerResponse } from "@/lib/types/api";

export default function RAGPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const { toast } = useToast();
  const { messages, addMessage } = useChatStore();

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: (data: { query: string; top_k: number }) => ragAPI.search(data.query, data.top_k),
    onSuccess: (data) => {
      setSearchResults(data?.results || []);
      toast({
        title: "Search Complete",
        description: `Found ${data?.results?.length || 0} relevant chunks`,
        variant: "success",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Search Failed",
        description: error.response?.data?.detail || "Failed to search documents",
        variant: "destructive",
      });
    },
  });

  // Answer mutation
  const answerMutation = useMutation({
    mutationFn: (data: { query: string; top_k: number }) => ragAPI.answer(data.query, data.top_k),
    onSuccess: (data: AnswerResponse) => {
      addMessage({
        role: "user",
        content: query,
        timestamp: new Date().toISOString(),
      });
      addMessage({
        role: "assistant",
        content: data.answer,
        timestamp: new Date().toISOString(),
        metadata: {
          citations: data.citations,
          model: data.metadata?.provider,
        },
      });
      setQuery("");
    },
    onError: (error: any) => {
      toast({
        title: "Query Failed",
        description: error.response?.data?.detail || "Failed to get answer",
        variant: "destructive",
      });
    },
  });

  const handleSearch = () => {
    if (!query.trim()) {
      toast({
        title: "Empty Query",
        description: "Please enter a search query",
        variant: "destructive",
      });
      return;
    }
    searchMutation.mutate({ query, top_k: topK });
  };

  const handleAsk = () => {
    if (!query.trim()) {
      toast({
        title: "Empty Query",
        description: "Please enter a question",
        variant: "destructive",
      });
      return;
    }
    answerMutation.mutate({ query, top_k: topK });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          RAG Search & Q&A
        </h1>
        <p className="text-muted-foreground mt-2">
          Search your documents or ask questions powered by AI
        </p>
      </div>

      {/* Settings */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium">Top-K Results:</label>
            <input
              type="range"
              min="1"
              max="20"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="flex-1 accent-neon-cyan"
            />
            <span className="text-sm font-mono bg-neon-cyan/20 px-3 py-1 rounded text-neon-cyan">
              {topK}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="search" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="search">
            <Search className="h-4 w-4 mr-2" />
            Search
          </TabsTrigger>
          <TabsTrigger value="qa">
            <MessageSquare className="h-4 w-4 mr-2" />
            Q&A
          </TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex space-x-2">
                <Input
                  placeholder="Search across your documents..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="flex-1"
                />
                <Button
                  onClick={handleSearch}
                  disabled={searchMutation.isPending}
                >
                  {searchMutation.isPending ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      Search
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Search Results */}
          {searchResults && searchResults.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Results ({searchResults.length})</h3>
              {searchResults.map((result, idx) => (
                <Card key={idx} className="comic-panel">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-base font-medium">
                          {result.metadata.filename || "Unknown Document"}
                        </CardTitle>
                        <CardDescription className="text-xs mt-1">
                          Chunk {result.metadata.chunk_index} • {result.metadata.format?.toUpperCase()}
                        </CardDescription>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="text-xs text-muted-foreground">Confidence</span>
                        <span className={`text-lg font-bold ${getConfidenceColor(result.score)}`}>
                          {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{result.content}</p>
                    {/* Confidence Bar */}
                    <div className="mt-3 h-1 bg-base-bg rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          result.score >= 0.8
                            ? "bg-neon-green"
                            : result.score >= 0.6
                            ? "bg-neon-cyan"
                            : "bg-neon-magenta"
                        }`}
                        style={{ width: `${result.score * 100}%` }}
                      ></div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {searchMutation.isSuccess && searchResults && searchResults.length === 0 && (
            <Card>
              <CardContent className="p-12 text-center">
                <Search className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-lg text-muted-foreground">No results found</p>
                <p className="text-sm text-muted-foreground mt-2">Try a different search query</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Q&A Tab */}
        <TabsContent value="qa" className="space-y-4">
          {/* Chat Messages */}
          <Card className="h-[500px] flex flex-col">
            <CardHeader className="border-b border-neon-cyan/30">
              <CardTitle>AI Assistant</CardTitle>
              <CardDescription>Ask questions about your documents</CardDescription>
            </CardHeader>
            
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Sparkles className="h-12 w-12 mx-auto mb-4 text-neon-cyan" />
                    <p className="text-lg text-muted-foreground">Ask your first question</p>
                    <p className="text-sm text-muted-foreground mt-2">
                      I'll search your documents and provide answers with citations
                    </p>
                  </div>
                </div>
              ) : (
                messages.map((message, idx) => (
                  <div
                    key={idx}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${
                        message.role === "user"
                          ? "bg-neon-cyan/20 border border-neon-cyan/50"
                          : "bg-neon-magenta/20 border border-neon-magenta/50"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{message.content}</p>
                      
                      {/* Citations */}
                      {message.metadata?.citations && message.metadata.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-neon-magenta/30">
                          <p className="text-xs text-muted-foreground mb-2">Sources:</p>
                          <div className="space-y-1">
                            {message.metadata.citations.map((citation: any, citIdx: number) => (
                              <div key={citIdx} className="flex items-center space-x-2 text-xs">
                                <FileText className="h-3 w-3 text-neon-cyan" />
                                <span className="text-neon-cyan">{citation.filename}</span>
                                <span className="text-muted-foreground">
                                  ({(citation.score * 100).toFixed(0)}%)
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {answerMutation.isPending && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] rounded-lg p-4 bg-neon-magenta/20 border border-neon-magenta/50">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-neon-magenta rounded-full animate-pulse"></div>
                      <div className="w-2 h-2 bg-neon-magenta rounded-full animate-pulse delay-75"></div>
                      <div className="w-2 h-2 bg-neon-magenta rounded-full animate-pulse delay-150"></div>
                      <span className="text-sm text-muted-foreground ml-2">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>

            {/* Input */}
            <div className="border-t border-neon-cyan/30 p-4">
              <div className="flex space-x-2">
                <Input
                  placeholder="Ask a question..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleAsk()}
                  className="flex-1"
                />
                <Button
                  onClick={handleAsk}
                  disabled={answerMutation.isPending}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
