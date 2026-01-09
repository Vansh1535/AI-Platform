"use client"

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { documentsAPI } from "@/lib/api/endpoints";
import { useAuthStore } from "@/lib/store/authStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LoadingState } from "@/components/ui/loading";
import { useToast } from "@/components/ui/use-toast";
import { Upload, Search, FileText, MoreVertical, Eye, Sparkles, X, Trash2 } from "lucide-react";
import { formatFileSize, formatDate, getStatusColor } from "@/lib/utils";
import type { Document } from "@/lib/types/api";

export default function DocumentsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuthStore();

  const pageSize = 10;

  // Fetch documents
  const { data, isLoading, error } = useQuery({
    queryKey: ["documents", page, searchQuery],
    queryFn: () => documentsAPI.list({ limit: pageSize, offset: page * pageSize }),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      console.log("Starting upload for:", file.name, file.type, file.size);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", file.name);
      
      try {
        const response = await documentsAPI.upload(formData);
        console.log("Upload response:", response);
        return response;
      } catch (error) {
        console.error("Upload error:", error);
        throw error;
      }
    },
    onSuccess: (data) => {
      console.log("Upload succeeded:", data);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({
        title: "Success",
        description: `Document uploaded: ${data.chunks || 0} chunks created`,
        variant: "success",
      });
    },
    onError: (error: any) => {
      console.error("Upload failed:", error);
      const errorMsg = error.response?.data?.detail || error.message || "Failed to upload document";
      toast({
        title: "Upload Failed",
        description: errorMsg,
        variant: "destructive",
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      return await documentsAPI.delete(id);
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
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || "Failed to delete document";
      toast({
        title: "Delete Failed",
        description: errorMsg,
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

  const documents = data?.documents || [];
  const totalPages = Math.ceil((data?.pagination.total_count || 0) / pageSize);

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
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          Document Management
        </h1>
        <p className="text-muted-foreground mt-2">
          Upload and manage your documents for RAG processing
        </p>
      </div>

      {/* Upload Zone */}
      <Card>
        <CardContent className="p-6">
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
            <div className="mt-4 p-4 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
              <div className="flex items-center justify-center space-x-3">
                <div className="w-5 h-5 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin"></div>
                <div className="text-sm">
                  <p className="text-neon-cyan font-medium">Uploading document...</p>
                  <p className="text-muted-foreground text-xs mt-1">Processing file and creating embeddings</p>
                </div>
              </div>
            </div>
          )}
          {uploadMutation.isError && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">
                ❌ Upload failed. Check console for details.
              </p>
            </div>
          )}
          {uploadMutation.isSuccess && (
            <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
              <p className="text-sm text-green-400">
                ✅ Document uploaded successfully!
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Documents Table */}
      {isLoading ? (
        <LoadingState message="Loading documents..." />
      ) : documents.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">No documents yet</p>
            <p className="text-sm text-muted-foreground mt-2">Upload your first document to get started</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-neon-cyan/30">
                  <tr>
                    <th className="text-left p-4 font-medium text-neon-cyan">Name</th>
                    <th className="text-left p-4 font-medium text-neon-cyan">Type</th>
                    <th className="text-left p-4 font-medium text-neon-cyan">Size</th>
                    <th className="text-left p-4 font-medium text-neon-cyan">Uploaded</th>
                    <th className="text-left p-4 font-medium text-neon-cyan">Status</th>
                    <th className="text-left p-4 font-medium text-neon-cyan">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id} className="border-b border-neon-cyan/10 hover:bg-base-surface/50 transition-colors">
                      <td className="p-4">
                        <div className="flex items-center space-x-2">
                          <FileText className="h-4 w-4 text-neon-cyan" />
                          <span className="font-medium">{doc.filename}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-neon-purple/20 text-neon-purple">
                          {doc.format.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-4 text-muted-foreground">
                        {doc.size ? formatFileSize(doc.size) : "-"}
                      </td>
                      <td className="p-4 text-muted-foreground">
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center space-x-2">
                          <div className={`w-2 h-2 rounded-full ${getStatusColor(doc.status)}`}></div>
                          <span className="text-sm">{doc.status}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedDoc(doc);
                              setPreviewOpen(true);
                            }}
                            title="Preview document"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {isAdmin && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setDeleteConfirm(doc.id)}
                              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                              title="Delete document"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-neon-cyan/30">
                <p className="text-sm text-muted-foreground">
                  Page {page + 1} of {totalPages}
                </p>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Preview Modal */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedDoc?.filename}</DialogTitle>
            <DialogDescription>Document details and preview</DialogDescription>
          </DialogHeader>
          
          {previewLoading ? (
            <LoadingState message="Loading preview..." />
          ) : (
            <div className="space-y-4">
              {/* Metadata */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <span className="text-muted-foreground">Type:</span>
                    <span>{selectedDoc?.format.toUpperCase()}</span>
                    
                    <span className="text-muted-foreground">Size:</span>
                    <span>{selectedDoc?.size ? formatFileSize(selectedDoc.size) : "-"}</span>
                    
                    <span className="text-muted-foreground">Chunks:</span>
                    <span>{selectedDoc?.chunk_count}</span>
                    
                    <span className="text-muted-foreground">Status:</span>
                    <span className="flex items-center space-x-2">
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(selectedDoc?.status || "")}`}></div>
                      <span>{selectedDoc?.status}</span>
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Preview Chunks */}
              {previewData?.preview_chunks && previewData.preview_chunks.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Content Preview</CardTitle>
                    <CardDescription>First {previewData.preview_chunks.length} chunks</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {previewData.preview_chunks.map((chunk: any, idx: number) => (
                      <div key={idx} className="p-3 rounded bg-base-bg/50 border border-neon-cyan/20">
                        <p className="text-xs text-muted-foreground mb-1">Chunk {idx + 1}</p>
                        <p className="text-sm">{chunk.chunk}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteConfirm !== null} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this document? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm(null)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
