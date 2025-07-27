# Python Execution Platform - Frontend

A modern, browser-based IDE for Python development with integrated terminal, code execution, and review workflow.

## Features

### 🖥️ Monaco Editor
- **Full Python syntax highlighting** with autocomplete
- **Auto-save functionality** with debounced saves
- **Keyboard shortcuts** (Ctrl+S to save, Ctrl+Enter to run)
- **Real-time syntax validation** with error highlighting
- **Customizable themes** (VS Dark, VS Light, High Contrast)
- **Code folding** and bracket matching
- **Multi-cursor editing** and find/replace

### 🖥️ Integrated Terminal
- **Full xterm.js terminal** with native capabilities
- **WebSocket connection** to backend containers
- **Command history** with arrow key navigation
- **Real-time output** streaming
- **Copy/paste support** and text selection
- **Customizable themes** and font settings
- **Terminal resizing** and proper PTY handling

### 🐳 Container Management
- **Docker container lifecycle** management
- **Real-time status** indicators
- **Multiple container** support
- **Auto-creation** of containers when needed
- **Resource monitoring** and cleanup

### 📁 File Management
- **File browser** with hierarchical view
- **Create, edit, delete** files
- **File type detection** and appropriate syntax highlighting
- **Persistent storage** integration with backend

### 🔄 Code Submission & Review
- **Submit code** for instructor/peer review
- **Rich submission dialog** with metadata
- **Code preview** and validation
- **Submission guidelines** and best practices
- **Review workflow** (for reviewers)

### 🎨 Modern UI/UX
- **Responsive design** that works on all screen sizes
- **Dark/light theme** support
- **Resizable panels** for optimal workflow
- **Toast notifications** for user feedback
- **Loading states** and error handling
- **Keyboard shortcuts** and accessibility

## Technology Stack

- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** with custom design system
- **shadcn/ui** for consistent UI components
- **Monaco Editor** (VS Code editor engine)
- **xterm.js** for terminal emulation
- **Zustand** for state management
- **WebSockets** for real-time communication

## Getting Started

### Prerequisites
- Node.js 18+ or Bun runtime
- Backend API running (see backend README)

### Installation

```bash
# Install dependencies
bun install

# Start development server
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview
```

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Architecture

### State Management
The application uses Zustand for state management with three main stores:

- **`appStore`** - Global application state, user data, containers, files
- **`editorStore`** - Monaco editor configuration, content, auto-save settings
- **`terminalStore`** - Terminal state, WebSocket connection, command history

### Component Structure
```
src/
├── components/
│   ├── ui/              # Base UI components (shadcn/ui)
│   ├── editor/          # Monaco Editor components
│   ├── terminal/        # Terminal components
│   ├── layout/          # Layout and navigation
│   └── common/          # Shared components
├── hooks/               # Custom React hooks
├── stores/              # Zustand state stores
├── lib/                 # Utilities and API clients
└── types/               # TypeScript type definitions
```

### Key Components

#### MonacoEditor
- Full-featured code editor with Python support
- Auto-save with debouncing
- Syntax validation and error highlighting
- Keyboard shortcuts and customization

#### Terminal
- xterm.js-based terminal emulation
- WebSocket integration for real-time communication
- Command history and navigation
- Copy/paste and text selection

#### ResizablePanel
- Custom resizable panel implementation
- Horizontal and vertical splitting
- Configurable size constraints
- Smooth resize interactions

## Usage Guide

### Basic Workflow

1. **Start Coding**: Open the application and start typing Python code in the Monaco editor
2. **Run Code**: Use Ctrl+Enter or click "Run Code" to execute in the terminal
3. **Terminal Commands**: Use the integrated terminal for `pip install`, `ls`, `cat`, etc.
4. **Save Work**: Code auto-saves, or use Ctrl+S for manual save
5. **Submit**: Click "Submit" to send code for review

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save file |
| `Ctrl+Enter` | Run code |
| `Ctrl+\`` | Focus terminal |
| `Ctrl+/` | Toggle comment |
| `F1` | Command palette |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find and replace |

### Terminal Commands

The terminal supports all standard bash commands plus Python-specific commands:

```bash
# Python execution
python script.py
python3 -c "print('Hello, World!')"

# Package management
pip install pandas numpy matplotlib
pip list
pip freeze > requirements.txt

# File operations
ls -la
cat script.py
mkdir project
cd project

# Git operations (if available)
git init
git add .
git commit -m "Initial commit"
```

### File Management

- **Create Files**: Use the "New File" button in the sidebar
- **Switch Files**: Click on files in the file browser
- **File Sync**: Files are automatically synced between editor and terminal
- **Persistent Storage**: All files are saved to the backend database

### Code Submission

1. Click the "Submit" button in the header
2. Fill out the submission form:
   - **Title**: Descriptive name for your submission
   - **Description**: Optional details about your code
3. Review the code preview
4. Click "Submit for Review"

## Development

### Adding New Components

1. Create component in appropriate directory
2. Follow TypeScript and React best practices
3. Use shadcn/ui components for consistency
4. Add proper error handling and loading states

### State Management

Use Zustand stores for shared state:

```typescript
// Reading state
const { user, currentContainer } = useAppStore();

// Updating state
const { setUser, setError } = useAppStore();
```

### API Integration

Use the provided API utilities:

```typescript
import { containerApi, fileApi } from '../lib/api';

// Create container
const response = await containerApi.create();
if (response.success) {
  // Handle success
}
```

### WebSocket Integration

Use the WebSocket hook for real-time communication:

```typescript
const { connect, disconnect, sendCommand } = useWebSocket();

// Connect to terminal
await connect();

// Send command
sendCommand('python script.py');
```

## Performance Considerations

- **Code Splitting**: Components are lazy-loaded where appropriate
- **Debounced Auto-save**: Prevents excessive API calls
- **Virtual Scrolling**: Used in file lists and terminal output
- **Optimized Re-renders**: React.memo and useCallback used strategically

## Browser Support

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

## Contributing

1. Follow the established code style
2. Add TypeScript types for all new code
3. Include error handling and loading states
4. Test on multiple browsers
5. Update documentation as needed

## Troubleshooting

### Common Issues

**Editor not loading**: Check if Monaco Editor assets are properly served
**Terminal not connecting**: Verify WebSocket URL and backend connectivity
**Auto-save not working**: Check network connectivity and API endpoints
**Styles not loading**: Ensure Tailwind CSS is properly configured

### Debug Mode

Enable debug logging by setting:
```javascript
localStorage.setItem('debug', 'true');
```

This will enable detailed logging in the browser console. 