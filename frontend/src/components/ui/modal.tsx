import { ReactNode } from 'react';
import { Button } from './button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  type?: 'success' | 'error' | 'info';
  showCloseButton?: boolean;
}

export function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  type = 'info',
  showCloseButton = true 
}: ModalProps) {
  if (!isOpen) return null;

  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return {
          iconBg: 'bg-green-100',
          iconColor: 'text-green-600',
          icon: '✓'
        };
      case 'error':
        return {
          iconBg: 'bg-red-100',
          iconColor: 'text-red-600',
          icon: '✕'
        };
      default:
        return {
          iconBg: 'bg-blue-100',
          iconColor: 'text-blue-600',
          icon: 'ℹ'
        };
    }
  };

  const styles = getTypeStyles();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex items-center space-x-3 mb-4">
          <div className={`w-10 h-10 rounded-full ${styles.iconBg} flex items-center justify-center`}>
            <span className={`text-lg font-bold ${styles.iconColor}`}>
              {styles.icon}
            </span>
          </div>
          <h2 className="text-xl font-semibold">{title}</h2>
        </div>
        
        <div className="mb-6">
          {children}
        </div>
        
        {showCloseButton && (
          <div className="flex justify-end">
            <Button onClick={onClose}>
              OK
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

interface SuccessModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
}

export function SuccessModal({ isOpen, onClose, title, message }: SuccessModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} type="success">
      <p className="text-gray-700">{message}</p>
    </Modal>
  );
}

interface ErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
}

export function ErrorModal({ isOpen, onClose, title, message }: ErrorModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} type="error">
      <p className="text-gray-700">{message}</p>
    </Modal>
  );
}