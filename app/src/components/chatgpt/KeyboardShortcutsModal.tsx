import { X, Keyboard, ShieldAlert } from "lucide-react";
import { soundEngine } from "../../utils/sound";

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ShortcutDef {
  keys: string[];
  description: string;
  category: "Navigation" | "Computer-Use & Safety" | "Actions";
}

const SHORTCUTS: ShortcutDef[] = [
  // Safety & Computer-Use
  { keys: ["Ctrl", "Alt", "Esc"], description: "Emergency Hardware Panic Kill Switch", category: "Computer-Use & Safety" },
  { keys: ["Ctrl", "K"], description: "Open Command Palette / Quick Run", category: "Computer-Use & Safety" },
  { keys: ["Ctrl", "1"], description: "Switch to Chat Assistant Mode", category: "Navigation" },
  { keys: ["Ctrl", "2"], description: "Switch to Workstation Pilot Mode", category: "Navigation" },
  { keys: ["Ctrl", "Shift", "O"], description: "Start New Chat / Mission", category: "Actions" },
  { keys: ["Ctrl", "Shift", "S"], description: "Toggle Left Navigation Drawer", category: "Navigation" },
  { keys: ["Alt", "←"], description: "Navigate Back in History", category: "Navigation" },
  { keys: ["Alt", "→"], description: "Navigate Forward in History", category: "Navigation" },
  { keys: ["F11"], description: "Expand / Collapse Full Canvas", category: "Navigation" },
  { keys: ["Ctrl", "/"], description: "Show Keyboard Shortcuts Guide", category: "Actions" },
  { keys: ["1", "-", "9"], description: "Direct Numeric Tab Navigation", category: "Navigation" },
];

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  if (!isOpen) return null;

  const handleClose = () => {
    soundEngine.playTick();
    onClose();
  };

  const categories: ShortcutDef["category"][] = [
    "Computer-Use & Safety",
    "Navigation",
    "Actions",
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150 font-sans select-none"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg bg-[#212121] border border-white/[0.1] rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#1A1A1A]">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Keyboard className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#ECECEC] tracking-tight">
                Keyboard Shortcuts
              </h3>
              <p className="text-[11px] text-[#8E8E8E]">
                Extra v2.4 (ChatGPT Desktop Edition)
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-7 h-7 rounded-lg text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {categories.map((cat) => (
            <div key={cat} className="space-y-2">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#8E8E8E] px-1 font-semibold">
                {cat}
              </div>
              <div className="bg-[#171717] rounded-xl border border-white/[0.06] divide-y divide-white/[0.04] overflow-hidden">
                {SHORTCUTS.filter((s) => s.category === cat).map((shortcut, idx) => (
                  <div
                    key={idx}
                    className="px-3.5 py-2.5 flex items-center justify-between text-xs"
                  >
                    <span className="text-[#ECECEC] font-medium flex items-center gap-2">
                      {shortcut.category === "Computer-Use & Safety" && shortcut.keys.includes("Esc") && (
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      )}
                      <span>{shortcut.description}</span>
                    </span>
                    <div className="flex items-center gap-1 shrink-0 font-mono text-[10px]">
                      {shortcut.keys.map((k, kIdx) => (
                        <kbd
                          key={kIdx}
                          className="px-1.5 py-0.5 rounded bg-[#2F2F2F] text-[#ECECEC] border border-white/[0.1] shadow-[inset_0_-1px_0_rgba(0,0,0,0.5)]"
                        >
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/[0.06] bg-[#1A1A1A] text-[11px] text-[#8E8E8E] flex items-center justify-between">
          <span>Press <kbd className="font-mono text-[#ECECEC] bg-white/[0.06] px-1 rounded">Esc</kbd> to close</span>
          <span className="font-mono text-purple-400">Zero-Stall Win32 Fast Paths</span>
        </div>
      </div>
    </div>
  );
}
