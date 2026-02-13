import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useIngestion } from '@/hooks/useIngestion';
import { DocumentUpload } from './DocumentUpload';
import { DocumentList } from './DocumentList';
import type { ProviderConfig } from '@/types/chat';
import { Button } from '@/components/ui/button';
import { MessageSquare, AlertCircle, FileText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { SettingsModal } from '@/components/Settings/SettingsModal';
import { useModelConfig } from '@/hooks/useModelConfig';
import { UserProfileMenu } from '@/components/Layout/UserProfileMenu';

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
  const modelConfig = useModelConfig(
    { provider: 'openai', model: 'gpt-4o-mini' },
    { provider: 'openai', model: 'text-embedding-3-small', dimensions: 1536 }
  );
  const [showSettings, setShowSettings] = useState(false);

  const handleUpload = async (file: File, embeddingConfig?: ProviderConfig) => {
    try {
      setUploadError(null);
      await uploadDocument(file, embeddingConfig);
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

  const location = useLocation();
  const isChat = location.pathname === '/chat';

  return (
    <div className="flex h-screen">
      {/* Left Sidebar - Document List */}
      <div className="w-80 border-r bg-muted/10 flex flex-col">
        {/* Mode Toggle */}
        <div className="p-4 border-b">
          <div className="grid grid-cols-2 gap-2">
            <Link to="/chat" className="w-full">
              <Button
                variant={isChat ? 'default' : 'outline'}
                size="sm"
                className="w-full"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat
              </Button>
            </Link>
            <Link to="/ingestion" className="w-full">
              <Button
                variant={!isChat ? 'default' : 'outline'}
                size="sm"
                className="w-full"
              >
                <FileText className="w-4 h-4 mr-2" />
                Documents
              </Button>
            </Link>
          </div>
        </div>

        {/* Document Library Header */}
        <div className="p-4 border-b">
          <h2 className="font-semibold text-sm text-muted-foreground">
            Document Library
          </h2>
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-hidden p-4">
          <DocumentList
            documents={documents}
            onDelete={handleDelete}
            isLoading={isLoading}
          />
        </div>

        {/* User profile at bottom */}
        <div className="border-t">
          <UserProfileMenu
            user={user}
            onSettingsClick={() => setShowSettings(true)}
            onLogout={logout}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b p-4">
          <h1 className="text-xl font-semibold">Document Ingestion</h1>
        </header>

        {/* Main Content */}
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-2xl mx-auto space-y-6">
            <DocumentUpload
              onUpload={handleUpload}
              isUploading={isUploading}
              embeddingConfig={modelConfig.embeddingsConfig.current}
            />

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
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        chatConfig={modelConfig.chatConfig.pending}
        embeddingsConfig={modelConfig.embeddingsConfig.pending}
        onChatConfigChange={modelConfig.updateChatConfig}
        onEmbeddingsConfigChange={modelConfig.updateEmbeddingsConfig}
        onConfirm={modelConfig.confirmChanges}
        onCancel={modelConfig.cancelChanges}
        hasChanges={modelConfig.hasChanges}
      />
    </div>
  );
}
