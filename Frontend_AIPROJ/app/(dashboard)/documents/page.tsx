"use client"

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { documentsAPI, ragAPI, analyticsAPI } from "@/lib/api/endpoints";
import { useAuthStore } from "@/lib/store/authStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LoadingState } from "@/components/ui/loading";
import { useToast } from "@/components/ui/use-toast";
import { Upload, Search, FileText, Eye, Trash2, MessageSquare, Sparkles, BarChart3, FileDown, RefreshCw } from "lucide-react";
import { formatFileSize, formatDate, getStatusColor } from "@/lib/utils";
import type { Document } from "@/lib/types/api";

export default function DocumentIntelligencePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("search");
  
  // RAG states
  const [ragQuery, setRagQuery] = useState("");
  const [ragResults, setRagResults] = useState<any>(null);
  
  // Q&A states
  const [qaQuestion, setQaQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState<any>(null);
  
  // Summarize states
  const [selectedDocForSummary, setSelectedDocForSummary] = useState<string>("");
  const [summary, setSummary] = useState<any>(null);
  
  // Analytics states
  const [selectedDocForAnalytics, setSelectedDocForAnalytics] = useState<string>("");
  const [analytics, setAnalytics] = useState<any>(null);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuthStore();

  const pageSize = 10;

  // Fetch documents with real-time polling
  const { data: documentsData, isLoading, error } = useQuery({
    queryKey: ["documents", page, searchQuery],
    queryFn: () => documentsAPI.list({ limit: pageSize, offset: page * pageSize }),
    refetchInterval: 5000, // Poll every 5 seconds
    refetchOnWindowFocus: true,
  });

  // Upload mutation with optimistic update
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", file.name);
      return await documentsAPI.upload(formData);
    },
    onMutate: async (newFile) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ["documents"] });
      
      // Snapshot previous state
      const previous = queryClient.getQueryData(["documents"]);
      
      // Optimistically update
      queryClient.setQueryData(["documents", page, searchQuery], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          documents: [{
            id: 'uploading-' + Date.now(),
            filename: newFile.name,
            source: newFile.name,
            format: newFile.name.split('.').pop() || 'unknown',
            size: newFile.size,
            created_at: new Date().toISOString(),
            status: 'processing' as const,
            chunk_count: 0,
          }, ...old.documents],
        };
      });
      
      return { previous };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({
        title: "Success",
        description: `Document uploaded: ${data.chunks || 0} chunks created`,
        variant: "success",
      });
    },
    onError: (error: any, newFile, context) => {
      // Rollback
      if (context?.previous) {
        queryClient.setQueryData(["documents", page, searchQuery], context.previous);
      }
      const errorMsg = error.response?.data?.detail || error.message || "Failed to upload document";
      toast({
        title: "Upload Failed",
        description: errorMsg,
        variant: "destructive",
      });
    },
  });

  // Delete mutation with optimistic update
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      return await documentsAPI.delete(id);
    },
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ["documents"] });
      const previous = queryClient.getQueryData(["documents"]);
      
      queryClient.setQueryData(["documents", page, searchQuery], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          documents: old.documents.filter((doc: Document) => doc.id !== deletedId),
        };
      });
      
      return { previous };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({
        title: "Deleted",
        description: `Document "${data.filename}" has been deleted`,
        variant: "success",
      });
      setDeleteConfirm(null);
    },
    onError: (error: any, deletedId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["documents", page, searchQuery], context.previous);
      }
      const errorMsg = error.response?.data?.detail || error.message || "Failed to delete document";
      toast({
        title: "Delete Failed",
        description: errorMsg,
        variant: "destructive",
      });
    },
  });

  // RAG Search mutation
  const ragSearchMutation = useMutation({
    mutationFn: async (query: string) => {
      return await ragAPI.query({ query, top_k: 5 });
    },
    onSuccess: (data) => {
      setRagResults(data);
    },
    onError: (error: any) => {
      toast({
        title: "Search Failed",
        description: error.response?.data?.detail || "Failed to perform semantic search",
        variant: "destructive",
      });
    },
  });

  // Q&A mutation
  const qaMutation = useMutation({
    mutationFn: async (question: string) => {
      return await ragAPI.answer({ query: question, top_k: 5 });
    },
    onSuccess: (data) => {
      setQaAnswer(data);
      if (data.metadata?.error_class === "LLM_PROVIDER_UNAVAILABLE") {
        toast({
          title: "LLM Not Configured",
          description: "Q&A requires LLM API keys. Please configure GEMINI_API_KEY or OPENAI_API_KEY in backend .env",
          variant: "destructive",
        });
      }
    },
    onError: (error: any) => {
      toast({
        title: "Q&A Failed",
        description: error.response?.data?.detail || "Failed to generate answer",
        variant: "destructive",
      });
    },
  });

  // Summarize mutation
  const summarizeMutation = useMutation({
    mutationFn: async (docId: string) => {
      return await ragAPI.summarize(docId);
    },
    onSuccess: (data) => {
      setSummary(data);
    },
    onError: (error: any) => {
      toast({
        title: "Summarization Failed",
        description: error.response?.data?.detail || "Failed to generate summary",
        variant: "destructive",
      });
    },
  });

  // Analytics mutation
  const analyticsMutation = useMutation({
    mutationFn: async (docId: string) => {
      return await analyticsAPI.csvInsights(docId);
    },
    onSuccess: (data) => {
      setAnalytics(data);
    },
    onError: (error: any) => {
      toast({
        title: "Analytics Failed",
        description: error.response?.data?.detail || "Failed to analyze CSV",
        variant: "destructive",
      });
    },
  });

  // Dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      acceptedFiles.forEach((file) => uploadMutation.mutate(file));
    },
    multiple: true,
  });

  // Preview modal
  const { data: previewData, isLoading: previewLoading } = useQuery({
    queryKey: ["preview", selectedDoc?.id],
    queryFn: () => documentsAPI.preview(selectedDoc!.id, 5),
    enabled: !!selectedDoc && previewOpen,
  });

  const documents = documentsData?.documents || [];
  const totalPages = Math.ceil((documentsData?.pagination.total_count || 0) / pageSize);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card>
          <CardContent className="p-6">
            <p className="text-red-400">Error loading documents. Make sure backend is running.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
            📁 Document Intelligence Hub
          </h1>
          <p className="text-muted-foreground mt-2">
            Upload, query, analyze, and extract insights from your documents
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Auto-refresh: 5s</span>
        </div>
      </div>

      {/* Upload Zone */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Document Management
          </CardTitle>
          <CardDescription>
            Upload and manage documents ({documents.length} total)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-all cursor-pointer ${
              isDragActive
                ? "border-neon-cyan bg-neon-cyan/10 shadow-glow-cyan"
                : "border-neon-cyan/30 hover:border-neon-cyan hover:bg-neon-cyan/5"
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 mx-auto mb-4 text-neon-cyan" />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? "Drop files here" : "Drag & drop files here"}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              or click to browse
            </p>
            <p className="text-xs text-muted-foreground">
              Supported: PDF, CSV, TXT, DOCX, MD
            </p>
          </div>
          {uploadMutation.isPending && (
            <div className="p-4 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
              <div className="flex items-center justify-center space-x-3">
                <div className="w-5 h-5 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin"></div>
                <div className="text-sm">
                  <p className="text-neon-cyan font-medium">Uploading document...</p>
                  <p className="text-muted-foreground text-xs mt-1">Processing file and creating embeddings</p>
                </div>
              </div>
            </div>
          )}

          {/* Document List */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {isLoading ? (
              <LoadingState message="Loading documents..." />
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No documents uploaded yet</p>
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 border border-neon-cyan/20 rounded-lg hover:border-neon-cyan/40 transition-all"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <FileText className="h-5 w-5 text-neon-cyan" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{doc.filename}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                        <span>{doc.format.toUpperCase()}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                        <span>•</span>
                        <span className={getStatusColor(doc.status)}>{doc.status}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setSelectedDoc(doc);
                        setPreviewOpen(true);
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {isAdmin && (
                      <>
                        {deleteConfirm === doc.id ? (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => deleteMutation.mutate(doc.id)}
                            >
                              Confirm
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setDeleteConfirm(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteConfirm(doc.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-400" />
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Query & Analysis Tabs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Query & Analysis
          </CardTitle>
          <CardDescription>
            Search, ask questions, summarize, and analyze your documents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="search">
                <Search className="h-4 w-4 mr-2" />
                RAG Search
              </TabsTrigger>
              <TabsTrigger value="qa">
                <MessageSquare className="h-4 w-4 mr-2" />
                Q&A
              </TabsTrigger>
              <TabsTrigger value="summarize">
                <FileDown className="h-4 w-4 mr-2" />
                Summarize
              </TabsTrigger>
              <TabsTrigger value="analytics">
                <BarChart3 className="h-4 w-4 mr-2" />
                Analytics
              </TabsTrigger>
            </TabsList>

            {/* RAG Search Tab */}
            <TabsContent value="search" className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Semantic Search</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter search query..."
                    value={ragQuery}
                    onChange={(e) => setRagQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        ragSearchMutation.mutate(ragQuery);
                      }
                    }}
                  />
                  <Button
                    onClick={() => ragSearchMutation.mutate(ragQuery)}
                    disabled={!ragQuery || ragSearchMutation.isPending}
                  >
                    {ragSearchMutation.isPending ? "Searching..." : "Search"}
                  </Button>
                </div>
              </div>

              {ragResults && (
                <div className="space-y-3">
                  <h3 className="font-medium">Results ({ragResults.results?.length || 0} chunks found)</h3>
                  {ragResults.results?.map((result: any, idx: number) => (
                    <div key={idx} className="p-4 bg-base-surface border border-neon-cyan/20 rounded-lg">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-sm font-medium text-neon-cyan">
                          {result.metadata?.filename || 'Unknown'}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Score: {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">{result.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Q&A Tab */}
            <TabsContent value="qa" className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Ask a Question</label>
                <div className="flex gap-2">
                  <Textarea
                    placeholder="What is the total revenue mentioned in the documents?"
                    value={qaQuestion}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setQaQuestion(e.target.value)}
                    rows={3}
                  />
                </div>
                <Button
                  onClick={() => qaMutation.mutate(qaQuestion)}
                  disabled={!qaQuestion || qaMutation.isPending}
                  className="w-full"
                >
                  {qaMutation.isPending ? "Generating Answer..." : "Ask Question"}
                </Button>
              </div>

              {qaAnswer && (
                <div className="space-y-3">
                  <div className="p-4 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
                    <h3 className="font-medium text-neon-cyan mb-2">Answer:</h3>
                    <p className="text-sm">{qaAnswer.answer}</p>
                    {qaAnswer.user_message && (
                      <p className="text-xs text-yellow-400 mt-2">⚠️ {qaAnswer.user_message}</p>
                    )}
                  </div>
                  {qaAnswer.citations && qaAnswer.citations.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">Citations:</h4>
                      {qaAnswer.citations.map((citation: any, idx: number) => (
                        <div key={idx} className="p-3 bg-base-surface border border-neon-cyan/10 rounded text-xs mb-2">
                          <p className="text-muted-foreground">{citation.chunk}</p>
                          {citation.source && (
                            <p className="text-neon-cyan mt-1">Source: {citation.source}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </TabsContent>

            {/* Summarize Tab */}
            <TabsContent value="summarize" className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Document to Summarize</label>
                <select
                  className="w-full p-2 bg-base-bg border border-neon-cyan/30 rounded-md"
                  value={selectedDocForSummary}
                  onChange={(e) => setSelectedDocForSummary(e.target.value)}
                >
                  <option value="">-- Select Document --</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
                <Button
                  onClick={() => summarizeMutation.mutate(selectedDocForSummary)}
                  disabled={!selectedDocForSummary || summarizeMutation.isPending}
                  className="w-full"
                >
                  {summarizeMutation.isPending ? "Generating Summary..." : "Generate Summary"}
                </Button>
              </div>

              {summary && (
                <div className="p-4 bg-neon-purple/10 border border-neon-purple/30 rounded-lg">
                  <h3 className="font-medium text-neon-purple mb-2">Summary:</h3>
                  <p className="text-sm whitespace-pre-wrap">{summary.summary}</p>
                </div>
              )}
            </TabsContent>

            {/* Analytics Tab */}
            <TabsContent value="analytics" className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select CSV Document to Analyze</label>
                <select
                  className="w-full p-2 bg-base-bg border border-neon-cyan/30 rounded-md"
                  value={selectedDocForAnalytics}
                  onChange={(e) => setSelectedDocForAnalytics(e.target.value)}
                >
                  <option value="">-- Select CSV Document --</option>
                  {documents.filter(doc => doc.format === 'csv').map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
                <Button
                  onClick={() => analyticsMutation.mutate(selectedDocForAnalytics)}
                  disabled={!selectedDocForAnalytics || analyticsMutation.isPending}
                  className="w-full"
                >
                  {analyticsMutation.isPending ? "Analyzing..." : "Analyze CSV"}
                </Button>
              </div>

              {analytics && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-base-surface border border-neon-cyan/20 rounded-lg">
                      <p className="text-xs text-muted-foreground">Rows</p>
                      <p className="text-2xl font-bold text-neon-cyan">{analytics.basic_stats?.row_count || 0}</p>
                    </div>
                    <div className="p-3 bg-base-surface border border-neon-cyan/20 rounded-lg">
                      <p className="text-xs text-muted-foreground">Columns</p>
                      <p className="text-2xl font-bold text-neon-cyan">{analytics.basic_stats?.column_count || 0}</p>
                    </div>
                    <div className="p-3 bg-base-surface border border-neon-cyan/20 rounded-lg">
                      <p className="text-xs text-muted-foreground">Null Values</p>
                      <p className="text-2xl font-bold text-yellow-400">{analytics.basic_stats?.null_count || 0}</p>
                    </div>
                    <div className="p-3 bg-base-surface border border-neon-cyan/20 rounded-lg">
                      <p className="text-xs text-muted-foreground">Duplicates</p>
                      <p className="text-2xl font-bold text-red-400">{analytics.basic_stats?.duplicate_rows || 0}</p>
                    </div>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedDoc?.filename}</DialogTitle>
            <DialogDescription>
              {selectedDoc?.format.toUpperCase()} • {selectedDoc?.chunk_count} chunks
            </DialogDescription>
          </DialogHeader>
          {previewLoading ? (
            <LoadingState message="Loading preview..." />
          ) : previewData ? (
            <div className="space-y-3">
              {previewData.chunks?.map((chunk: any, idx: number) => (
                <div key={idx} className="p-4 bg-base-surface border border-neon-cyan/20 rounded-lg">
                  <p className="text-sm font-medium text-neon-cyan mb-2">Chunk {idx + 1}</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{chunk.text}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No preview available</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
