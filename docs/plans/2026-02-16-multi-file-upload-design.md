# Multi-File Upload Design

**Date:** 2026-02-16
**Status:** Approved
**Complexity:** ⚠️ Medium

## Overview

Enhance the document upload feature to support multiple files instead of single file uploads. Users can select multiple files, review and curate the queue, then upload sequentially with interactive error handling.

## Requirements

- **Multi-file selection:** Support drag-and-drop and file picker for multiple files
- **Queue management:** Display all selected files with ability to remove individual files
- **Sequential upload:** Upload one file at a time (not parallel)
- **Interactive error handling:** On failure, ask user whether to continue with remaining files or stop
- **No file limit:** Allow unlimited number of files in queue
- **Backward compatible:** Single file upload still works

## Approach

**Frontend Queue Manager (Frontend-only changes)**

- Frontend manages queue of files before upload
- Users review, reorder, and remove files from queue
- Upload to existing `/upload` endpoint sequentially
- No backend changes required

## Architecture

### Components Modified

1. **DocumentUpload.tsx**
   - Accept multiple files via drag-and-drop and file picker
   - Show file queue with remove buttons
   - Manage sequential upload state
   - Display error dialog on upload failure

2. **IngestionInterface.tsx**
   - Minor updates to handle upload completion callback

3. **useIngestion hook** (if modifications needed)
   - Track current upload in multi-file context

### State Management

```typescript
interface QueuedFile {
  file: File;
  id: string; // unique ID for React keys
  status: 'pending' | 'uploading' | 'success' | 'failed';
  error?: string;
}

const [fileQueue, setFileQueue] = useState<QueuedFile[]>([]);
const [currentUploadIndex, setCurrentUploadIndex] = useState<number>(-1);
const [isPaused, setIsPaused] = useState(false);
```

### Backend Changes

None - use existing `/upload` endpoint as-is.

## UI/UX Design

### File Selection Area

- Existing drag-and-drop zone
- File input updated with `multiple` attribute
- Files validated individually on selection
- Invalid files shown with error message but don't block valid ones

### File Queue Display

Replace single-file preview with scrollable list:

**Each queue item shows:**
- File icon + name
- File size
- Validation status (✓ valid or ✗ invalid with reason)
- Remove button (X)
- Upload status badge (Waiting → Uploading → Success/Failed)

### Upload Controls

- **"Upload All" button** (replaces "Upload Document")
  - Disabled if queue empty or all files invalid
  - Shows "Uploading X of Y..." during upload
- **"Clear All" button** to empty queue

### Progress Feedback

- Current file uploading highlighted
- Text shows "Uploading file 3 of 5..."
- Completed files show green checkmark or red X
- Supabase Realtime shows processing status after upload

### Error Dialog (on failure)

Modal popup with:
- Title: "Upload Failed"
- Message: "{fileName} failed to upload: {error}"
- Info: "{filesRemaining} files remaining in queue"
- Actions: "Continue with next file" | "Stop uploading"

### Summary (after completion)

- "Upload complete: 4 succeeded, 1 failed"
- Option to retry failed files or clear queue

## Data Flow

### Sequential Upload Logic

1. User clicks "Upload All" → `currentUploadIndex = 0`
2. Upload `fileQueue[0]` → update status to 'uploading'
3. Wait for upload completion (success or failure)
4. **If success:** Move to next file (`currentUploadIndex++`)
5. **If failure:**
   - Pause upload (`isPaused = true`)
   - Show error dialog
   - If user clicks "Continue" → `isPaused = false`, move to next file
   - If user clicks "Stop" → `currentUploadIndex = -1`, end upload
6. Repeat until all files processed or user stops

### File Addition

- Validate each file as added
- Invalid files added to queue but marked with error
- Don't prevent adding invalid files (user sees why they're invalid)

### File Removal

- Can remove any file except currently uploading one
- Currently uploading file's remove button disabled with tooltip

### Upload Completion

- Each successful upload triggers Supabase Realtime for processing status
- DocumentList updates in real-time as before

## Error Handling

### Validation Errors (before upload)

- File too large → Show error in queue item
- Unsupported file type → Show error in queue item
- Invalid files don't prevent uploading valid ones
- "Upload All" button skips invalid files automatically

### Upload Errors (during sequential upload)

- Network failure → Pause, show dialog with error
- Backend 400/500 error → Pause, show dialog with API error message
- Timeout → Pause, show dialog offering to retry or skip

### Error Dialog Component

```typescript
interface ErrorDialogProps {
  fileName: string;
  error: string;
  filesRemaining: number;
  onContinue: () => void;
  onStop: () => void;
}
```

### Retry Logic

- No automatic retry
- Failed files remain in queue with "failed" status
- User can retry failed files via "Retry Failed Files" button

### Edge Cases

- User closes browser during upload → Clean state on next session (no persistence)
- Duplicate file detection → Backend handles via hash check (unchanged)
- Network reconnect → No special handling, next attempt fails/succeeds normally

## Testing Strategy

### Unit Tests (Frontend)

- File validation logic (size, type)
- Queue operations (add, remove, clear)
- State transitions during sequential upload
- Error dialog triggering

### Integration Tests (Playwright E2E)

1. **Multi-file selection:**
   - Select 3 valid files via file picker → all in queue
   - Drag and drop 3 files → all in queue
   - Mix valid/invalid files → invalid show errors

2. **Queue management:**
   - Remove file from queue → disappears
   - Clear all files → queue empties
   - Cannot remove currently uploading file

3. **Sequential upload happy path:**
   - Upload 3 files → all succeed sequentially
   - Each file appears in DocumentList after processing
   - Supabase Realtime updates work for each file

4. **Error handling:**
   - Upload file that fails → error dialog appears
   - Click "Continue" → next file uploads
   - Click "Stop" → upload stops
   - Failed files remain in queue with error

5. **Summary display:**
   - After mixed success/failure → correct counts
   - Retry failed files → only failed ones re-upload

### Manual Testing

- Test with 10+ files (performance)
- Test with very large files (close to 10MB limit)
- Verify UI doesn't freeze
- Check browser console for errors

### Backward Compatibility

- Single file upload still works (selecting 1 file behaves as before)

## Implementation Notes

- Keep existing validation constants in sync (frontend/backend)
- Reuse existing error handling from parent component
- Leverage existing Supabase Realtime for processing status
- No changes to backend `/upload` endpoint
- All changes contained in frontend DocumentUpload component

## Success Criteria

- Users can select and upload multiple files
- File queue displays correctly with remove functionality
- Sequential uploads work with proper status updates
- Error dialog appears on failure with continue/stop options
- Upload summary shows accurate success/failure counts
- All existing tests pass
- New E2E tests pass
- Backward compatible with single-file uploads
