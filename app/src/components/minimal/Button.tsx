import React from "react";
import { cn } from "../../utils/cn";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "icon" | "destructive" | "accent";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-sans font-medium transition-all duration-120 cursor-pointer select-none disabled:opacity-40 disabled:pointer-events-none active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/40";

  const sizeStyles = {
    sm: "h-7 min-h-[28px] px-2.5 text-xs rounded-md gap-1.5",
    md: "h-8.5 min-h-[34px] px-3.5 text-xs md:text-[13px] rounded-md gap-2",
    lg: "h-10 min-h-[40px] px-4 text-xs md:text-sm rounded-md gap-2 font-semibold",
  };

  const variantStyles = {
    primary:
      "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs border border-transparent font-semibold",
    secondary:
      "bg-station-surface text-station-text-primary hover:bg-station-surface/80 border border-station-border shadow-xs",
    ghost:
      "bg-transparent text-station-text-muted hover:text-station-text-primary hover:bg-station-surface/50 border border-transparent",
    icon:
      "h-8 w-8 min-h-[32px] min-w-[32px] p-0 text-station-text-muted hover:text-station-text-primary hover:bg-station-surface/50 rounded-md border border-transparent",
    destructive:
      "bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 active:bg-rose-500/30",
    accent:
      "bg-indigo-600 text-white hover:bg-indigo-500 shadow-xs border border-indigo-500/30 font-semibold",
  };

  return (
    <button
      className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}