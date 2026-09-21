import React from 'react';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

export interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  isLoading?: boolean;
  isPaperModeNotice?: boolean;
}

export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'warning',
  isLoading = false,
  isPaperModeNotice = true,
}) => {
  const icon = {
    danger: <AlertTriangle className="w-5 h-5 text-rose-400" />,
    warning: <AlertCircle className="w-5 h-5 text-amber-400" />,
    info: <Info className="w-5 h-5 text-sky-400" />,
  }[variant];

  const confirmVariant = {
    danger: 'danger' as const,
    warning: 'primary' as const,
    info: 'primary' as const,
  }[variant];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>
            {cancelLabel}
          </Button>
          <Button
            variant={confirmVariant}
            size="sm"
            onClick={onConfirm}
            isLoading={isLoading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 flex-shrink-0">
            {icon}
          </div>
          <div className="text-sm text-slate-300 leading-relaxed pt-1">
            {message}
          </div>
        </div>

        {isPaperModeNotice && (
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-2.5 text-center">
            <span className="text-[11px] font-mono text-amber-300 font-bold uppercase tracking-wider">
              SIMULATED PAPER EXECUTION — $0.00 REAL CAPITAL AT RISK
            </span>
          </div>
        )}
      </div>
    </Modal>
  );
};
