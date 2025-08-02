# Race Condition Fixes for App Initialization

## Issues Identified

The app was experiencing race conditions during initialization, particularly on page refresh, causing:
- WebSocket connection errors
- "File tree not found" errors  
- "Failed to connect to terminal" errors
- Components attempting to initialize before dependencies were ready

## Root Causes

1. **Timing Dependencies**: Components tried to initialize before their dependencies were ready
2. **No Container Readiness Check**: WebSocket and FileTree attempted connections before containers were fully operational
3. **Missing Retry Logic**: Temporary failures caused permanent errors instead of recovery
4. **Insufficient Error Handling**: Race condition errors weren't distinguished from permanent failures

## Fixes Implemented

### 1. WebSocket Connection Timing (`useWebSocket.ts`)
- **Added Container Readiness Check**: WebSocket now waits for container status to be 'running'
- **Added Readiness Polling**: `waitForContainerReady()` function with 10-second timeout
- **Improved Retry Logic**: Exponential backoff with jitter for reconnection attempts
- **Better Error Messaging**: Distinguish between temporary and permanent connection failures

### 2. File Tree Error Handling (`FileTree.tsx`)
- **Added Retry Logic**: Automatically retries failed file loads up to 3 times
- **Smart Error Detection**: Identifies container-not-ready errors vs permanent failures
- **Progressive Backoff**: Increasing delays between retry attempts
- **Better Error Context**: More detailed error logging for debugging

### 3. Terminal Initialization (`Terminal.tsx`)
- **Delayed WebSocket Connection**: 500ms delay after terminal initialization before connecting
- **Better Dependency Tracking**: Ensures terminal is fully ready before connection attempts
- **Improved Logging**: More detailed connection state tracking

### 4. Container Management (`useContainer.ts`)
- **Status Polling**: Regular 15-second polling to detect container state changes
- **Health Monitoring**: Automatic detection and recovery from status mismatches
- **Force Refresh**: Ability to bypass cache when checking container status

### 5. App-Level Coordination (`App.tsx`)
- **Delayed Container Creation**: 1-second delay to ensure auth state is settled
- **Better State Tracking**: Comprehensive debug logging of initialization flow
- **Error Recovery**: Proper cleanup and retry mechanisms

### 6. WebSocket Manager (`websocket.ts`)
- **Exponential Backoff**: Improved reconnection strategy with jitter
- **Connection Health**: Regular health checks and automatic recovery
- **Better Error Reporting**: Clear distinction between temporary and permanent failures

## Expected Behavior After Fixes

1. **On Page Refresh**:
   - Auth check completes first
   - Container loading waits for auth
   - WebSocket waits for container readiness
   - File tree waits for container + small buffer
   - Terminal connects after initialization + readiness check

2. **Error Recovery**:
   - Temporary connection failures automatically retry
   - Container not ready errors wait and retry
   - WebSocket disconnections trigger automatic reconnection
   - File loading failures retry with progressive backoff

3. **Better User Experience**:
   - Fewer error messages during normal initialization
   - Faster recovery from temporary issues
   - More informative error messages when real problems occur
   - Smoother initialization flow

## Testing Recommendations

1. **Refresh Testing**: Refresh the page multiple times to ensure consistent initialization
2. **Network Simulation**: Test with slow network to verify retry logic
3. **Container Restart**: Test behavior when containers are restarted externally
4. **Multiple Tabs**: Ensure multiple browser tabs don't interfere with each other

## Monitoring

The enhanced logging will help track:
- Component initialization order
- Container readiness timing
- WebSocket connection attempts and failures
- File tree loading success/failure rates
- Overall initialization flow health