import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: number | string;
  subtext: string;
  icon: LucideIcon;
  iconColorClass?: string;
  subtextColorClass?: string;
}

export function StatCard({ 
  label, 
  value, 
  subtext, 
  icon: Icon, 
  iconColorClass = 'text-accent',
  subtextColorClass = 'text-text-secondary'
}: StatCardProps) {
  return (
    <div className="bg-surface-0 border border-border-subtle rounded-xl p-5 shadow-sm">
      <div className="flex justify-between items-start">
        <span className="text-xs font-medium text-text-muted">{label}</span>
        <div className="w-8 h-8 rounded-lg bg-accent-light flex items-center justify-center">
          <Icon className={`w-4 h-4 ${iconColorClass}`} />
        </div>
      </div>
      <div className="text-2xl font-bold text-text-main mt-2 tracking-tight">{value}</div>
      <div className={`text-xs mt-1 ${subtextColorClass}`}>{subtext}</div>
    </div>
  );
}
