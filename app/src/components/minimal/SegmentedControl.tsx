import React from "react";
import { cn } from "../../utils/cn";

export interface SegmentOption<T extends string = string> {
  id: T;
  label: string | React.ReactNode;
  badge?: string;
}

export interface SegmentedControlProps<T extends string = string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function SegmentedControl<T extends string = string>({
  options,
  value,
  onChange,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-0.5 bg-station-well p-0.5 rounded-lg border border-station-border select-none",
        className
      )}
      role="tablist"
    >
      {options.map((opt) => {
        const isActive = opt.id === value;
        return (
          <button
            key={opt.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(opt.id)}
            className={cn(
              "h-7 min-h-[28px] px-3 py-1 rounded-md text-xs font-medium transition-all duration-120 cursor-pointer flex items-center gap-1.5 focus-visible:outline-none",
              isActive
                ? "bg-station-surface text-station-text-primary font-medium border border-station-border shadow-xs"
                : "text-station-text-muted hover:text-station-text-primary hover:bg-station-surface/50 border border-transparent"
            )}
          >
            <span>{opt.label}</span>
            {opt.badge && (
              <span
                className={cn(
                  "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                  isActive ? "bg-station-surface text-station-text-primary" : "text-station-text-dim"
                )}
              >
                {opt.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
