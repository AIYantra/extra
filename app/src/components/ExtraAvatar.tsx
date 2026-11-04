import { Blobatar } from "@blobatar/react";
import { useGaze } from "@blobatar/react/gaze";
import "blobatar/motion.css";
import "blobatar/gaze.css";

interface ExtraAvatarProps {
  seed: string;
  size?: number;
  className?: string;
  showBorder?: boolean;
}

/**
 * Deterministic animated avatar, same engine as extra.yantraos.com.
 * Generated from the account seed (email) — no images stored anywhere.
 */
export function ExtraAvatar({
  seed,
  size = 32,
  className = "",
  showBorder = true,
}: ExtraAvatarProps) {
  const { ref } = useGaze({ travel: 4, lookAt: "pointer" });

  return (
    <div
      className={`relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full ${
        showBorder ? "border border-[#dfe4eb] shadow-2xs" : ""
      } bg-[#f0f2f6] ${className}`}
      style={{ width: size, height: size }}
      title={`Avatar for ${seed}`}
    >
      <Blobatar
        ref={ref as any}
        name={seed || "anonymous"}
        size={size}
        animate="always"
        className="size-full"
      />
    </div>
  );
}
