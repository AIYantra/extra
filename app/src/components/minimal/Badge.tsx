import React from "react";
import { cn } from "../../utils/cn";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "success" | "warning" | "mono" | "outline" | "danger" | "accent";
  dot?: boolean;
  pulse?: boolean;
  children: React.ReactNode;
}

export function Badge({
  variant = "neutral",
  dot = false,
  pulse = false,
  className,
  children,
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center font-sans text-[11px] font-medium leading-none px-2 py-0.5 rounded-md select-none transition-colors";

  const variantStyles = {
    neutral: "bg-station-surface text-station-text-muted border border-station-border",
    success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
    danger: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20",
    accent: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20",
    mono: "bg-station-surface text-station-text-primary font-mono text-[10px] px-1.5 py-0.5 rounded border border-station-border tracking-tight",
    outline: "bg-transparent text-station-text-muted border border-station-border font-medium",
  };

  return (
    <span className={cn(baseStyles, variantStyles[variant], className)} {...props}>
      {dot && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full mr-1.5 shrink-0",
            variant === "success" && "bg-emerald-500",
            variant === "warning" && "bg-amber-500",
            variant === "danger" && "bg-rose-500",
            variant === "accent" && "bg-indigo-500",
            (variant === "neutral" || variant === "outline" || variant === "mono") && "bg-station-text-muted",
            pulse && "animate-pulse"
          )}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}