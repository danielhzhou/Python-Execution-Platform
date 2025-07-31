# 🔍 Debug File Save Issue

## Problem
Monaco editor changes are not being saved to the Docker container. The execution shows old code instead of edited code.

## Debugging Steps

### Step 1: Check Browser Console Logs
When you edit the code in Monaco Editor, you should see these logs:

```
🔄 Editor content changed: {oldLength: 522, newLength: 525, preview: "# Welcome to Python Execution Platform..."}
```

**If you DON'T see this log:**
- The Monaco editor change handler isn't working
- Content isn't being updated in the store

### Step 2: Check Auto-Save Logs
After editing, you should see auto-save logs (after 2 second delay):

```
💾 Auto-saving file: {path: "/workspace/main.py", containerId: "...", contentLength: 525, contentPreview: "# Welcome to Python Execution Platform..."}
📤 Sending save request to API...
📥 Save response received: {success: true, data: {...}}
✅ File saved successfully: /workspace/main.py
```

**If you DON'T see these logs:**
- Auto-save isn't triggering
- Check if `autoSaveEnabled` is true
- Check if `isDirty` flag is being set

### Step 3: Check Manual Save Before Execution
When you click "Run", you should see:

```
🔄 Saving file before execution: {path: "/workspace/main.py", contentLength: 525, contentPreview: "# Welcome to Python Execution Platform..."}
💾 Auto-saving file: {path: "/workspace/main.py", ...}
✅ File saved successfully before execution
```

**If the contentPreview shows OLD content:**
- The editor content isn't being updated in the store
- There's a sync issue between Monaco and the store

### Step 4: Check Backend Logs
In your backend logs, you should see:

```
🔄 SAVE REQUEST: Saving file /workspace/main.py in container ...
📝 Content preview: # Welcome to Python Execution Platform...
📊 Content length: 525 characters
✅ Successfully saved and verified file /workspace/main.py (525 bytes)
```

**If you DON'T see these logs:**
- The save request isn't reaching the backend
- Check network tab for failed requests

### Step 5: Manual Test
Run the test script to verify the API works:

```bash
python test_manual_save.py
```

This will:
1. Save your exact edited content via API
2. Read it back to verify it was saved
3. Show if the issue is in the API or frontend

## Common Issues & Solutions

### Issue 1: Content Not Updating in Store
**Symptoms:** Browser console shows old content in save logs
**Solution:** Check if `setContent()` is being called in `handleEditorChange`

### Issue 2: Auto-Save Not Triggering
**Symptoms:** No auto-save logs after editing
**Solution:** Check if `isDirty` flag is being set when content changes

### Issue 3: API Request Failing
**Symptoms:** 500 errors in network tab, backend error logs
**Solution:** Check container permissions, Docker daemon status

### Issue 4: Race Condition
**Symptoms:** Save appears to work but execution shows old code
**Solution:** Increase delay in execution flow, verify save completion

## Quick Fixes to Try

### Fix 1: Force Save Before Execution
Add this to your browser console:
```javascript
// Force save current content
const store = window.useEditorStore?.getState();
if (store) {
  console.log('Current content:', store.content.substring(0, 100));
}
```

### Fix 2: Check Store State
```javascript
// Check if content is in the store
const editorStore = window.useEditorStore?.getState();
const appStore = window.useAppStore?.getState();
console.log('Editor content:', editorStore?.content?.substring(0, 100));
console.log('Current file:', appStore?.currentFile?.path);
```

### Fix 3: Manual API Test
```javascript
// Test save API directly
fetch('/api/containers/YOUR_CONTAINER_ID/files', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    path: '/workspace/main.py',
    content: 'print("Direct API test")'
  })
}).then(r => r.json()).then(console.log);
```

## Next Steps

1. **Open browser dev tools** (F12)
2. **Go to Console tab**
3. **Edit code in Monaco Editor**
4. **Watch for the debug logs above**
5. **Run the test script** to verify API functionality
6. **Report back which logs you see/don't see**

This will help pinpoint exactly where the save process is failing!