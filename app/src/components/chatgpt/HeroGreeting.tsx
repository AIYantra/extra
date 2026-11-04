import { Sparkles } from "lucide-react";

interface HeroGreetingProps {
  title?: string;
  subtitle?: string;
}

export function HeroGreeting({
  title = "What’s on your mind today?",
  subtitle = "Directly pilot Windows desktop apps, dispatch automated workflows, and synthesize deliverables in real-time.",
}: HeroGreetingProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center space-y-3 mb-8 select-none font-sans">
      {/* Top Subtle Pill */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-purple-300 text-xs font-medium shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-purple-400" />
        <span>Extra Sovereign Computer-Use Engine v2.4</span>
      </div>

      {/* Main Centered Greeting */}
      <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[#ECECEC] max-w-xl">
        {title}
      </h1>

      {/* Whisper Subtitle */}
      {subtitle && (
        <p className="text-sm text-[#8E8E8E] max-w-md mx-auto leading-relaxed">
          {subtitle}
        </p>
      )}
    </div>
  );
}
