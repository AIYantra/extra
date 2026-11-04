'use client';

import { useEffect, useRef, type RefObject } from 'react';
export function useButtonHoverAnimation(
  buttonRef: RefObject<HTMLElement | null>,
  iconRef: RefObject<HTMLElement | null>,
  textRef: RefObject<HTMLElement | null>
) {
  const distances = useRef({ icon: 0, text: 0 });

  useEffect(() => {
    const button = buttonRef.current;
    const icon = iconRef.current;
    const text = textRef.current;
    if (!button || !icon || !text) return;

    const wrapperRect = button.getBoundingClientRect();
    const iconRect = icon.getBoundingClientRect();
    const textRect = text.getBoundingClientRect();

    const leftPadding = Number.parseFloat(getComputedStyle(button).paddingLeft) || 0;
    const rightPadding = Number.parseFloat(getComputedStyle(button).paddingRight) || 0;

    const iconLeftRelative = iconRect.left - wrapperRect.left;
    distances.current.icon = wrapperRect.width - rightPadding - icon.offsetWidth - iconLeftRelative;

    const textLeftRelative = textRect.left - wrapperRect.left;
    distances.current.text = Math.max(0, textLeftRelative - leftPadding);
  }, [buttonRef, iconRef, textRef]);

  const onMouseEnter = () => {
    const icon = iconRef.current;
    const text = textRef.current;
    if (!icon || !text) return;

    icon.style.transform = `translateX(${distances.current.icon}px)`;
    text.style.transform = `translateX(-${distances.current.text}px)`;
  };

  const onMouseLeave = () => {
    const icon = iconRef.current;
    const text = textRef.current;
    if (!icon || !text) return;

    icon.style.transform = 'translateX(0)';
    text.style.transform = 'translateX(0)';
  };

  return { onMouseEnter, onMouseLeave };
}
