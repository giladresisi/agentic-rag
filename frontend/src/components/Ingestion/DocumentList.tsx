import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, Trash2, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Document, IngestionStatus } from '@/types/ingestion';

interface DocumentListProps {
  documents: Document[];
  onDelete: (documentId: string) => Promise<void>;
  isLoading: boolean;
}

function StatusIndicator({ status }: { status: IngestionStatus }) {
  switch (status) {
    case 'processing':
      return (
        <div className="flex items-center gap-1.5 text-yellow-600">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span className="text-xs font-medium">Processing</span>
        </div>
      );
    case 'completed':
      return (
        <div className="flex items-center gap-1.5 text-green-600">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="text-xs font-medium">Completed</span>
        </div>
      );
    case 'failed':
      return (
        <div className="flex items-center gap-1.5 text-red-600">
          <AlertCircle className="w-3.5 h-3.5" />
          <span className="text-xs font-medium">Failed</span>
        </div>
      );
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

export function DocumentList({ documents, onDelete, isLoading }: DocumentListProps) {
  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <FileText className="w-12 h-12 mx-auto mb-2 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 h-full flex flex-col">
      <h2 className="text-lg font-semibold mb-3 px-2">Documents</h2>
      <ScrollArea className="flex-1">
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="border rounded-lg p-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <FileText className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" title={doc.filename}>
                      {doc.filename}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <StatusIndicator status={doc.status} />
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs text-muted-foreground">
                        {formatFileSize(doc.file_size_bytes)}
                      </span>
                      {doc.chunk_count !== null && doc.status === 'completed' && (
                        <>
                          <span className="text-xs text-muted-foreground">•</span>
                          <span className="text-xs text-muted-foreground">
                            {doc.chunk_count} chunks
                          </span>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDate(doc.created_at)}
                    </p>
                    {doc.error_message && (
                      <p className="text-xs text-red-600 mt-1 truncate" title={doc.error_message}>
                        Error: {doc.error_message}
                      </p>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(doc.id)}
                  className="flex-shrink-0"
                >
                  <Trash2 className="w-4 h-4 text-muted-foreground hover:text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
