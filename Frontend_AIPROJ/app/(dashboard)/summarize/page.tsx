"use client"

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { documentsAPI, ragAPI, analyticsAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading";
import { useToast } from "@/components/ui/use-toast";
import { FileText, Sparkles, Layers } from "lucide-react";
import type { Document, SummarizeResponse } from "@/lib/types/api";

export default function SummarizePage() {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [mode, setMode] = useState<"auto" | "extractive" | "hybrid">("auto");
  const [length, setLength] = useState<"short" | "medium" | "detailed">("medium");
  const [maxChunks, setMaxChunks] = useState(5);
  const [multiDocIds, setMultiDocIds] = useState<string[]>([]);
  const [result, setResult] = useState<SummarizeResponse | null>(null);
  const { toast } = useToast();

  // Fetch documents
  const { data: docsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsAPI.list({ limit: 100, offset: 0 }),
  });

  const documents = docsData?.documents || [];

  // Summarize mutation
  const summarizeMutation = useMutation({
    mutationFn: (data: { document_id: string; mode: string; length: string; max_chunks: number }) =>
      ragAPI.summarize(data.document_id, data.mode, data.length, data.max_chunks),
    onSuccess: (data: SummarizeResponse) => {
      setResult(data);
      toast({
        title: "Summary Complete",
        description: "Document summarized successfully",
        variant: "success",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Summarization Failed",
        description: error.response?.data?.detail || "Failed to summarize document",
        variant: "destructive",
      });
    },
  });

  // Aggregate mutation (multi-document)
  const aggregateMutation = useMutation({
    mutationFn: (data: { document_ids: string[] }) =>
      analyticsAPI.aggregate(data.document_ids),
    onSuccess: (data: any) => {
      setResult({
        summary: data.summary,
        metadata: data.metadata,
      });
      toast({
        title: "Aggregation Complete",
        description: "Cross-document insights generated",
        variant: "success",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Aggregation Failed",
        description: error.response?.data?.detail || "Failed to aggregate documents",
        variant: "destructive",
      });
    },
  });

  const handleSummarize = () => {
    if (!selectedDocId) {
      toast({
        title: "No Document Selected",
        description: "Please select a document to summarize",
        variant: "destructive",
      });
      return;
    }
    setResult(null);
    summarizeMutation.mutate({
      document_id: selectedDocId,
      mode,
      length,
      max_chunks: maxChunks,
    });
  };

  const handleAggregate = () => {
    if (multiDocIds.length < 2) {
      toast({
        title: "Insufficient Documents",
        description: "Please select at least 2 documents for aggregation",
        variant: "destructive",
      });
      return;
    }
    setResult(null);
    aggregateMutation.mutate({ document_ids: multiDocIds });
  };

  const toggleMultiDoc = (docId: string) => {
    setMultiDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  if (documents.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">No documents found</p>
            <p className="text-sm text-muted-foreground mt-2">Upload documents to get started</p>
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
          Document Summarization
        </h1>
        <p className="text-muted-foreground mt-2">
          AI-powered summaries and cross-document insights
        </p>
      </div>

      {/* Single Document Mode */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <FileText className="h-5 w-5 text-neon-cyan" />
            <CardTitle>Single Document Summary</CardTitle>
          </div>
          <CardDescription>Summarize an individual document</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Select Document</label>
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
            >
              <option value="">Choose a document...</option>
              {documents.map((doc: Document) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.format.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
              >
                <option value="auto">Auto</option>
                <option value="extractive">Extractive</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Length</label>
              <select
                value={length}
                onChange={(e) => setLength(e.target.value as any)}
                className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
              >
                <option value="short">Short</option>
                <option value="medium">Medium</option>
                <option value="detailed">Detailed</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Max Chunks: {maxChunks}</label>
              <input
                type="range"
                min="1"
                max="20"
                value={maxChunks}
                onChange={(e) => setMaxChunks(Number(e.target.value))}
                className="w-full accent-neon-cyan"
              />
            </div>
          </div>

          <Button
            onClick={handleSummarize}
            disabled={summarizeMutation.isPending}
            className="w-full"
          >
            {summarizeMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                Summarizing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Summary
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Multi-Document Aggregation */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Layers className="h-5 w-5 text-neon-magenta" />
            <CardTitle>Multi-Document Aggregation</CardTitle>
          </div>
          <CardDescription>Generate insights across multiple documents</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">
              Select Documents ({multiDocIds.length} selected)
            </label>
            <div className="max-h-48 overflow-y-auto space-y-2 p-3 bg-base-bg rounded-lg border border-neon-cyan/30">
              {documents.map((doc: Document) => (
                <label
                  key={doc.id}
                  className="flex items-center space-x-3 p-2 rounded hover:bg-base-surface cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={multiDocIds.includes(doc.id)}
                    onChange={() => toggleMultiDoc(doc.id)}
                    className="w-4 h-4 accent-neon-magenta"
                  />
                  <span className="text-sm flex-1">{doc.filename}</span>
                  <span className="text-xs text-muted-foreground">
                    {doc.format.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <Button
            onClick={handleAggregate}
            disabled={aggregateMutation.isPending || multiDocIds.length < 2}
            className="w-full"
            variant="outline"
          >
            {aggregateMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mr-2"></div>
                Aggregating...
              </>
            ) : (
              <>
                <Layers className="h-4 w-4 mr-2" />
                Aggregate Insights
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Result Display */}
      {(summarizeMutation.isPending || aggregateMutation.isPending) && (
        <LoadingState message="Processing your request..." />
      )}

      {result && (
        <Card className="border-neon-green/50 animate-slide-in-right">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Sparkles className="h-5 w-5 text-neon-green" />
              <CardTitle>Summary Result</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary Text */}
            <div className="p-4 bg-base-bg rounded-lg border border-neon-cyan/30">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.summary}</p>
            </div>

            {/* Metadata */}
            {result.metadata && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-neon-cyan/30">
                {result.metadata.mode && (
                  <div>
                    <p className="text-xs text-muted-foreground">Mode</p>
                    <p className="text-sm font-medium capitalize">{result.metadata.mode}</p>
                  </div>
                )}

                {result.metadata.chunks_used !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">Chunks Used</p>
                    <p className="text-sm font-medium text-neon-cyan">{result.metadata.chunks_used}</p>
                  </div>
                )}

                {result.metadata.model_name && (
                  <div>
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-medium">{result.metadata.model_name}</p>
                  </div>
                )}

                {result.metadata.generation_time !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">Time</p>
                    <p className="text-sm font-medium text-neon-magenta">
                      {result.metadata.generation_time.toFixed(2)}s
                    </p>
                  </div>
                )}

                {result.metadata.document_count !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">Documents</p>
                    <p className="text-sm font-medium text-neon-purple">
                      {result.metadata.document_count}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Key Points */}
            {result.key_points && result.key_points.length > 0 && (
              <div className="pt-4 border-t border-neon-cyan/30">
                <h4 className="text-sm font-semibold text-neon-cyan mb-3">Key Points</h4>
                <ul className="space-y-2">
                  {result.key_points.map((point: string, idx: number) => (
                    <li key={idx} className="flex items-start space-x-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan mt-2 flex-shrink-0"></div>
                      <span className="text-sm">{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
