# Monaco Editor ↔ Docker Container Integration

## Overview

This document explains how the Monaco Editor is now directly connected to the Docker container filesystem, enabling real-time synchronization between the web-based editor and the container's execution environment.

## Architecture Changes

### Before (Broken Integration)
```
Monaco Editor → Supabase Storage (isolated)
                     ↕ (no sync)
Docker Container → /workspace/ filesystem (isolated)
```

### After (Integrated System)
```
Monaco Editor → Container Files API → Docker Container /workspace/
                                           ↕
Terminal/Execution ← Docker Container /workspace/
```

## Key Components

### 1. Container Files API (`/containers/{id}/files`)

**Endpoints:**
- `GET /containers/{id}/files` - List files in container
- `GET /containers/{id}/files/content?path=...` - Get file content
- `POST /containers/{id}/files` - Save file to container
- `DELETE /containers/{id}/files?path=...` - Delete file from container
- `POST /containers/{id}/directories?path=...` - Create directory
- `POST /containers/{id}/files/rename` - Rename/move files

**Implementation:**
- Uses Docker `exec_run()` to execute commands directly in containers
- Base64 encoding for safe content transfer
- Proper error handling and permissions (user 1000:1000)

### 2. Frontend Integration

**File API Client (`frontend/src/lib/api.ts`):**
```typescript
export const fileApi = {
  async save(containerId: string, path: string, content: string)
  async get(containerId: string, path: string)
  async list(containerId: string)
  // ... other operations
}
```

**Auto-Save Hook (`frontend/src/hooks/useAutoSave.ts`):**
- Automatically saves Monaco editor changes to container
- Debounced saving (configurable delay)
- Error handling and user feedback

**File Tree (`frontend/src/components/layout/FileTree.tsx`):**
- Lists files directly from container filesystem
- Loads files into Monaco editor
- Real-time file browser

### 3. Execution Flow

1. **Edit Code**: User types in Monaco Editor
2. **Auto-Save**: Content automatically saved to container via API
3. **Execute**: Run button executes the actual file in the container
4. **Terminal Output**: Results shown in integrated terminal

## File Operations

### Creating Files
```typescript
await fileApi.save(containerId, '/workspace/myfile.py', content)
```

### Reading Files
```typescript
const result = await fileApi.get(containerId, '/workspace/myfile.py')
console.log(result.data.content)
```

### Listing Files
```typescript
const files = await fileApi.list(containerId)
// Returns: [{ name, path, type, size }, ...]
```

## Security Features

- **User Isolation**: Each user gets their own container
- **Path Validation**: All file paths are validated
- **Permission Control**: Files created with proper ownership (1000:1000)
- **Network Isolation**: Containers start with no network access
- **Resource Limits**: CPU and memory limits enforced

## Error Handling

- **Container Not Found**: Returns 404 if container doesn't exist
- **Access Denied**: Returns 403 if user doesn't own container
- **File Not Found**: Returns 404 for missing files
- **Write Failures**: Detailed error messages for file operations
- **Auto-Retry**: Frontend automatically retries failed operations

## Testing

Run the integration test:
```bash
python test_monaco_docker_integration.py
```

This test verifies:
- ✅ Authentication
- ✅ Container creation
- ✅ File CRUD operations
- ✅ Directory creation
- ✅ Content synchronization

## Benefits

1. **Real-time Sync**: Changes in editor immediately available in container
2. **True Execution**: Code runs from actual files, not temporary copies
3. **File Management**: Full file tree browsing and management
4. **Auto-Save**: Never lose work with automatic saving
5. **Consistency**: What you see is what executes

## Usage Examples

### Basic File Editing
1. Open Monaco Editor
2. Select or create a Python file
3. Edit the code
4. Changes auto-save to container
5. Click "Run" to execute

### File Management
1. Use file tree to browse container files
2. Create new files and directories
3. Rename/move files as needed
4. Delete unwanted files

### Code Execution
1. Edit your Python code
2. Code is automatically saved to `/workspace/filename.py`
3. Terminal executes: `python3 /workspace/filename.py`
4. Output appears in integrated terminal

## Technical Details

### Container File Storage
- **Location**: `/workspace/` directory in container
- **Permissions**: Files owned by user 1000:1000 (non-root)
- **Encoding**: UTF-8 with base64 transfer encoding
- **Persistence**: Files persist for container lifetime

### API Communication
- **Authentication**: Bearer token authentication
- **Content-Type**: `application/json`
- **Error Format**: Consistent error response structure
- **Rate Limiting**: Built-in protection against abuse

### WebSocket Integration
- **Terminal I/O**: Real-time terminal communication
- **File Events**: (Future) Real-time file change notifications
- **Connection Management**: Automatic reconnection handling

## Future Enhancements

1. **Real-time Collaboration**: Multiple users editing same files
2. **File Watchers**: Automatic refresh when files change externally
3. **Git Integration**: Version control within containers
4. **Package Management**: GUI for pip install operations
5. **File Upload/Download**: Drag-and-drop file operations

## Troubleshooting

### Common Issues

**Files not saving:**
- Check browser console for API errors
- Verify container is running
- Check authentication token

**Execution not working:**
- Ensure file is saved before execution
- Check file permissions in container
- Verify Python syntax

**File tree not loading:**
- Check container status
- Verify API connectivity
- Look for Docker daemon issues

### Debug Commands

```bash
# Check container status
docker ps

# Inspect container files
docker exec -it <container_id> ls -la /workspace/

# Check container logs
docker logs <container_id>
```

## Conclusion

The Monaco Editor is now fully integrated with the Docker container filesystem, providing a seamless development experience where code editing, file management, and execution all work together in a unified environment.