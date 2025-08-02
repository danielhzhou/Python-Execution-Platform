# Security Recommendations for Terminal Access

## Current Security Assessment

### ⚠️ Issue: Unrestricted Terminal Access
Users currently get full bash shell access via `docker exec -it`, allowing:
- Navigation outside `/workspace` with `cd ..`
- Reading system files (`/etc/passwd`, `/proc/*`, etc.)
- Exploring container internals
- Potential information disclosure

## Recommended Security Enhancements

### 1. 🔒 Restricted Shell (chroot jail)
```bash
# Option A: Use chroot to restrict filesystem access
RUN mkdir -p /workspace-jail
COPY --chown=pyuser:pyuser /workspace /workspace-jail/workspace
# Then chroot the user to /workspace-jail
```

### 2. 🛡️ Custom Shell Wrapper
```python
# Create a restricted shell that intercepts cd commands
class RestrictedShell:
    def __init__(self, allowed_paths=["/workspace"]):
        self.allowed_paths = allowed_paths
    
    def validate_cd(self, path):
        resolved = os.path.realpath(path)
        return any(resolved.startswith(allowed) for allowed in self.allowed_paths)
```

### 3. 🔐 Container Hardening
```dockerfile
# Remove unnecessary system tools
RUN rm -rf /bin/su /bin/sudo /usr/bin/passwd
# Remove shell history
RUN rm -f /home/pyuser/.bash_history
# Limit process visibility
RUN mount -t proc proc /proc -o hidepid=2
```

### 4. 🚧 Directory Binding
```python
# Mount only /workspace as writable, rest as read-only
volumes=[
    ("/workspace", "/workspace", "rw"),
    ("/usr", "/usr", "ro"),
    ("/etc", "/etc", "ro")
]
```

### 5. 🔍 Command Filtering
```python
# In WebSocket service, filter dangerous commands
BLOCKED_COMMANDS = [
    r'^cd\s+\.\.(/.*)?$',  # Block cd .. 
    r'^cd\s+/(?!workspace)',  # Block cd to non-workspace
    r'^cat\s+/etc/',  # Block reading system files
    r'^ls\s+/(?!workspace)',  # Block listing system dirs
]

def is_command_allowed(command: str) -> bool:
    return not any(re.match(pattern, command) for pattern in BLOCKED_COMMANDS)
```

## Implementation Priority

### 🚨 High Priority (Implement Soon)
1. **Command Filtering** - Quick win, filter `cd ..` and system access
2. **Path Validation** - Validate all cd commands stay in /workspace
3. **System File Protection** - Block access to /etc, /proc, /sys

### 🔒 Medium Priority  
1. **Container Hardening** - Remove unnecessary tools
2. **Read-only Mounts** - Mount system directories as read-only
3. **Process Isolation** - Hide other processes

### 🛡️ Long Term
1. **Custom Shell** - Build restricted shell environment
2. **Chroot Jail** - Complete filesystem isolation
3. **Security Auditing** - Log all command attempts

## Quick Fix for Current Issue

```python
# In websocket_service.py, add validation:
async def _handle_terminal_input(self, session_id: str, input_data: str):
    # ... existing code ...
    
    if input_data in ['\r', '\n', '\r\n']:
        command = self.command_buffers[session_id].strip()
        
        # SECURITY: Block dangerous navigation
        if not self._is_command_safe(command):
            await self._send_security_warning(session_id, command)
            return
            
        # ... rest of existing code ...

def _is_command_safe(self, command: str) -> bool:
    """Check if command is safe to execute"""
    dangerous_patterns = [
        r'^cd\s+\.\.(/.*)?$',  # cd ..
        r'^cd\s+/(?!workspace)',  # cd /anywhere-not-workspace
        r'^cat\s+/etc/',  # reading system files
        r'^ls\s+/(?!workspace)',  # listing system dirs
    ]
    
    return not any(re.match(pattern, command, re.IGNORECASE) 
                   for pattern in dangerous_patterns)
```

## Conclusion

The current `cd ..` access is a **legitimate security concern** that should be addressed. While the container provides isolation, allowing unrestricted filesystem navigation within the container is not ideal for a secure learning environment.

**Immediate Action**: Implement command filtering to block `cd ..` and system directory access.
**Long-term**: Consider implementing a more restricted shell environment.