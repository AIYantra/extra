import { cn } from '@/src/utils/cn';
import { forwardRef, type HTMLAttributes } from 'react';

export type BadgePrimaryProps = HTMLAttributes<HTMLDivElement>;

export const BadgePrimary = forwardRef<HTMLDivElement, BadgePrimaryProps>(
  function BadgePrimary({ className, children, ...props }, ref) {
    return (
      <div
        ref={ref}
        className={cn(
          'border-stroke-3 text-tagline-3 text-secondary inline-block rounded-full border bg-white py-[3px] pr-4 pl-[3px] font-inter-tight font-normal',
          className,
        )}
        {...props}
      >
        <div className="flex items-center gap-x-2">
          <span
            className="bg-secondary flex h-6 w-8 shrink-0 items-center justify-center rounded-full"
            aria-hidden="true"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="none"
              className="fill-accent size-5"
              aria-hidden="true"
            >
              <path d="M6.66602 4.16675H8.33268V5.83341H6.66602V4.16675Z" />
              <path d="M9.16602 6.66675H10.8327V8.33342H9.16602V6.66675Z" />
              <path d="M11.666 9.16675H13.3327V10.8334H11.666V9.16675Z" />
              <path d="M9.16602 11.6667H10.8327V13.3334H9.16602V11.6667Z" />
              <path d="M6.66602 14.1667H8.33268V15.8334H6.66602V14.1667Z" />
            </svg>
          </span>
          <span>{children}</span>
        </div>
      </div>
    );
  },
);

BadgePrimary.displayName = 'BadgePrimary';
