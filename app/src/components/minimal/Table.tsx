import React from "react";
import { cn } from "../../utils/cn";

export function Table({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <table className="w-full text-left text-xs md:text-[13px] border-collapse">{children}</table>
    </div>
  );
}

export function TableHeader({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <thead>
      <tr
        className={cn(
          "border-b border-station-border text-[11px] font-mono uppercase tracking-wider text-station-text-muted select-none bg-station-elevated/70",
          className
        )}
      >
        {children}
      </tr>
    </thead>
  );
}

export function TableBody({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <tbody className={cn("divide-y divide-station-border/40 font-sans", className)}>{children}</tbody>;
}

export function TableRow({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "transition-colors hover:bg-station-surface/50",
        onClick && "cursor-pointer",
        className
      )}
    >
      {children}
    </tr>
  );
}

export function TableHeadCell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <th className={cn("py-2.5 px-3.5 font-medium text-station-text-muted", className)}>{children}</th>;
}

export function TableCell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={cn("py-3 px-3.5 text-station-text-primary align-middle whitespace-nowrap", className)}>{children}</td>;
}