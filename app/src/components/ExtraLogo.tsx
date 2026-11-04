import extraLogoImg from "../assets/ExtraLOGO-Square.png";
import { APP_VERSION_LABEL, PRODUCT_BYLINE } from "../utils/appMeta";

interface ExtraLogoProps {
  className?: string;
  showWordmark?: boolean;
  size?: "sm" | "md" | "lg";
  alt?: string;
}

/**
 * Official Extra Dotted-X brand logo.
 * Directly sourced from: "D:\yantra_workspace\extra.yantraos.com\extra Logo\extra Logo\ExtraLOGO Square.png"
 */
export function ExtraLogoIcon({
  className = "size-8.5",
  alt = "Extra Logo",
}: {
  className?: string;
  alt?: string;
  color?: string;
}) {
  return (
    <img
      src={extraLogoImg}
      alt={alt}
      className={`object-contain select-none shrink-0 ${className}`}
      draggable={false}
    />
  );
}

/**
 * Official Extra brand logo with wordmark.
 */
export function ExtraLogo({
  className = "",
  showWordmark = true,
  size = "md",
}: ExtraLogoProps) {
  const iconSizes = {
    sm: "size-6",
    md: "size-8.5",
    lg: "size-10",
  };

  const textSizes = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg",
  };

  const iconElement = (
    <img
      src={extraLogoImg}
      alt="Extra Logo"
      className={`${iconSizes[size]} object-contain select-none shrink-0`}
      draggable={false}
    />
  );

  if (!showWordmark) {
    return <div className={`inline-flex items-center justify-center ${className}`}>{iconElement}</div>;
  }

  return (
    <div className={`flex items-center gap-2.5 min-w-0 ${className}`}>
      {iconElement}
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-1.5 leading-none">
          <span className={`font-bold ${textSizes[size]} text-[#1a1a1c] tracking-tight`}>
            Extra
          </span>
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-[#1677ff]/10 text-[#1677ff] leading-none uppercase tracking-wider">
            {APP_VERSION_LABEL}
          </span>
        </div>
        <span className="text-[10px] text-[#868c98] font-medium tracking-normal mt-0.5 truncate">
          {PRODUCT_BYLINE}
        </span>
      </div>
    </div>
  );
}

export default ExtraLogo;
