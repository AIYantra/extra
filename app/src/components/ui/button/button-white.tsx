'use client';

import { useButtonHoverAnimation } from '@/src/hooks/use-button-hover-animation';
import { cn } from '@/src/utils/cn';
import { forwardRef, useRef, type ButtonHTMLAttributes } from 'react';
import { ButtonIcon, buttonHoverTransitionStyle } from './button-icon';

export type ButtonWhiteProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  textClassName?: string;
};

export const ButtonWhite = forwardRef<HTMLButtonElement, ButtonWhiteProps>(function ButtonWhite(
  { className, textClassName, children, type = 'button', ...props },
  ref
) {
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
        'border-stroke-1 button group button-inner font-ibm-plex-mono text-tagline-1 text-secondary flex h-12 cursor-pointer items-center rounded-full border bg-white p-1 font-normal first-letter:uppercase',
        className
      )}
      {...props}
    >
      <ButtonIcon ref={iconRef} wrapperClassName="bg-(image:--color-gradient-14)" iconClassName="fill-black" />
      <span
        ref={textRef}
        style={buttonHoverTransitionStyle}
        className={cn('shrink-0 stroke-0 px-4', textClassName)}
      >
        {children}
      </span>
    </button>
  );
});

ButtonWhite.displayName = 'ButtonWhite';
