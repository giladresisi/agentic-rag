import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Upload, FileText, X, AlertCircle } from 'lucide-react';
import type { ProviderConfig } from '@/types/chat';
import { UploadErrorDialog } from './UploadErrorDialog';

const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
// IMPORTANT: Keep in sync with backend/config.py SUPPORTED_FILE_TYPES
const SUPPORTED_TYPES = ['.pdf', '.docx', '.pptx', '.txt', '.html', '.md', '.csv', '.json', '.xml', '.rtf'];
const SUPPORTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'text/plain',
  'text/html',
  'text/markdown',
  'text/csv',
  'application/json',
  'application/xml',
  'text/xml',
  'application/rtf',
  'text/rtf',
];

interface QueuedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'failed';
  error?: string;
  validationError?: string;
}

interface DocumentUploadProps {
  onUpload: (file: File, embeddingConfig?: ProviderConfig) => Promise<void>;
  isUploading: boolean;
  embeddingConfig?: ProviderConfig;
}

export function DocumentUpload({ onUpload, isUploading, embeddingConfig }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileQueue, setFileQueue] = useState<QueuedFile[]>([]);
  const [currentUploadIndex, setCurrentUploadIndex] = useState<number>(-1);
  const [isPaused, setIsPaused] = useState(false);
  const [showErrorDialog, setShowErrorDialog] = useState(false);
  const [errorDialogData, setErrorDialogData] = useState<{
    fileName: string;
    error: string;
    filesRemaining: number;
  } | null>(null);

  const removeFile = useCallback((id: string) => {
    setFileQueue(prev => prev.filter(f => f.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setFileQueue([]);
    setCurrentUploadIndex(-1);
    setIsPaused(false);
  }, []);

  const uploadNext = useCallback(async () => {
    // Find next valid file to upload
    let nextIndex = currentUploadIndex + 1;
    while (nextIndex < fileQueue.length) {
      const queuedFile = fileQueue[nextIndex];
      if (!queuedFile.validationError && queuedFile.status === 'pending') {
        break;
      }
      nextIndex++;
    }

    // No more files to upload
    if (nextIndex >= fileQueue.length) {
      setCurrentUploadIndex(-1);
      return;
    }

    setCurrentUploadIndex(nextIndex);
    const queuedFile = fileQueue[nextIndex];

    // Update status to uploading
    setFileQueue(prev => prev.map((f, idx) =>
      idx === nextIndex ? { ...f, status: 'uploading' as const } : f
    ));

    try {
      await onUpload(queuedFile.file, embeddingConfig);

      // Update status to success
      setFileQueue(prev => prev.map((f, idx) =>
        idx === nextIndex ? { ...f, status: 'success' as const } : f
      ));

      // Continue to next file
      if (!isPaused) {
        setTimeout(() => uploadNext(), 100);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';

      // Update status to failed
      setFileQueue(prev => prev.map((f, idx) =>
        idx === nextIndex ? { ...f, status: 'failed' as const, error: errorMessage } : f
      ));

      // Count remaining files
      const remainingCount = fileQueue.slice(nextIndex + 1).filter(
        f => !f.validationError && f.status === 'pending'
      ).length;

      // Show error dialog
      setIsPaused(true);
      setErrorDialogData({
        fileName: queuedFile.file.name,
        error: errorMessage,
        filesRemaining: remainingCount,
      });
      setShowErrorDialog(true);
    }
  }, [currentUploadIndex, fileQueue, onUpload, embeddingConfig, isPaused]);

  const handleUploadAll = useCallback(() => {
    if (fileQueue.length === 0) return;

    setCurrentUploadIndex(-1);
    setIsPaused(false);
    uploadNext();
  }, [fileQueue, uploadNext]);

  const handleContinueUpload = useCallback(() => {
    setShowErrorDialog(false);
    setErrorDialogData(null);
    setIsPaused(false);
    uploadNext();
  }, [uploadNext]);

  const handleStopUpload = useCallback(() => {
    setShowErrorDialog(false);
    setErrorDialogData(null);
    setCurrentUploadIndex(-1);
    setIsPaused(false);
  }, []);

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File "${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum size: ${MAX_FILE_SIZE_MB}MB`;
    }

    // Check file type by extension
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!SUPPORTED_TYPES.includes(extension)) {
      return `File "${file.name}" has unsupported type ${extension}. Supported: ${SUPPORTED_TYPES.join(', ')}`;
    }

    // Check MIME type if available
    if (file.type && !SUPPORTED_MIME_TYPES.includes(file.type)) {
      return `File "${file.name}" has unsupported MIME type "${file.type}". Supported: ${SUPPORTED_TYPES.join(', ')}`;
    }

    return null;
  };

  const createQueuedFile = (file: File): QueuedFile => {
    const validationError = validateFile(file);
    return {
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file,
      status: 'pending',
      validationError: validationError || undefined,
    };
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        const newFiles = files.map(createQueuedFile);
        setFileQueue(prev => [...prev, ...newFiles]);
      }
    },
    [createQueuedFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const newFiles = Array.from(files).map(createQueuedFile);
        setFileQueue(prev => [...prev, ...newFiles]);
      }
      // Reset input so same file can be selected again
      e.target.value = '';
    },
    [createQueuedFile]
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const QueueItem = ({ queuedFile, onRemove, canRemove }: {
    queuedFile: QueuedFile;
    onRemove: () => void;
    canRemove: boolean;
  }) => {
    const getStatusIcon = () => {
      if (queuedFile.status === 'success') {
        return <span className="text-green-600">✓</span>;
      }
      if (queuedFile.status === 'failed') {
        return <span className="text-destructive">✗</span>;
      }
      if (queuedFile.status === 'uploading') {
        return <span className="text-primary">↻</span>;
      }
      if (queuedFile.validationError) {
        return <span className="text-destructive">!</span>;
      }
      return <span className="text-muted-foreground">○</span>;
    };

    const getStatusBadge = () => {
      if (queuedFile.status === 'uploading') return 'Uploading...';
      if (queuedFile.status === 'success') return 'Success';
      if (queuedFile.status === 'failed') return 'Failed';
      if (queuedFile.validationError) return 'Invalid';
      return 'Waiting';
    };

    return (
      <div className={`flex items-center gap-3 p-3 rounded-md border ${
        queuedFile.status === 'uploading' ? 'bg-primary/5 border-primary' : 'bg-muted/30'
      }`}>
        <FileText className="w-5 h-5 text-muted-foreground flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{queuedFile.file.name}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatFileSize(queuedFile.file.size)}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              {getStatusIcon()}
              {getStatusBadge()}
            </span>
          </div>
          {queuedFile.validationError && (
            <p className="text-xs text-destructive mt-1">{queuedFile.validationError}</p>
          )}
          {queuedFile.error && (
            <p className="text-xs text-destructive mt-1">{queuedFile.error}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRemove}
          disabled={!canRemove}
          title={!canRemove ? 'Cannot remove file during upload' : 'Remove file'}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
    );
  };

  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold mb-4">Upload Document</h2>

      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-primary/50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!selectedFile ? (
          <>
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-2">
              Drag and drop a file here, or click to browse
            </p>
            <p className="text-xs text-muted-foreground mb-4">
              Supported formats: PDF, DOCX, PPTX, TXT, HTML, MD, CSV, JSON, XML, RTF (max {MAX_FILE_SIZE_MB}MB)
            </p>
            <input
              type="file"
              id="file-input"
              className="hidden"
              accept={SUPPORTED_TYPES.join(',')}
              onChange={handleFileInput}
              disabled={isUploading}
              multiple
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => document.getElementById('file-input')?.click()}
              disabled={isUploading}
            >
              Browse Files
            </Button>
          </>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3">
              <FileText className="w-8 h-8 text-primary" />
              <div className="flex-1 text-left">
                <p className="text-sm font-medium">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClear}
                disabled={isUploading}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            <Button
              onClick={handleUpload}
              disabled={isUploading}
              className="w-full"
            >
              {isUploading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </div>
        )}
      </div>

      {validationError && (
        <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{validationError}</p>
        </div>
      )}
    </Card>
  );
}
