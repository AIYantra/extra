import {
  Play,
  Monitor,
  PauseCircle,
  FileDown,
  Layers,
  Terminal,
  Calculator,
  FileSpreadsheet,
  Palette,
  Box,
  FolderOpen,
  Cable,
} from "lucide-react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import { soundEngine } from "../utils/sound";
import { toast } from "sonner";
import { telemetryClient } from "../services/telemetryClient";

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunAction: (action: string) => void;
}

export function CommandPaletteModal({ isOpen, onClose, onRunAction }: CommandPaletteModalProps) {
  const handleSelect = (actionName: string, label: string) => {
    soundEngine.playTick();
    toast.success(`Action dispatched: ${label}`);
    onRunAction(actionName);
    onClose();
  };

  const handleRevealWorkspace = async () => {
    soundEngine.playTick();
    toast.info("Revealing ~/.extra/workspace in Windows Explorer");
    try {
      await telemetryClient.revealFile("~/.extra/workspace");
    } catch {
      // ignore
    }
    onClose();
  };

  return (
    <CommandDialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title="Extra Command Palette"
      description="Quickly navigate views, dispatch macro fast-paths, or trigger safety guardrails."
      showCloseButton={false}
      className="max-w-xl bg-white dark:bg-[#14161b] border border-[#dfe4eb] dark:border-[#262930] text-[#1a1a1c] dark:text-[#f4f5f8] shadow-2xl rounded-2xl overflow-hidden p-0"
    >
      <CommandInput
        placeholder="Search commands, tools, or macros..."
        className="text-xs sm:text-sm text-[#1a1a1c] dark:text-[#f4f5f8] placeholder:text-[#868c98] font-sans"
      />

      <CommandList className="max-h-[340px] p-2 font-sans bg-white dark:bg-[#14161b]">
        <CommandEmpty className="py-8 text-center text-xs text-[#868c98] font-mono">
          No commands match your query.
        </CommandEmpty>

        {/* Group 1: Pilot Cockpit & Views */}
        <CommandGroup heading="Pilot Cockpit & Views" className="text-[#868c98] text-[11px] font-medium px-1">
          <CommandItem
            onSelect={() => handleSelect("pilot", "Live Desktop Pilot Glass")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Play className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Live Desktop Pilot Glass</span>
                <span className="text-[11px] text-[#868c98] truncate block">Real-time optical streaming & actuator HUD</span>
              </div>
            </div>
            <CommandShortcut>2</CommandShortcut>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("dual-plane", "Dual-Plane Screen Monitor")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Layers className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Dual-Plane Monitor</span>
                <span className="text-[11px] text-[#868c98] truncate block">Plane 1 Optical SOUL vs Plane 2 Bridge</span>
              </div>
            </div>
            <CommandShortcut>5</CommandShortcut>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("optical", "Optical Radar View")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Monitor className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Optical Accessibility Radar</span>
                <span className="text-[11px] text-[#868c98] truncate block">Live AT-SPI2 and UIAutomation tree</span>
              </div>
            </div>
            <CommandShortcut>7</CommandShortcut>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("connectors", "Plugins & AI Connectors Setup")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Cable className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Plugins & AI Connectors Setup</span>
                <span className="text-[11px] text-[#868c98] truncate block">ChatGPT Actions, Claude.ai & Cursor setup guide</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-[#f8f9fb] dark:bg-[#1a1c20] text-[#1677ff]">
              Setup
            </span>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("terminal", "Terminal & Process Bridge")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Terminal className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Terminal & Python Bridge</span>
                <span className="text-[11px] text-[#868c98] truncate block">Deterministic code execution console</span>
              </div>
            </div>
            <CommandShortcut>6</CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator className="bg-[#dfe4eb] dark:bg-[#262930] my-1" />

        {/* Group 2: Universal Macro Fast Paths */}
        <CommandGroup heading="Macro Fast Paths" className="text-[#868c98] text-[11px] font-medium px-1">
          <CommandItem
            onSelect={() => handleSelect("macro-calc", "Calculate in Windows Calculator")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Calculator className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Calculate in Windows Calculator</span>
                <span className="text-[11px] text-[#868c98] truncate block">calc.exe · Single-turn instant micro-routine</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-[#f8f9fb] dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98]">
              1-Turn
            </span>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("macro-sheets", "Google Sheets Financial Reconciliation")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <FileSpreadsheet className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Reconcile Sheets & Export PDF</span>
                <span className="text-[11px] text-[#868c98] truncate block">Dual-Plane Shift+F11 tab insertion</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-[#f8f9fb] dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98]">
              Sheets
            </span>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("macro-canva", "Canva Social Banner Synthesis")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Palette className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Sync Canva Social Banners (4K PNG)</span>
                <span className="text-[11px] text-[#868c98] truncate block">Zero-stall keyboard accelerators (T, R, C)</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-[#f8f9fb] dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98]">
              Canva
            </span>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("macro-blender", "Blender Turntable Render")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Box className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Execute Blender Turntable Render</span>
                <span className="text-[11px] text-[#868c98] truncate block">Plane 2 bpy Python bridge dispatch</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-[#f8f9fb] dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98]">
              &lt; 15ms
            </span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator className="bg-[#dfe4eb] dark:bg-[#262930] my-1" />

        {/* Group 3: Governance & Safety */}
        <CommandGroup heading="Governance & Safety" className="text-[#868c98] text-[11px] font-medium px-1">
          <CommandItem
            onSelect={() => handleSelect("lineage", "Cryptographic Lineage Vault")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <FileDown className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Open Lineage Vault</span>
                <span className="text-[11px] text-[#868c98] truncate block">Inspect SHA-256 deliverable manifests</span>
              </div>
            </div>
            <CommandShortcut>4</CommandShortcut>
          </CommandItem>

          <CommandItem
            onSelect={handleRevealWorkspace}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 data-[selected=true]:bg-[#f4f5f8] dark:data-[selected=true]:bg-[#1e2025]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <FolderOpen className="size-4 text-[#868c98] group-hover:text-[#1a1a1c] group-data-[selected=true]:text-[#1a1a1c] dark:group-hover:text-[#f4f5f8] dark:group-data-[selected=true]:text-[#f4f5f8] shrink-0 transition-colors" />
              <div className="min-w-0">
                <span className="font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">Reveal Workspace in Windows Explorer</span>
                <span className="text-[11px] text-[#868c98] truncate block">~/.extra/workspace</span>
              </div>
            </div>
          </CommandItem>

          <CommandItem
            onSelect={() => handleSelect("panic", "Emergency Hardware Panic Stop")}
            className="group flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors duration-120 hover:bg-rose-50 dark:hover:bg-rose-950/20 data-[selected=true]:bg-rose-50 dark:data-[selected=true]:bg-rose-950/30 text-rose-600 dark:text-rose-400"
          >
            <div className="flex items-center gap-3 min-w-0">
              <PauseCircle className="size-4 text-rose-500 shrink-0" />
              <div className="min-w-0">
                <span className="font-medium text-rose-600 dark:text-rose-300 block">Trigger Emergency Panic Stop</span>
                <span className="text-[11px] text-rose-500/80 truncate block">Instantly freeze all AI hardware actuators</span>
              </div>
            </div>
            <kbd className="inline-flex items-center justify-center h-5 px-1.5 text-[10px] font-mono font-medium rounded border border-rose-200 dark:border-rose-900/40 bg-rose-50/50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 select-none">
              Ctrl+Alt+Esc
            </kbd>
          </CommandItem>
        </CommandGroup>
      </CommandList>

      {/* Footer Navigation Hints */}
      <div className="px-4 py-2.5 bg-[#f8f9fb] dark:bg-[#111216] border-t border-[#dfe4eb] dark:border-[#262930] flex items-center justify-between text-xs text-[#868c98] select-none">
        <div className="flex items-center gap-2">
          <span className="size-1.5 rounded-full bg-[#0e8345] shrink-0" />
          <span className="text-[#525866] dark:text-[#868c98] text-[11px]">
            Extra · Local Dispatch
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="inline-flex items-center gap-1 text-[#525866] dark:text-[#868c98]">
            <kbd className="inline-flex items-center justify-center min-w-4 h-4 px-1 text-[10px] font-mono font-medium rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-white dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98] shadow-2xs">
              ↑↓
            </kbd>
            <span>Navigate</span>
          </span>
          <span className="inline-flex items-center gap-1 text-[#525866] dark:text-[#868c98]">
            <kbd className="inline-flex items-center justify-center min-w-4 h-4 px-1 text-[10px] font-mono font-medium rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-white dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98] shadow-2xs">
              ↵
            </kbd>
            <span>Select</span>
          </span>
          <span className="inline-flex items-center gap-1 text-[#525866] dark:text-[#868c98]">
            <kbd className="inline-flex items-center justify-center min-w-4 h-4 px-1 text-[10px] font-mono font-medium rounded border border-[#dfe4eb] dark:border-[#2c3038] bg-white dark:bg-[#1a1c20] text-[#525866] dark:text-[#868c98] shadow-2xs">
              Esc
            </kbd>
            <span>Close</span>
          </span>
        </div>
      </div>
    </CommandDialog>
  );
}
