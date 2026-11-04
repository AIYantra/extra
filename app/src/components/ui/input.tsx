import * as React from "react"
import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-8.5 w-full min-w-0 rounded-md border border-white/[0.08] bg-[#121417] px-3 py-1.5 text-xs text-[#f4f4f6] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-all outline-none selection:bg-primary selection:text-primary-foreground placeholder:text-[#555a64] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-indigo-500 focus-visible:ring-1 focus-visible:ring-indigo-500/50",
        "aria-invalid:border-rose-500 aria-invalid:ring-rose-500/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
