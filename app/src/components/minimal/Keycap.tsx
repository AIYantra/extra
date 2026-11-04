import React from "react";
import { cn } from "../../utils/cn";

export interface KeycapProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  size?: "sm" | "md";
}

export function Keycap({ children, size = "md", className, ...props }: KeycapProps) {
  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center font-mono font-medium select-none text-station-text-muted bg-station-surface border border-station-border rounded-[4px] shadow-xs transition-colors",
        size === "sm" ? "h-4.5 min-w-[18px] px-1 text-[9px]" : "h-5 min-w-[20px] px-1.5 text-[10px]",
        className
      )}
      {...props}
    >
      {children}
    </kbd>
  );
}