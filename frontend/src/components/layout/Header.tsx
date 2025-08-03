import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useAppStore } from '../../stores/appStore';
import { useEditorStore } from '../../stores/editorStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { Button } from '../ui/button';
import { 
  LogOut,
  Code,
  Wifi,
  WifiOff,
  User
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const { 
    user, 
    currentContainer, 
    error,
    logout
  } = useAppStore();
  
  const { isDirty } = useEditorStore();
  const { isConnected } = useTerminalStore();
  
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, right: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);

  const updateMenuPosition = () => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + 8, // 8px gap below button
        right: window.innerWidth - rect.right, // Distance from right edge
      });
    }
  };

  const toggleUserMenu = () => {
    if (!showUserMenu) {
      updateMenuPosition();
    }
    setShowUserMenu(!showUserMenu);
  };

  // Update position on window resize
  useEffect(() => {
    if (showUserMenu) {
      const handleResize = () => updateMenuPosition();
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, [showUserMenu]);

  return (
    <header className={cn(
      'flex items-center justify-between h-14 px-6 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
      className
    )}>
      {/* Left Section - Clean Logo */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10">
            <Code className="h-4 w-4 text-primary" />
          </div>
          <span className="text-lg font-semibold text-foreground">
            CodePlatform
          </span>
        </div>
        
        {/* Compact Status Bar */}
        <div className="flex items-center gap-4 text-xs">
          {currentContainer && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/50">
              <div className={cn(
                'w-1.5 h-1.5 rounded-full',
                currentContainer.status === 'running' ? 'bg-emerald-500' : 
                currentContainer.status === 'stopped' ? 'bg-red-500' : 
                'bg-amber-500'
              )} />
              <span className="text-muted-foreground font-medium">
                {currentContainer.status === 'running' ? 'Ready' : 'Starting...'}
              </span>
            </div>
          )}
          
          {isDirty && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-500/10 text-amber-600 border border-amber-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
              <span className="font-medium">Unsaved Changes</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Section - User & Actions */}
      <div className="flex items-center gap-3">
        {/* Quick Status */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className={cn(
            'flex items-center gap-1',
            isConnected ? 'text-emerald-600' : 'text-red-600'
          )}>
            {isConnected ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            <span className="font-medium">
              {isConnected ? 'Connected' : 'Offline'}
            </span>
          </div>
        </div>
        
        <div className="w-px h-4 bg-border" />
        
        {/* User Menu */}
        <div className="relative">
          <Button
            ref={buttonRef}
            variant="ghost"
            size="sm"
            onClick={toggleUserMenu}
            className="gap-2 h-8 px-3"
          >
            <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
              <User className="h-3 w-3 text-primary" />
            </div>
            <span className="text-sm font-medium">
              {user?.email?.split('@')[0] || 'User'}
            </span>
          </Button>
          

        </div>
      </div>
      
      {/* User Menu Dropdown - Portaled */}
      {showUserMenu && createPortal(
        <div 
          className="fixed w-56 bg-background border rounded-lg shadow-lg z-[9999] p-1"
          style={{
            top: `${menuPosition.top}px`,
            right: `${menuPosition.right}px`,
          }}
        >
          <div className="px-3 py-2 border-b border-border/50">
            <div className="text-sm font-medium">{user?.email?.split('@')[0] || 'User'}</div>
            <div className="text-xs text-muted-foreground">{user?.email || 'Anonymous User'}</div>
            <div className="text-xs text-muted-foreground mt-1 capitalize">
              Role: {user?.role || 'submitter'}
            </div>
          </div>
          
          <div className="py-1">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start h-8 px-3 text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={async () => {
                setShowUserMenu(false);
                await logout();
              }}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </div>,
        document.body
      )}
      
      {/* Backdrop for user menu */}
      {showUserMenu && (
        <div 
          className="fixed inset-0 z-[9998]" 
          onClick={() => setShowUserMenu(false)}
        />
      )}
      
      {/* Error Toast */}
      {error && (
        <div className="fixed top-16 right-4 z-[9997] max-w-sm">
          <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 rounded-lg shadow-lg">
            <div className="text-sm font-medium">Error</div>
            <div className="text-xs opacity-90">{typeof error === 'string' ? error : 'Something went wrong'}</div>
          </div>
        </div>
      )}
    </header>
  );
}    