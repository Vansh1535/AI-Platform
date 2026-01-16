"use client"

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { documentsAPI, exportAPI, analyticsAPI, ragAPI, summarizeAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { Download, FileText, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { Document } from "@/lib/types/api";

export default function ExportPage() {
  const [sourceType, setSourceType] = useState<"rag" | "summary" | "csv_insights" | "aggregation">("rag");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]); // For multi-document aggregation
  const [query, setQuery] = useState("");
  const [filename, setFilename] = useState("report");
  const [format, setFormat] = useState<"markdown" | "pdf">("markdown");
  const [preview, setPreview] = useState<string>("");
  const [pdfAvailable, setPdfAvailable] = useState(true);
  const { toast } = useToast();

  // Check PDF capabilities
  const { data: capabilities } = useQuery({
    queryKey: ["export-capabilities"],
    queryFn: exportAPI.capabilities,
  });

  useEffect(() => {
    if (capabilities) {
      const isPdfAvailable = capabilities.pdf?.available || false;
      setPdfAvailable(isPdfAvailable);
      // Auto-switch to markdown if PDF not available
      if (!isPdfAvailable && format === "pdf") {
        setFormat("markdown");
        toast({
          title: "PDF Unavailable",
          description: capabilities.pdf?.message || "Markdown export will be used instead",
          variant: "default",
        });
      }
    }
  }, [capabilities]);

  // Fetch documents
  const { data: docsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsAPI.list({ limit: 100, offset: 0 }),
  });

  const documents = docsData?.documents || [];

  // Export mutation with data fetching
  const exportMutation = useMutation({
    mutationFn: async (params: {
      payload_source: string;
      payload: any;
      format: 'md' | 'pdf';
      filename: string;
    }) => {
      let finalPayload = params.payload;
      
      // Fetch actual data based on source type
      switch (params.payload_source) {
        case 'rag':
          // Payload has {query, top_k}, fetch the answer
          const ragResponse = await ragAPI.answer(params.payload.query, params.payload.top_k);
          // Add the original query back to the response
          finalPayload = { ...ragResponse, query: params.payload.query };
          break;
          
        case 'summary':
          // Payload has {document_id, mode, length}, fetch the summary
          const summaryResponse = await summarizeAPI.document({
            document_id: params.payload.document_id,
            mode: params.payload.mode || 'auto',
            max_chunks: 5,
            summary_length: params.payload.length || 'medium',
          });
          // Add document info back to the response
          const doc = documents.find((d: Document) => d.id === params.payload.document_id);
          finalPayload = { 
            ...summaryResponse, 
            document_id: params.payload.document_id,
            document_name: doc?.filename || 'Unknown',
            format: doc?.format || 'unknown'
          };
          break;
          
        case 'csv_insights':
          // Payload has {document_id, use_llm}, fetch the insights
          const csvResponse = await analyticsAPI.csvInsights(
            params.payload.document_id,
            params.payload.use_llm || false
          );
          // Add document info back
          const csvDoc = documents.find((d: Document) => d.id === params.payload.document_id);
          finalPayload = {
            ...csvResponse,
            document_id: params.payload.document_id,
            document_name: csvDoc?.filename || 'Unknown',
          };
          break;
          
        case 'aggregation':
          // Payload has {document_ids}, fetch the aggregation
          const aggregationResponse = await analyticsAPI.aggregate(
            params.payload.document_ids,
            'auto',
            5
          );
          // Add document names to per_document summaries
          const docsWithNames = aggregationResponse.per_document.map((docSummary: any) => {
            const foundDoc = documents.find((d: Document) => d.id === docSummary.document_id);
            return {
              ...docSummary,
              document_name: foundDoc?.filename || docSummary.document_id,
            };
          });
          finalPayload = {
            ...aggregationResponse,
            per_document: docsWithNames,
          };
          break;
      }
      
      // Now export with the actual data
      return exportAPI.report({
        ...params,
        payload: finalPayload,
      });
    },
    onSuccess: (data) => {
      if (format === "markdown" || (format as string) === "md") {
        setPreview(data.content);
      } else {
        // PDF - trigger download
        const blob = new Blob([atob(data.content)], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.metadata.filename || filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      toast({
        title: "Export Complete",
        description: `Report exported successfully`,
        variant: "success",
      });
    },
    onError: (error: any) => {
      let errorMessage = "Failed to export report";
      
      // Handle validation errors (422)
      if (error.response?.data) {
        const data = error.response.data;
        if (Array.isArray(data)) {
          // Pydantic validation errors
          errorMessage = data.map((err: any) => err.msg || JSON.stringify(err)).join(", ");
        } else if (data.detail) {
          errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
      }
      
      toast({
        title: "Export Failed",
        description: errorMessage,
        variant: "destructive",
      });
    },
  });

  const handleExport = () => {
    let sourceData: any = {};

    switch (sourceType) {
      case "rag":
        if (!query) {
          toast({
            title: "Missing Input",
            description: "Please enter a query for RAG answer export",
            variant: "destructive",
          });
          return;
        }
        sourceData = { query, top_k: 5 };
        break;

      case "summary":
        if (!selectedDocId) {
          toast({
            title: "Missing Input",
            description: "Please select a document for summary export",
            variant: "destructive",
          });
          return;
        }
        sourceData = { document_id: selectedDocId, mode: "auto", length: "medium" };
        break;

      case "csv_insights":
        if (!selectedDocId) {
          toast({
            title: "Missing Input",
            description: "Please select a CSV document for insights export",
            variant: "destructive",
          });
          return;
        }
        sourceData = { document_id: selectedDocId, use_llm: true };
        break;

      case "aggregation":
        if (selectedDocIds.length < 2) {
          toast({
            title: "Insufficient Documents",
            description: "Please select at least 2 documents for aggregation export",
            variant: "destructive",
          });
          return;
        }
        sourceData = { document_ids: selectedDocIds };
        break;
    }

    if (!filename.trim()) {
      toast({
        title: "Missing Filename",
        description: "Please enter a filename for the export",
        variant: "destructive",
      });
      return;
    }

    setPreview("");
    exportMutation.mutate({
      payload_source: sourceType,
      payload: sourceData,
      format: format === "markdown" ? "md" : "pdf",
      filename,
    });
  };

  const handleDownload = () => {
    if (!preview) return;

    const blob = new Blob([preview], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: "Download Started",
      description: "Markdown file downloaded successfully",
      variant: "success",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          Export Reports
        </h1>
        <p className="text-muted-foreground mt-2">
          Generate and export professional reports in Markdown or PDF
        </p>
      </div>

      {/* PDF Warning */}
      {!pdfAvailable && (
        <Card className="border-yellow-500/50 bg-yellow-500/10">
          <CardContent className="p-4 flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">PDF Export Unavailable</p>
              <p className="text-xs text-muted-foreground mt-1">
                PDF generation requires WeasyPrint. Only Markdown export is available.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Export Configuration</CardTitle>
          <CardDescription>Configure your report export settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Source Type */}
          <div>
            <label className="text-sm font-medium mb-2 block">Source Type</label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as any)}
              className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
            >
              <option value="rag">RAG Answer</option>
              <option value="summary">Document Summary</option>
              <option value="csv_insights">CSV Insights</option>
              <option value="aggregation">Multi-Document Aggregation</option>
            </select>
          </div>

          {/* Conditional Inputs */}
          {sourceType === "rag" && (
            <div>
              <label className="text-sm font-medium mb-2 block">Query</label>
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your question..."
              />
            </div>
          )}

          {(sourceType === "summary" || sourceType === "csv_insights") && (
            <div>
              <label className="text-sm font-medium mb-2 block">Select Document</label>
              <select
                value={selectedDocId || ""}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full px-4 py-2 bg-base-bg border border-neon-cyan/30 rounded-lg focus:border-neon-cyan focus:outline-none"
              >
                <option value="">Choose a document...</option>
                {documents
                  .filter((doc: Document) =>
                    sourceType === "csv_insights" ? doc.format === "csv" : true
                  )
                  .map((doc: Document) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename} ({doc.format.toUpperCase()})
                    </option>
                  ))}
              </select>
            </div>
          )}

          {sourceType === "aggregation" && (
            <div>
              <label className="text-sm font-medium mb-2 block">
                Select Documents (minimum 2)
              </label>
              <div className="space-y-2 max-h-64 overflow-y-auto border border-neon-cyan/30 rounded-lg p-3">
                {documents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No documents available</p>
                ) : (
                  documents.map((doc: Document) => (
                    <label
                      key={doc.id}
                      className="flex items-center space-x-2 p-2 hover:bg-neon-cyan/10 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocIds.includes(doc.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDocIds([...selectedDocIds, doc.id]);
                          } else {
                            setSelectedDocIds(selectedDocIds.filter(id => id !== doc.id));
                          }
                        }}
                        className="w-4 h-4 accent-neon-cyan"
                      />
                      <span className="text-sm flex-1">
                        {doc.filename} <span className="text-muted-foreground">({doc.format.toUpperCase()})</span>
                      </span>
                    </label>
                  ))
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Selected: {selectedDocIds.length} document{selectedDocIds.length !== 1 ? 's' : ''}
                {selectedDocIds.length > 0 && selectedDocIds.length < 2 && (
                  <span className="text-yellow-500 ml-2">⚠ Select at least 2 documents</span>
                )}
              </p>
            </div>
          )}

          {/* Format & Filename */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Export Format</label>
              <div className="flex space-x-2">
                <Button
                  variant={format === "markdown" ? "default" : "outline"}
                  onClick={() => setFormat("markdown")}
                  className="flex-1"
                >
                  Markdown
                </Button>
                <Button
                  variant={format === "pdf" ? "default" : "outline"}
                  onClick={() => setFormat("pdf")}
                  disabled={!pdfAvailable}
                  className="flex-1"
                >
                  PDF
                </Button>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Filename</label>
              <Input
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder="report"
              />
            </div>
          </div>

          <Button
            onClick={handleExport}
            disabled={exportMutation.isPending}
            className="w-full"
          >
            {exportMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                Generating...
              </>
            ) : (
              <>
                <FileText className="h-4 w-4 mr-2" />
                Generate Report
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Preview (Markdown only) */}
      {preview && format === "markdown" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Preview</CardTitle>
                <CardDescription>Markdown report preview</CardDescription>
              </div>
              <Button onClick={handleDownload} variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="p-4 bg-base-bg rounded-lg border border-neon-cyan/30 max-h-[600px] overflow-y-auto">
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{preview}</ReactMarkdown>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Capabilities Info */}
      {capabilities && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Export Capabilities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${capabilities.markdown_available ? "bg-neon-green" : "bg-gray-500"}`}></div>
                <span className="text-sm">Markdown Export</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${capabilities.pdf_available ? "bg-neon-green" : "bg-gray-500"}`}></div>
                <span className="text-sm">PDF Export</span>
              </div>
            </div>
            {capabilities.supported_sources && (
              <div className="mt-4">
                <p className="text-xs text-muted-foreground mb-2">Supported Sources:</p>
                <div className="flex flex-wrap gap-2">
                  {capabilities.supported_sources.map((source: string) => (
                    <span
                      key={source}
                      className="px-2 py-1 rounded text-xs bg-neon-cyan/20 text-neon-cyan"
                    >
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
