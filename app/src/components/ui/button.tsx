import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-md font-sans text-xs font-medium whitespace-nowrap transition-all duration-120 outline-none select-none cursor-pointer disabled:pointer-events-none disabled:opacity-40 active:scale-[0.98] focus-visible:border-ring focus-visible:ring-[2px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs border border-indigo-400/30 font-semibold",
        primary:
          "bg-station-text-primary text-station-canvas hover:opacity-90 shadow-xs font-semibold",
        secondary:
          "bg-station-surface text-station-text-primary hover:bg-station-surface-hover border border-station-border shadow-xs",
        destructive:
          "bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 active:bg-rose-500/30",
        accent:
          "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs border border-indigo-400/30 font-semibold",
        outline:
          "border border-station-border bg-transparent text-station-text-primary hover:bg-station-surface",
        ghost:
          "bg-transparent text-station-text-muted hover:text-station-text-primary hover:bg-station-surface border border-transparent",
        icon:
          "h-8 w-8 min-h-[32px] min-w-[32px] p-0 text-station-text-muted hover:text-station-text-primary hover:bg-station-surface rounded-md border border-transparent",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-8.5 min-h-[34px] px-3.5 text-xs md:text-[13px] has-[>svg]:px-3",
        xs: "h-6 min-h-[24px] gap-1 px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 min-h-[28px] gap-1.5 px-2.5 text-xs has-[>svg]:px-2",
        md: "h-8.5 min-h-[34px] px-3.5 text-xs md:text-[13px] has-[>svg]:px-3",
        lg: "h-10 min-h-[40px] px-4 text-xs md:text-sm font-semibold has-[>svg]:px-3.5",
        icon: "size-8.5 min-h-[34px] min-w-[34px] p-0",
        "icon-xs": "size-6 min-h-[24px] min-w-[24px] p-0 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7 min-h-[28px] min-w-[28px] p-0",
        "icon-lg": "size-10 min-h-[40px] min-w-[40px] p-0",
      },
    },
    defaultVariants: {
      variant: "secondary",
      size: "default",
    },
  }
)

interface ButtonProps
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

function Button({
  className,
  variant = "secondary",
  size = "default",
  asChild = false,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

/** Backwards-compatibility aliases for legacy views */
function ButtonPrimary({
  children,
  className,
  textClassName,
  ...props
}: React.ComponentProps<typeof Button> & { textClassName?: string }) {
  return (
    <Button variant="primary" className={cn(className, textClassName)} {...props}>
      {children}
    </Button>
  )
}

function ButtonSecondary({
  children,
  className,
  textClassName,
  ...props
}: React.ComponentProps<typeof Button> & { textClassName?: string }) {
  return (
    <Button variant="secondary" className={cn(className, textClassName)} {...props}>
      {children}
    </Button>
  )
}

export { Button, buttonVariants, ButtonPrimary, ButtonSecondary }
export type { ButtonProps }
