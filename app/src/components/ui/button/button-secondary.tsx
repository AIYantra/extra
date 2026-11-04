'use client';

import { useButtonHoverAnimation } from '@/src/hooks/use-button-hover-animation';
import { cn } from '@/src/utils/cn';
import { forwardRef, useRef, type ButtonHTMLAttributes } from 'react';
import { ButtonIcon, buttonHoverTransitionStyle } from './button-icon';

export type ButtonSecondaryProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  textClassName?: string;
};

export const ButtonSecondary = forwardRef<HTMLButtonElement, ButtonSecondaryProps>(
  function ButtonSecondary({ className, textClassName, children, type = 'button', ...props }, ref) {
    const buttonRef = useRef<HTMLButtonElement>(null);
    const iconRef = useRef<HTMLDivElement>(null);
    const textRef = useRef<HTMLSpanElement>(null);
    const { onMouseEnter, onMouseLeave } = useButtonHoverAnimation(buttonRef, iconRef, textRef);

    return (
      <button
        ref={(node) => {
          buttonRef.current = node;
          if (typeof ref === 'function') ref(node);
          else if (ref) ref.current = node;
        }}
        type={type}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        className={cn(
          'button group button-inner font-ibm-plex-mono text-tagline-1 text-secondary flex h-12 w-full cursor-pointer items-center rounded-full bg-white p-1 font-normal first-letter:uppercase',
          className
        )}
        {...props}
      >
        <ButtonIcon ref={iconRef} wrapperClassName="bg-black" iconClassName="fill-white" />
        <span
          ref={textRef}
          style={buttonHoverTransitionStyle}
          className={cn('shrink-0 px-4', textClassName)}
        >
          {children}
        </span>
      </button>
    );
  }
);

ButtonSecondary.displayName = 'ButtonSecondary';
