import * as React from "react"
import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-16 w-full rounded-md border border-white/[0.08] bg-[#121417] px-3 py-2 text-xs text-[#f4f4f6] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-all outline-none placeholder:text-[#555a64] focus-visible:border-indigo-500 focus-visible:ring-1 focus-visible:ring-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-rose-500",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
