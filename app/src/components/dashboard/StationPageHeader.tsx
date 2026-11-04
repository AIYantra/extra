import type { LucideIcon } from "lucide-react";

interface StationPageHeaderProps {
  icon: LucideIcon;
  iconColor?: string;
  title: string;
  badge?: string;
  badgeVariant?: "mono" | "default" | "secondary" | "outline" | "success" | "warning";
  description: string;
  actions?: React.ReactNode;
}

export function StationPageHeader({
  icon: Icon,
  iconColor = "text-indigo-600 dark:text-indigo-400",
  title,
  badge,
  description,
  actions,
}: StationPageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08] select-none">
      <div className="min-w-0">
        <div className="flex items-center gap-2.5">
          <span className="p-1.5 rounded-lg bg-black/[0.04] dark:bg-white/[0.06] text-slate-700 dark:text-zinc-300">
            <Icon className={`size-4 ${iconColor}`} />
          </span>
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
            {title}
          </h2>
          {badge && (
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-black/[0.04] dark:bg-white/[0.06] text-slate-600 dark:text-zinc-400 border border-black/[0.04] dark:border-white/[0.06] tabular-nums">
              {badge}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 leading-relaxed">
          {description}
        </p>
      </div>

      {actions && (
        <div className="flex items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}

