import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface UploadErrorDialogProps {
  isOpen: boolean;
  fileName: string;
  error: string;
  filesRemaining: number;
  onContinue: () => void;
  onStop: () => void;
}

export function UploadErrorDialog({
  isOpen,
  fileName,
  error,
  filesRemaining,
  onContinue,
  onStop,
}: UploadErrorDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            Upload Failed
          </DialogTitle>
          <DialogDescription className="pt-2 space-y-2">
            <p className="font-medium text-foreground">
              "{fileName}" failed to upload
            </p>
            <p className="text-sm">{error}</p>
            <p className="text-sm text-muted-foreground">
              {filesRemaining} file{filesRemaining !== 1 ? 's' : ''} remaining in queue
            </p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onStop}>
            Stop uploading
          </Button>
          <Button onClick={onContinue}>
            Continue with next file
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
