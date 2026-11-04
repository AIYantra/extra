import { cn } from '@/src/utils/cn';
import { forwardRef } from 'react';

export const buttonHoverTransitionStyle = {
  transition: 'transform 0.7s cubic-bezier(0.4, 0, 0.2, 1)',
} as const;

type ButtonIconProps = Readonly<{
  wrapperClassName?: string;
  iconClassName?: string;
}>;

export const ButtonIcon = forwardRef<HTMLDivElement, ButtonIconProps>(function ButtonIcon(
  { wrapperClassName, iconClassName },
  ref
) {
  return (
    <div
      ref={ref}
      style={buttonHoverTransitionStyle}
      className={cn(
        'relative z-20 flex h-10 w-14 items-center justify-center overflow-hidden rounded-full',
        wrapperClassName
      )}
      aria-hidden="true"
    >
      <span className="flex size-6 shrink-0 items-center justify-center" aria-hidden="true">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          className={cn('size-6', iconClassName)}
          aria-hidden="true"
        >
          <path d="M8 5H10V7H8V5Z" />
          <path d="M11 8H13V10H11V8Z" />
          <path d="M14 11H16V13H14V11Z" />
          <path d="M11 14H13V16H11V14Z" />
          <path d="M8 17H10V19H8V17Z" />
        </svg>
      </span>
    </div>
  );
});

ButtonIcon.displayName = 'ButtonIcon';
