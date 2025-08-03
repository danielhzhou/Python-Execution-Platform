# Dynamic Filesystem Implementation

## Overview
This implementation makes the filesystem dynamic by automatically refreshing the file tree when terminal commands that affect the filesystem are executed.

## Features Implemented

### 1. Filesystem Command Detection (Backend)
- **File**: `backend/app/services/websocket_service.py`
- **Functionality**: Detects filesystem-changing commands using regex patterns
- **Supported Commands**:
  - File creation: `touch`, `echo >`, `cat >`, `tee`, `nano`, `vim`, `emacs`, `code`
  - Directory creation: `mkdir`
  - Deletion: `rm`, `rmdir`
  - Move/Copy: `mv`, `cp`, `rsync`
  - Directory navigation: `cd`
  - File listing: `ls`, `dir`, `find`, `tree`
  - Archive extraction: `tar`, `unzip`, `gunzip`, `unrar`
  - Git operations: `git clone`, `git checkout`, `git pull`, etc.

### 2. WebSocket Event System
- **New Event Types**:
  - `filesystem_change`: Sent when filesystem commands are detected
  - `directory_change`: Sent when `cd` commands change the current directory
- **Event Data**:
  - Command type and original command
  - Current directory path
  - Timestamp

### 3. Current Directory Tracking
- **Backend**: Tracks current working directory per terminal session
- **Frontend**: Displays current directory in file tree header
- **Path Normalization**: Ensures paths stay within `/workspace` bounds

### 4. Automatic File Tree Refresh
- **Trigger**: Listens for `filesystem_change` events via WebSocket
- **Mechanism**: Uses custom DOM events to communicate between WebSocket hook and FileTree component
- **Timing**: Small delay (1 second) to allow commands to complete before refreshing

### 5. Enhanced UI
- **Current Directory Display**: Shows current directory in Explorer header
- **Refresh Button**: Manual refresh option with loading indicator
- **Real-time Updates**: No manual intervention required

## Technical Implementation

### Backend Changes

#### WebSocketManager Class Updates
```python
# Command pattern detection
self.filesystem_command_patterns = {
    'create_file': re.compile(r'^(touch|echo\s+.*\s*>\s*|...)', re.IGNORECASE),
    'create_dir': re.compile(r'^mkdir\s+', re.IGNORECASE),
    # ... more patterns
}

# Directory tracking
self.current_directories: Dict[str, str] = {}
```

#### Command Processing
```python
# In _handle_terminal_input method
if command.startswith('cd '):
    asyncio.create_task(self._update_current_directory(session_id, command))

is_fs_command, command_type = self._is_filesystem_command(command)
if is_fs_command:
    asyncio.create_task(self._delayed_filesystem_notification(session_id, command_type, command))
```

### Frontend Changes

#### Type Definitions
```typescript
// New WebSocket message types
| { type: 'filesystem_change'; data: { command_type: string; command: string; timestamp: string } }
| { type: 'directory_change'; data: { current_directory: string; timestamp: string } }
```

#### Terminal Store Enhancement
```typescript
interface TerminalState {
  // ... existing fields
  currentDirectory: string;
  setCurrentDirectory: (directory: string) => void;
}
```

#### WebSocket Event Handling
```typescript
// Filesystem change handler
wsRef.current.on('filesystem_change', (message: WebSocketMessage) => {
  const event = new CustomEvent('filesystem-change', {
    detail: { commandType, command, timestamp }
  });
  window.dispatchEvent(event);
});

// Directory change handler  
wsRef.current.on('directory_change', (message: WebSocketMessage) => {
  setCurrentDirectory(message.data.current_directory);
});
```

#### FileTree Auto-Refresh
```typescript
useEffect(() => {
  const handleFilesystemChange = (event: CustomEvent) => {
    setTimeout(() => {
      fetchContainerFiles();
    }, 1000);
  };

  window.addEventListener('filesystem-change', handleFilesystemChange);
  return () => window.removeEventListener('filesystem-change', handleFilesystemChange);
}, [fetchContainerFiles]);
```

## Usage Examples

### Basic File Operations
```bash
# Create a file - triggers file tree refresh
touch new_file.py

# Create directory - triggers file tree refresh  
mkdir my_project

# Navigate to directory - updates current directory display
cd my_project

# Create file in subdirectory - triggers refresh
echo "print('Hello')" > hello.py

# List files - triggers refresh (shows current state)
ls -la
```

### Advanced Operations
```bash
# Git operations - triggers refresh
git clone https://github.com/user/repo.git

# Package installation with file creation
pip install requests  # May create files, triggers refresh

# Archive extraction - triggers refresh
tar -xzf archive.tar.gz
```

## Benefits

1. **Real-time Synchronization**: File tree always reflects current filesystem state
2. **No Manual Intervention**: Automatic updates without user action required
3. **Command Awareness**: System understands which commands affect filesystem
4. **Directory Context**: Always shows current working directory
5. **Performance Optimized**: Only refreshes when necessary, with appropriate delays

## Testing

Use the provided `test_dynamic_filesystem.py` script to verify functionality:

1. Start backend and frontend servers
2. Create a container session
3. Execute filesystem commands in terminal
4. Observe automatic file tree updates
5. Verify current directory display updates

## Future Enhancements

- **File Watching**: Add inotify/fsevents for even more real-time updates
- **Selective Refresh**: Only refresh affected directories instead of full tree
- **Command Output Parsing**: Parse command output for more precise change detection
- **Undo/Redo**: Track filesystem changes for potential undo functionality
- **Conflict Resolution**: Handle concurrent filesystem changes gracefully