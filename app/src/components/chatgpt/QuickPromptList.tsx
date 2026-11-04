import { Image, PenTool, Globe, Calculator, ArrowRight } from "lucide-react";
import { soundEngine } from "../../utils/sound";

interface QuickPromptOption {
  id: string;
  title: string;
  description: string;
  prompt: string;
  targetApp: string;
  icon: any;
  colorClass: string;
}

interface QuickPromptListProps {
  onSelectPrompt: (prompt: string, targetApp?: string) => void;
}

const DEFAULT_PROMPTS: QuickPromptOption[] = [
  {
    id: "image",
    title: "Create an image or sketch",
    description: "Draw system architecture in MS Paint or Canva",
    prompt: "Open Paint and draw system architecture diagram with vector boxes and connectors",
    targetApp: "mspaint.exe",
    icon: Image,
    colorClass: "text-emerald-400 bg-emerald-500/10",
  },
  {
    id: "write",
    title: "Write or edit",
    description: "Draft executive briefing or notes in Notepad",
    prompt: "Draft an executive briefing note in Notepad comparing autonomous agent paradigms",
    targetApp: "notepad.exe",
    icon: PenTool,
    colorClass: "text-purple-400 bg-purple-500/10",
  },
  {
    id: "search",
    title: "Search the web",
    description: "Automate research and summarize live web pages",
    prompt: "Search the web for latest AI news and summarize top benchmarks",
    targetApp: "msedge.exe",
    icon: Globe,
    colorClass: "text-amber-400 bg-amber-500/10",
  },
  {
    id: "calc",
    title: "Calculate in Windows Calculator",
    description: "Compute formulas and verify output in calc.exe",
    prompt: "Calculate 245.12/383.29 in Windows Calculator and display verified result",
    targetApp: "calc.exe",
    icon: Calculator,
    colorClass: "text-indigo-400 bg-indigo-500/10",
  },
];

export function QuickPromptList({ onSelectPrompt }: QuickPromptListProps) {
  const handleClick = (item: QuickPromptOption) => {
    soundEngine.playTick();
    onSelectPrompt(item.prompt, item.targetApp);
  };

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col space-y-2 select-none font-sans mt-4">
      <div className="text-[11px] font-mono text-[#8E8E8E] uppercase tracking-wider px-1 text-left">
        Suggested Automations
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {DEFAULT_PROMPTS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => handleClick(item)}
              className="p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.12] transition-all text-left flex items-start gap-3 cursor-pointer group shadow-sm hover:shadow-md"
            >
              <div
                className={`p-2 rounded-xl shrink-0 transition-transform group-hover:scale-105 ${item.colorClass}`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-medium text-[#ECECEC] group-hover:text-white transition-colors truncate">
                    {item.title}
                  </div>
                  <ArrowRight className="w-3 h-3 text-[#8E8E8E] opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                </div>
                <div className="text-[11px] text-[#8E8E8E] line-clamp-1 mt-0.5">
                  {item.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
