import { useState, useRef, useEffect } from "react";
import {
  Plus,
  ArrowUp,
  Mic,
  MicOff,
  Calculator,
  Paintbrush,
  FileText,
  Globe,
  Table,
  Camera,
  ChevronDown,
  X,
  Zap,
  Gauge,
  Shield,
  Check,
} from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";
import { SPEED_MODE_META } from "../../utils/speedModes";

interface ChatInputCapsuleProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (prompt: string, targetApp?: string) => void;
  placeholder?: string;
  isLoading?: boolean;
}

interface TargetAppOption {
  id: string;
  name: string;
  process: string;
  icon: any;
  hint: string;
}

const TARGET_APPS: TargetAppOption[] = [
  { id: "calc", name: "Calculator", process: "calc.exe", icon: Calculator, hint: "Math & formulas" },
  { id: "paint", name: "Paint", process: "mspaint.exe", icon: Paintbrush, hint: "Sketches & diagrams" },
  { id: "notepad", name: "Notepad", process: "notepad.exe", icon: FileText, hint: "Notes & drafts" },
  { id: "browser", name: "Web Browser", process: "msedge.exe", icon: Globe, hint: "Web research" },
  { id: "sheets", name: "Google Sheets", process: "sheets.google.com", icon: Table, hint: "Spreadsheets" },
  { id: "screen", name: "Screen Snipper", process: "snippingtool.exe", icon: Camera, hint: "Visual grounding" },
];

export function ChatInputCapsule({
  value,
  onChange,
  onSubmit,
  placeholder = "Ask Extra...",
  isLoading = false,
}: ChatInputCapsuleProps) {
  const [isAppMenuOpen, setIsAppMenuOpen] = useState(false);
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState<TargetAppOption | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  const speedMode = useEngineStore((state) => state.speedMode);
  const setSpeedMode = useEngineStore((state) => state.setSpeedMode);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menus on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsAppMenuOpen(false);
        setIsModeMenuOpen(false);
      }
    };
    if (isAppMenuOpen || isModeMenuOpen) {
      window.addEventListener("mousedown", handleClickOutside);
    }
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, [isAppMenuOpen, isModeMenuOpen]);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if ((!value.trim() && !selectedApp) || isLoading) return;
    const finalPrompt = selectedApp
      ? `[Target: ${selectedApp.name} (${selectedApp.process})] ${value.trim()}`
      : value.trim();

    soundEngine.playTick();
    onSubmit(finalPrompt, selectedApp?.process);
    setSelectedApp(null);
  };

  const toggleRecording = () => {
    soundEngine.playTick();
    if (!isRecording) {
      setIsRecording(true);
      // Simulate speech recognition or activate if Web Speech API is present
      if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        try {
          const rec = new SpeechRec();
          rec.continuous = false;
          rec.interimResults = false;
          rec.onresult = (evt: any) => {
            const transcript = evt.results[0][0].transcript;
            onChange(value ? `${value} ${transcript}` : transcript);
            setIsRecording(false);
          };
          rec.onerror = () => setIsRecording(false);
          rec.onend = () => setIsRecording(false);
          rec.start();
        } catch {
          setTimeout(() => setIsRecording(false), 2000);
        }
      } else {
        setTimeout(() => {
          setIsRecording(false);
          onChange(value ? `${value} (voice input)` : "Automate workflow on desktop");
        }, 1500);
      }
    } else {
      setIsRecording(false);
    }
  };

  const hasContent = value.trim().length > 0 || selectedApp !== null;

  return (
    <div
      ref={menuRef}
      className="w-full max-w-2xl mx-auto relative font-sans"
    >
      {/* Floating Capsule Main Body */}
      <div className="bg-[#2F2F2F] rounded-3xl p-2.5 px-3.5 shadow-2xl border border-white/[0.08] focus-within:border-white/[0.2] transition-all flex flex-col gap-2">
        {/* Selected Target Application Pill (if active) */}
        {selectedApp && (
          <div className="flex items-center gap-1.5 self-start px-2 py-0.5 rounded-full bg-purple-900/40 border border-purple-500/30 text-purple-200 text-[11px] animate-in fade-in duration-150">
            <selectedApp.icon className="w-3 h-3 text-purple-300" />
            <span>Target: {selectedApp.name}</span>
            <button
              onClick={() => setSelectedApp(null)}
              className="hover:text-white p-0.5 rounded-full hover:bg-white/[0.1] cursor-pointer"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        <div className="flex items-end gap-2.5">
          {/* Left: '+' Attachment / Target Application Picker Button */}
          <div className="relative">
            <button
              onClick={() => {
                setIsAppMenuOpen(!isAppMenuOpen);
                setIsModeMenuOpen(false);
              }}
              title="Attach target application or file"
              aria-label="Add application"
              className="w-8 h-8 rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-[#ECECEC] flex items-center justify-center transition-all cursor-pointer shrink-0"
            >
              <Plus className={`w-4 h-4 transition-transform duration-150 ${isAppMenuOpen ? "rotate-45" : ""}`} />
            </button>

            {/* Target Application Selection Dropdown */}
            {isAppMenuOpen && (
              <div className="absolute left-0 bottom-full mb-2 w-64 bg-[#252525] border border-white/[0.1] rounded-2xl shadow-2xl p-1.5 z-50 text-xs">
                <div className="px-2.5 py-1 text-[10px] text-[#8E8E8E] uppercase tracking-wider font-mono">
                  Select Target Application
                </div>
                <div className="space-y-0.5 mt-1">
                  {TARGET_APPS.map((app) => {
                    const Icon = app.icon;
                    return (
                      <button
                        key={app.id}
                        onClick={() => {
                          setSelectedApp(app);
                          setIsAppMenuOpen(false);
                        }}
                        className="w-full px-2.5 py-2 rounded-xl flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] transition-colors text-left cursor-pointer group"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-lg bg-white/[0.04] text-[#ECECEC] group-hover:bg-purple-500/20 group-hover:text-purple-300 transition-colors">
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium text-xs truncate">{app.name}</div>
                            <div className="text-[10px] text-[#8E8E8E] truncate">{app.hint}</div>
                          </div>
                        </div>
                        <span className="text-[9px] font-mono text-[#8E8E8E] bg-white/[0.04] px-1 py-0.2 rounded">
                          {app.process}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Center: Auto-expanding Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-[#ECECEC] placeholder-[#8E8E8E] text-sm resize-none focus:outline-none min-h-[32px] max-h-[160px] py-1.5 leading-relaxed"
          />

          {/* Right Controls Container */}
          <div className="flex items-center gap-1.5 shrink-0 pb-0.5">
            {/* Speed Mode Pill (Turbo / Balanced / Smart IT) */}
            <div className="relative">
              <button
                onClick={() => {
                  setIsModeMenuOpen(!isModeMenuOpen);
                  setIsAppMenuOpen(false);
                }}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/[0.06] hover:bg-white/[0.1] text-xs text-[#B4B4B4] hover:text-[#ECECEC] transition-colors cursor-pointer"
                title="Execution Speed Mode"
              >
                <span className="text-[11px] font-medium">{SPEED_MODE_META[speedMode].label}</span>
                <ChevronDown className="w-3 h-3 text-[#8E8E8E]" />
              </button>

              {/* Mode Menu Dropdown */}
              {isModeMenuOpen && (
                <div className="absolute right-0 bottom-full mb-2 w-48 bg-[#252525] border border-white/[0.1] rounded-xl shadow-2xl p-1 z-50 text-xs">
                  <div className="px-2 py-1 text-[10px] text-[#8E8E8E] uppercase tracking-wider font-mono">
                    Speed Mode
                  </div>
                  <button
                    onClick={() => {
                      setSpeedMode("turbo");
                      setIsModeMenuOpen(false);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Zap className="w-3.5 h-3.5 text-purple-400" />
                      <span>{SPEED_MODE_META.turbo.label}</span>
                    </div>
                    {speedMode === "turbo" && <Check className="w-3.5 h-3.5 text-purple-400" />}
                  </button>
                  <button
                    onClick={() => {
                      setSpeedMode("balanced");
                      setIsModeMenuOpen(false);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Gauge className="w-3.5 h-3.5 text-blue-400" />
                      <span>{SPEED_MODE_META.balanced.label}</span>
                    </div>
                    {speedMode === "balanced" && <Check className="w-3.5 h-3.5 text-blue-400" />}
                  </button>
                  <button
                    onClick={() => {
                      setSpeedMode("smart");
                      setIsModeMenuOpen(false);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Shield className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{SPEED_MODE_META.smart.label}</span>
                    </div>
                    {speedMode === "smart" && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                  </button>
                </div>
              )}
            </div>

            {/* Voice Dictation Button */}
            <button
              onClick={toggleRecording}
              title={isRecording ? "Stop dictation" : "Voice dictation"}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors cursor-pointer ${
                isRecording
                  ? "bg-rose-500/20 text-rose-300 animate-pulse"
                  : "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06]"
              }`}
            >
              {isRecording ? <MicOff className="w-4 h-4 text-rose-400" /> : <Mic className="w-4 h-4" />}
            </button>

            {/* Signature Circular Send Button (Purple #7042F8 with white Up Arrow) */}
            <button
              onClick={handleSubmit}
              disabled={!hasContent || isLoading}
              title="Send Prompt (Enter)"
              aria-label="Send"
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                hasContent && !isLoading
                  ? "bg-[#7042F8] hover:bg-[#5E34E0] text-white shadow-md hover:scale-105 cursor-pointer"
                  : "bg-white/[0.06] text-[#8E8E8E] cursor-not-allowed opacity-40"
              }`}
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
