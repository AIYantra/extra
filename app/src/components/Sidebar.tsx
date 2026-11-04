import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Play, Layers, Globe, Monitor, Brain, Cpu, Terminal, Settings, ChevronDown, Check, PanelLeftClose, PanelLeftOpen, ShieldCheck } from "lucide-react";

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

interface NavDef { id: string; label: string; icon: LucideIcon; count?: string; badge?: string }

const GROUPS: { label: string; items: NavDef[] }[] = [
  {
    label: "Workspace",
    items: [
      { id: "cockpit", label: "Cockpit", icon: Play, badge: "Live" },
      { id: "automations", label: "Automations", icon: Layers, count: "14" },
      { id: "browsers", label: "Browser Sessions", icon: Globe, count: "2" },
    ],
  },
  {
    label: "Engine",
    items: [
      { id: "dualplane", label: "Dual-Plane Screen", icon: Monitor },
      { id: "memory", label: "SOUL Memory", icon: Brain, count: "38" },
      { id: "skills", label: "Harnesses & Skills", icon: Cpu, count: "18" },
      { id: "terminal", label: "Agent Shell", icon: Terminal },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  },
];

const WORKSPACES = ["Default Desktop Pilot", "Finance Ops — Sheets", "Studio — Blender / Canva"];

export function Sidebar({ currentTab, onSelectTab, collapsed, onToggleCollapsed }: SidebarProps) {
  const [workspace, setWorkspace] = useState(WORKSPACES[0]);
  const [wsOpen, setWsOpen] = useState(false);

  return (
    <aside
      aria-label="Primary"
      className={`shrink-0 border-r border-[#DFE4EB] bg-white flex flex-col justify-between select-none h-screen sticky top-0 overflow-y-auto transition-[width] duration-200 ${collapsed ? "w-[68px]" : "w-60"}`}
    >
      <div className="min-w-0">
        {/* Brand */}
        <div className="h-14 px-3 border-b border-slate-100 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-[#0F172A] flex items-center justify-center text-white font-bold text-[13px] shrink-0" aria-hidden="true">X</div>
            {!collapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-[#0F172A] text-[13px] tracking-tight truncate">Extra</span>
                  <span className="text-[10px] bg-slate-100 text-slate-600 px-1 py-px rounded font-mono">v2.4.1</span>
                </div>
                <p className="text-[10px] text-[#94A3B8] font-mono leading-tight truncate">Computer-Use Engine</p>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="tactile p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 shrink-0"
          >
            {collapsed ? <PanelLeftOpen size={16} strokeWidth={1.75} /> : <PanelLeftClose size={16} strokeWidth={1.75} />}
          </button>
        </div>

        {/* Workspace switcher */}
        <div className="px-3 pt-3 relative">
          <button
            type="button"
            onClick={() => setWsOpen((v) => !v)}
            aria-expanded={wsOpen}
            aria-label="Switch workspace"
            className="tactile w-full text-left px-2.5 py-2 rounded-lg border border-[#DFE4EB] bg-slate-50 hover:bg-slate-100 flex items-center justify-between gap-2 text-xs text-slate-700 font-medium"
          >
            <span className="flex items-center gap-2 truncate">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]" />
              </span>
              {!collapsed && <span className="truncate">{workspace}</span>}
            </span>
            {!collapsed && <ChevronDown size={16} strokeWidth={1.75} className="text-slate-400 shrink-0" />}
          </button>
          {wsOpen && !collapsed && (
            <div className="absolute left-3 right-3 top-full mt-1 z-30 card rounded-lg p-1" role="listbox" aria-label="Workspaces">
              {WORKSPACES.map((w) => (
                <button
                  key={w}
                  type="button"
                  role="option"
                  aria-selected={w === workspace}
                  onClick={() => { setWorkspace(w); setWsOpen(false); }}
                  className="tactile w-full flex items-center justify-between px-2 py-1.5 rounded-md text-xs text-slate-700 hover:bg-slate-50 text-left"
                >
                  <span className="truncate">{w}</span>
                  {w === workspace && <Check size={16} strokeWidth={1.75} className="text-[#0284C7] shrink-0" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Navigation — 8 destinations total (Miller's Law) */}
        <nav className="p-2.5 space-y-4 mt-1" aria-label="Sections">
          {GROUPS.map((group) => (
            <div key={group.label}>
              {!collapsed && <div className="px-2 pb-1 text-[10px] font-semibold tracking-widest uppercase text-[#94A3B8]">{group.label}</div>}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = currentTab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onSelectTab(item.id)}
                      aria-current={active ? "page" : undefined}
                      title={collapsed ? item.label : undefined}
                      className={`tactile w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-[13px] font-medium ${active ? "bg-sky-50 text-[#0284C7]" : "text-slate-600 hover:bg-slate-100 hover:text-[#0F172A]"} ${collapsed ? "justify-center px-0" : ""}`}
                    >
                      <span className="flex items-center gap-2.5 min-w-0">
                        <Icon size={16} strokeWidth={1.75} className={active ? "text-[#0284C7] shrink-0" : "text-slate-400 shrink-0"} />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </span>
                      {!collapsed && item.badge && (
                        <span className="text-[10px] px-1.5 py-px rounded bg-emerald-50 text-emerald-700 border border-emerald-200/70 font-mono font-semibold">{item.badge}</span>
                      )}
                      {!collapsed && item.count && <span className="text-[11px] text-[#94A3B8] font-mono tabular-nums">{item.count}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Pinned engine telemetry */}
      <div className="p-3 border-t border-slate-100">
        <div className="card rounded-lg p-2.5">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-[#0F172A]">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" aria-hidden="true" />
              {!collapsed && "SOUL Engine"}
            </span>
            <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200/70 px-1.5 py-px rounded font-mono font-semibold">Ready</span>
          </div>
          {!collapsed && (
            <>
              <svg className="w-full h-6 mt-2" viewBox="0 0 120 24" preserveAspectRatio="none" aria-hidden="true">
                <polyline points="0,16 15,10 30,14 45,6 60,11 75,5 90,9 105,4 120,7" fill="none" stroke="#10B981" strokeWidth="1.5" />
              </svg>
              <dl className="mt-1 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between"><dt className="text-slate-500">Latency</dt><dd className="font-semibold text-slate-700 tabular-nums">12ms</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Grounding</dt><dd className="font-semibold text-slate-700 tabular-nums">99.4%</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">PID</dt><dd className="font-semibold text-slate-700 tabular-nums">14088</dd></div>
              </dl>
            </>
          )}
        </div>
        {!collapsed && (
          <p className="mt-2 flex items-center justify-between text-[11px] text-slate-500 px-0.5">
            <span className="flex items-center gap-1"><ShieldCheck size={16} strokeWidth={1.75} className="text-slate-400" /> Human in loop</span>
            <span className="font-mono text-[10px] text-[#94A3B8]">:1420</span>
          </p>
        )}
      </div>
    </aside>
  );
}
