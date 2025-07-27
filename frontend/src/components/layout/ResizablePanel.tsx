import React, { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '../../lib/utils';

interface ResizablePanelProps {
  children: [React.ReactNode, React.ReactNode];
  direction?: 'horizontal' | 'vertical';
  defaultSize?: number; // Percentage (0-100)
  minSize?: number; // Percentage
  maxSize?: number; // Percentage
  className?: string;
  onResize?: (size: number) => void;
}

export function ResizablePanel({
  children,
  direction = 'horizontal',
  defaultSize = 50,
  minSize = 20,
  maxSize = 80,
  className,
  onResize
}: ResizablePanelProps) {
  const [size, setSize] = useState(defaultSize);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const resizerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    
    let newSize: number;
    
    if (direction === 'horizontal') {
      const mouseX = e.clientX - rect.left;
      newSize = (mouseX / rect.width) * 100;
    } else {
      const mouseY = e.clientY - rect.top;
      newSize = (mouseY / rect.height) * 100;
    }

    // Clamp the size within bounds
    newSize = Math.max(minSize, Math.min(maxSize, newSize));
    
    setSize(newSize);
    onResize?.(newSize);
  }, [isDragging, direction, minSize, maxSize, onResize]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp, direction]);

  const isHorizontal = direction === 'horizontal';
  const firstPanelStyle = isHorizontal 
    ? { width: `${size}%` }
    : { height: `${size}%` };
  const secondPanelStyle = isHorizontal 
    ? { width: `${100 - size}%` }
    : { height: `${100 - size}%` };

  return (
    <div
      ref={containerRef}
      className={cn(
        'flex',
        isHorizontal ? 'flex-row' : 'flex-col',
        'w-full h-full',
        className
      )}
    >
      {/* First Panel */}
      <div
        style={firstPanelStyle}
        className={cn(
          'overflow-hidden',
          isHorizontal ? 'min-w-0' : 'min-h-0'
        )}
      >
        {children[0]}
      </div>

      {/* Resizer */}
      <div
        ref={resizerRef}
        onMouseDown={handleMouseDown}
        className={cn(
          'bg-border hover:bg-border/80 transition-colors flex-shrink-0 group',
          isHorizontal 
            ? 'w-1 cursor-col-resize hover:w-2' 
            : 'h-1 cursor-row-resize hover:h-2',
          isDragging && 'bg-primary',
          'relative'
        )}
      >
        {/* Visual indicator */}
        <div
          className={cn(
            'absolute bg-muted-foreground/20 group-hover:bg-muted-foreground/40 transition-colors',
            isHorizontal 
              ? 'top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-0.5 h-8'
              : 'top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-0.5 w-8',
            isDragging && 'bg-primary/60'
          )}
        />
      </div>

      {/* Second Panel */}
      <div
        style={secondPanelStyle}
        className={cn(
          'overflow-hidden',
          isHorizontal ? 'min-w-0' : 'min-h-0'
        )}
      >
        {children[1]}
      </div>
    </div>
  );
} 