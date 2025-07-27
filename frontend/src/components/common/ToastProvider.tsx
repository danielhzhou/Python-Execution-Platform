import React from 'react';
import {
  ToastProvider as RadixToastProvider,
  ToastViewport,
} from '../ui/toast';

interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <RadixToastProvider>
      {children}
      <ToastViewport />
    </RadixToastProvider>
  );
} 