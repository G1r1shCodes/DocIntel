import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface NavButtonProps {
  label: string;
  icon: LucideIcon;
  isActive: boolean;
  onClick: () => void;
  rightElement?: React.ReactNode;
}

export function NavButton({ label, icon: Icon, isActive, onClick, rightElement }: NavButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg font-medium text-sm transition-colors focus:outline-none ${
        isActive
          ? 'bg-accent-light text-accent border border-blue-200'
          : 'text-text-secondary hover:text-text-main hover:bg-surface-2 border border-transparent'
      }`}
    >
      <div className="flex items-center space-x-2.5">
        <Icon className="w-4 h-4 shrink-0" />
        <span>{label}</span>
      </div>
      {rightElement}
    </button>
  );
}
