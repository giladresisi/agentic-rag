import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Upload, FileText, X, AlertCircle } from 'lucide-react';
import type { ProviderConfig } from '@/types/chat';

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

interface DocumentUploadProps {
  onUpload: (file: File, embeddingConfig?: ProviderConfig) => Promise<void>;
  isUploading: boolean;
  embeddingConfig?: ProviderConfig;
}

export function DocumentUpload({ onUpload, isUploading, embeddingConfig }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

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

  const handleFile = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      setSelectedFile(null);
      return;
    }

    setValidationError(null);
    setSelectedFile(file);
  }, []);

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
        handleFile(files[0]);
      }
    },
    [handleFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      await onUpload(selectedFile, embeddingConfig);
      setSelectedFile(null);
      setValidationError(null);
    } catch (error) {
      // Error is handled by parent component
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setValidationError(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
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
