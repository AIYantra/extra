import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  FileCheck2,
  ExternalLink,
  FolderOpen,
  Sparkles,
  Zap,
  Monitor,
} from "lucide-react";
import { soundEngine } from "../../utils/sound";

export interface ThoughtBlock {
  durationSec: number;
  steps: string[];
}

export interface ExecutionReceipt {
  tool: string;
  intent: string;
  targetApp: string;
  targetPid?: number;
  settleMs: number;
  grounding: string;
  verified: boolean;
}

export interface DeliverableCard {
  filename: string;
  path: string;
  size: string;
  hash: string;
  type: "document" | "image" | "spreadsheet" | "data";
}

export interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  targetApp?: string;
  thought?: ThoughtBlock;
  receipt?: ExecutionReceipt;
  deliverable?: DeliverableCard;
}

interface ChatMessageThreadProps {
  messages: MessageItem[];
  isLoading?: boolean;
  onOpenWorkMode?: () => void;
}

export function ChatMessageThread({
  messages,
  isLoading = false,
  onOpenWorkMode,
}: ChatMessageThreadProps) {
  const [openThoughts, setOpenThoughts] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleThought = (msgId: string) => {
    setOpenThoughts((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    soundEngine.playTick();
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleOpenFile = (path: string) => {
    soundEngine.playTick();
    console.log("[Deliverable] Opening file:", path);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 pb-24 font-sans text-xs sm:text-sm">
      {messages.map((msg) => {
        const isUser = msg.role === "user";
        const isThoughtOpen = openThoughts[msg.id] ?? false;

        if (isUser) {
          return (
            <div key={msg.id} className="flex justify-end gap-3 select-text">
              <div className="max-w-xl bg-[#2F2F2F] text-[#ECECEC] px-4 py-3 rounded-2xl shadow-sm border border-white/[0.06] space-y-1.5">
                {msg.targetApp && (
                  <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-purple-900/40 border border-purple-500/30 text-[10px] text-purple-200 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                    Target: {msg.targetApp}
                  </div>
                )}
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.content}
                </div>
                <div className="text-[10px] text-[#8E8E8E] text-right">
                  {msg.timestamp}
                </div>
              </div>
              <div className="w-8 h-8 rounded-full bg-purple-600 text-white font-bold flex items-center justify-center text-xs shrink-0 shadow-sm mt-0.5">
                C
              </div>
            </div>
          );
        }

        return (
          <div key={msg.id} className="flex items-start gap-3 select-text animate-in fade-in duration-200">
            {/* Assistant Avatar */}
            <div className="w-8 h-8 rounded-xl bg-[#252525] border border-white/[0.08] text-sm flex items-center justify-center shrink-0 shadow-sm mt-0.5">
              <span>🐺</span>
            </div>

            {/* Message Body Container */}
            <div className="flex-1 space-y-3 min-w-0">
              {/* 1. Reasoning Trace Accordion ("Thought for X seconds") */}
              {msg.thought && (
                <div className="border border-white/[0.08] rounded-xl bg-[#1A1A1A] overflow-hidden text-xs">
                  <button
                    onClick={() => toggleThought(msg.id)}
                    className="w-full px-3 py-2 flex items-center justify-between text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.03] transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2 font-mono text-[11px]">
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                      <span>Thought for {msg.thought.durationSec}s</span>
                    </span>
                    {isThoughtOpen ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {isThoughtOpen && (
                    <div className="px-3.5 py-2.5 pt-1 space-y-1.5 border-t border-white/[0.06] bg-[#171717] font-mono text-[11px] text-[#B4B4B4]">
                      {msg.thought.steps.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-2">
                          <span className="text-purple-400 shrink-0 font-bold">›</span>
                          <span className="leading-relaxed">{step}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 2. Inline Hardware Execution Receipt */}
              {msg.receipt && (
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="p-1 rounded bg-purple-900/50 text-purple-300 border border-purple-500/30">
                        <Zap className="w-3.5 h-3.5" />
                      </span>
                      <span className="font-mono font-medium text-[#ECECEC] text-xs truncate">
                        Dispatched: {msg.receipt.tool}
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      Verified • {msg.receipt.settleMs}ms
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] font-mono text-[#8E8E8E] bg-[#171717] p-2 rounded-lg border border-white/[0.04]">
                    <div>
                      <span className="block text-[9px] uppercase tracking-wider text-[#555a64]">Target Process</span>
                      <span className="text-[#ECECEC]">{msg.receipt.targetApp} {msg.receipt.targetPid ? `(PID ${msg.receipt.targetPid})` : ""}</span>
                    </div>
                    <div>
                      <span className="block text-[9px] uppercase tracking-wider text-[#555a64]">Grounding</span>
                      <span className="text-indigo-300">{msg.receipt.grounding}</span>
                    </div>
                    <div className="col-span-2 sm:col-span-1">
                      <span className="block text-[9px] uppercase tracking-wider text-[#555a64]">Settle Detection</span>
                      <span className="text-emerald-400">SOUL Gateman</span>
                    </div>
                  </div>
                </div>
              )}

              {/* 3. Primary Message Content */}
              <div className="text-sm leading-relaxed text-[#ECECEC] whitespace-pre-wrap">
                {msg.content}
              </div>

              {/* 4. Physical Deliverable Receipt Card */}
              {msg.deliverable && (
                <div className="p-3.5 rounded-xl bg-[#2A2A2A] border border-white/[0.08] shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-emerald-900/30 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                      <FileCheck2 className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-xs text-[#ECECEC] truncate">
                        {msg.deliverable.filename}
                      </div>
                      <div className="text-[10px] font-mono text-[#8E8E8E] truncate">
                        {msg.deliverable.path}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[9px] font-mono text-[#8E8E8E]">
                        <span>{msg.deliverable.size}</span>
                        <span>•</span>
                        <span>SHA: {msg.deliverable.hash}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleOpenFile(msg.deliverable!.path)}
                      className="px-2.5 py-1 rounded-md bg-white/[0.08] hover:bg-white/[0.14] text-xs font-medium text-[#ECECEC] transition-colors cursor-pointer flex items-center gap-1.5 shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Open</span>
                    </button>
                    <button
                      onClick={() => handleOpenFile(msg.deliverable!.path)}
                      className="px-2.5 py-1 rounded-md bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-[#B4B4B4] transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Reveal in Explorer</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Message Bottom Action Bar */}
              <div className="flex items-center gap-2 pt-1 text-xs text-[#8E8E8E]">
                <button
                  onClick={() => handleCopy(msg.id, msg.content)}
                  className="flex items-center gap-1 hover:text-[#ECECEC] transition-colors cursor-pointer p-1 rounded hover:bg-white/[0.04]"
                  title="Copy message"
                >
                  {copiedId === msg.id ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-[10px] text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="text-[10px]">Copy</span>
                    </>
                  )}
                </button>

                {onOpenWorkMode && (
                  <button
                    onClick={onOpenWorkMode}
                    className="flex items-center gap-1 hover:text-purple-300 transition-colors cursor-pointer p-1 rounded hover:bg-white/[0.04]"
                    title="View live execution in Work Cockpit"
                  >
                    <Monitor className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-[10px]">View in Work Cockpit</span>
                  </button>
                )}

                <span className="text-[10px] ml-auto text-[#555a64]">{msg.timestamp}</span>
              </div>
            </div>
          </div>
        );
      })}

      {/* Loading Thinking Indicator */}
      {isLoading && (
        <div className="flex items-center gap-3 animate-pulse">
          <div className="w-8 h-8 rounded-xl bg-[#252525] border border-white/[0.08] text-sm flex items-center justify-center shrink-0">
            <span>🐺</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-[#B4B4B4]">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
            <span>Extra is thinking and dispatching hardware actions...</span>
          </div>
        </div>
      )}
    </div>
  );
}
