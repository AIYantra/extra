import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1.5 overflow-hidden rounded-md border text-xs font-medium whitespace-nowrap transition-[color,box-shadow] select-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground border-transparent shadow-xs [a&]:hover:bg-primary/90",
        secondary:
          "bg-station-surface text-station-text-primary border-station-border [a&]:hover:bg-station-surface-hover",
        destructive:
          "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20 [a&]:hover:bg-rose-500/20",
        danger:
          "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20 [a&]:hover:bg-rose-500/20",
        outline:
          "border-station-border text-station-text-muted bg-transparent [a&]:hover:bg-station-surface [a&]:hover:text-station-text-primary",
        ghost: "border-transparent [a&]:hover:bg-station-surface [a&]:hover:text-station-text-primary",
        link: "border-transparent text-primary underline-offset-4 [a&]:hover:underline",
        mono: "font-mono border-station-border bg-station-surface/60 text-station-text-primary text-[10px] px-1.5 py-0.5 tracking-tight tabular-nums",
        neutral: "bg-station-surface text-station-text-muted border-station-border",
        success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
        warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
        accent: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20",
      },
      size: {
        default: "px-2 py-0.5 text-[11px] leading-tight",
        sm: "px-1.5 py-0.2 text-[10px]",
        lg: "px-2.5 py-1 text-xs",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

interface BadgeProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof badgeVariants> {
  asChild?: boolean
  dot?: boolean
  pulse?: boolean
}

function Badge({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  dot = false,
  pulse = false,
  children,
  ...props
}: BadgeProps) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      data-size={size}
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            "size-1.5 rounded-full shrink-0",
            variant === "success" && "bg-emerald-400",
            variant === "warning" && "bg-amber-400",
            (variant === "destructive" || variant === "danger") && "bg-rose-400",
            (variant === "accent" || variant === "default") && "bg-indigo-400",
            (variant === "neutral" ||
              variant === "secondary" ||
              variant === "outline" ||
              variant === "mono") &&
              "bg-[#8a8f98]",
            pulse && "animate-pulse"
          )}
          aria-hidden="true"
        />
      )}
      {children}
    </Comp>
  )
}

/** Backwards-compatibility alias for legacy views */
function BadgePrimary({
  children,
  className,
  ...props
}: React.ComponentProps<typeof Badge>) {
  return (
    <Badge variant="default" className={className} {...props}>
      {children}
    </Badge>
  )
}

export { Badge, badgeVariants, BadgePrimary }
export type { BadgeProps }
