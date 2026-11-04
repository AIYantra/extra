import React from "react";
import { cn } from "../../utils/cn";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  elevated?: boolean;
}

export function Card({ className, elevated = false, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-station-border p-4 sm:p-5 flex flex-col space-y-4 transition-all duration-150",
        elevated
          ? "bg-station-elevated shadow-xs"
          : "bg-station-well shadow-xs",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
  className,
}: {
  title: string | React.ReactNode;
  subtitle?: string | React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3 border-b border-station-border pb-3", className)}>
      <div>
        <h3 className="text-sm font-medium text-station-text-primary tracking-tight">{title}</h3>
        {subtitle && <p className="text-xs text-station-text-muted mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex-1 space-y-3", className)}>{children}</div>;
}

export function CardFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("border-t border-station-border pt-3 flex items-center justify-between text-xs text-station-text-muted", className)}>
      {children}
    </div>
  );
}