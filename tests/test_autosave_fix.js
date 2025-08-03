// Simple test to verify the auto-save fix
// Run this in browser console after loading the app

console.log('🧪 Testing Auto-Save Fix...');

// Check if the app store has the updateFile function
const testUpdateFile = () => {
  try {
    // This would be available in the browser console if the app is loaded
    if (typeof window !== 'undefined' && window.useAppStore) {
      const store = window.useAppStore.getState();
      
      if (typeof store.updateFile === 'function') {
        console.log('✅ updateFile function exists in app store');
        return true;
      } else {
        console.log('❌ updateFile function missing from app store');
        return false;
      }
    } else {
      console.log('⚠️ App store not available (run this in browser with app loaded)');
      return false;
    }
  } catch (error) {
    console.error('❌ Error testing updateFile:', error);
    return false;
  }
};

// Test the function
const result = testUpdateFile();
console.log(result ? '🎉 Auto-save fix should work!' : '🔧 Auto-save still needs fixing');

// Instructions for manual testing
console.log(`
📋 Manual Testing Instructions:
1. Open the Monaco editor
2. Load or create a Python file
3. Start typing in the editor
4. Check browser console for:
   - "✅ File saved successfully: /workspace/filename.py"
   - No "updateFile is not a function" errors
5. Verify file content is preserved when switching files
`);