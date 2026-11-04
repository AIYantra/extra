import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Toggle as TogglePrimitive } from "radix-ui"

const toggleVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-xs font-medium whitespace-nowrap transition-all duration-120 outline-none hover:bg-white/[0.04] hover:text-[#f4f4f6] focus-visible:ring-1 focus-visible:ring-white/20 disabled:pointer-events-none disabled:opacity-50 data-[state=on]:bg-[#181b20] data-[state=on]:text-[#f4f4f6] data-[state=on]:border-white/[0.08] [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        default: "bg-transparent text-[#8a8f98]",
        outline:
          "border border-white/[0.08] bg-transparent text-[#8a8f98] shadow-xs hover:bg-white/[0.06] hover:text-[#f4f4f6]",
      },
      size: {
        default: "h-8 px-2.5",
        sm: "h-7 px-2 text-[11px]",
        lg: "h-9 px-3",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Toggle({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<typeof TogglePrimitive.Root> &
  VariantProps<typeof toggleVariants>) {
  return (
    <TogglePrimitive.Root
      data-slot="toggle"
      className={cn(toggleVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Toggle, toggleVariants }
