import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useIngestion } from '@/hooks/useIngestion';
import { DocumentUpload } from './DocumentUpload';
import { DocumentList } from './DocumentList';
import { Button } from '@/components/ui/button';
import { LogOut, MessageSquare, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export function IngestionInterface() {
  const { user, token, logout } = useAuth();
  const {
    documents,
    isLoading,
    isUploading,
    error,
    uploadDocument,
    deleteDocument,
  } = useIngestion(token);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    try {
      setUploadError(null);
      await uploadDocument(file);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
    } catch (err) {
      // Error is already set in the hook
    }
  };

  return (
    <div className="flex h-screen">
      {/* Left Sidebar - Document List */}
      <div className="w-80 border-r flex flex-col">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-sm text-muted-foreground">
            Document Library
          </h2>
        </div>
        <div className="flex-1 overflow-hidden p-4">
          <DocumentList
            documents={documents}
            onDelete={handleDelete}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b p-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold">Document Ingestion</h1>
          <div className="flex items-center gap-2">
            <Link to="/chat">
              <Button variant="outline" size="sm">
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat
              </Button>
            </Link>
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-2xl mx-auto space-y-6">
            <DocumentUpload onUpload={handleUpload} isUploading={isUploading} />

            {(uploadError || error) && (
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-destructive mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive">Error</p>
                  <p className="text-sm text-destructive/90">
                    {uploadError || error}
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <h3 className="text-lg font-semibold">How it works</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <p>
                  Upload documents to build your knowledge base for RAG-powered chat.
                  Supported formats include PDF, DOCX, TXT, HTML, and Markdown files.
                </p>
                <p>
                  Once uploaded, documents are automatically processed:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Text is extracted from the document</li>
                  <li>Content is split into semantic chunks</li>
                  <li>Embeddings are generated for vector search</li>
                  <li>Chunks are stored for retrieval during chat</li>
                </ul>
                <p>
                  Processing happens in the background. You'll see status updates
                  in real-time as your documents are processed.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
