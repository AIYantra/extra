import { useState, useEffect } from "react";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Wrench,
  FileCheck2,
  Layers,
  Brain,
  KeyRound,
  Activity,
  Settings,
  User,
  Info,
  PanelLeftClose,
  PanelLeftOpen,
  Cable,
} from "lucide-react";
import { ExtraLogoIcon } from "../ExtraLogo";
import { APP_VERSION_LABEL, PRODUCT_BYLINE } from "../../utils/appMeta";
import { useUpdateStore } from "../../store/useUpdateStore";
import { ExtraAvatar } from "../ExtraAvatar";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useAuthStore } from "../../store/useAuthStore";
import { extraDataService, type OperatorInfo } from "../../services/extraDataService";
import { soundEngine } from "../../utils/sound";

interface DashboardSidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

export function DashboardSidebar({
  currentTab,
  onSelectTab,
  collapsed,
  onToggleCollapsed,
}: DashboardSidebarProps) {
  const user = useAuthStore((state) => state.user);
  const openAuthModal = useAuthStore((state) => state.openAuthModal);

  const navItems: NavItem[] = [
    { id: "overview", label: "Dashboard", icon: LayoutDashboard },
    { id: "tools", label: "MCP Tools", icon: Wrench, badge: "40" },
    { id: "sessions", label: "Task Sessions", icon: FileCheck2 },
    { id: "apps", label: "Connected Apps", icon: Layers, badge: "5" },
    { id: "connectors", label: "Plugins & Connectors", icon: Cable, badge: "Setup" },
    { id: "skills", label: "Skills & Memory", icon: Brain },
    { id: "keys", label: "API Keys & Relay", icon: KeyRound },
    { id: "telemetry", label: "Reports & Doctor", icon: Activity },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "profile", label: "Profile", icon: User },
    { id: "about", label: "About", icon: Info },
  ];

  const handleNavClick = (id: string) => {
    soundEngine.playTick();
    onSelectTab(id);
  };

  const [operator, setOperator] = useState<OperatorInfo | null>(null);

  useEffect(() => {
    extraDataService.fetchOperator().then(setOperator).catch(() => {});
  }, []);

  const displayName = user?.username || operator?.display_name || "Operator (Local)";
  const avatarInitials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : (operator?.avatar_initials || "OP");
  const subtext = user?.email || operator?.email || "127.0.0.1 · CFA Safe";

  return (
    <aside
      className={`h-full max-h-screen shrink-0 flex flex-col justify-between bg-white border-r border-[#dfe4eb] transition-all duration-200 select-none z-30 overflow-hidden ${
        collapsed ? "w-18" : "w-64"
      }`}
    >
      {/* Top Header & Branding — Strict 56px height aligned to DashboardTopBar */}
      <div className="flex-1 flex flex-col min-h-0">
        <div
          className={`h-14 border-b border-[#dfe4eb] shrink-0 flex items-center ${
            collapsed ? "justify-center px-2" : "justify-between px-4"
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <ExtraLogoIcon className="size-7 shrink-0" />
            {!collapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <h1 className="font-semibold text-sm text-[#1a1a1c] tracking-tight leading-none">
                    Extra
                  </h1>
                  <span className="text-[10px] font-mono text-[#868c98] leading-none">
                    {useUpdateStore((s) => s.installedVersionLabel) || APP_VERSION_LABEL}
                  </span>
                </div>
                <p className="text-[10px] text-[#868c98] font-medium truncate mt-1 leading-none">
                  {PRODUCT_BYLINE}
                </p>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapsed}
            className="size-7 rounded-md text-[#868c98] hover:text-[#1a1a1c] hover:bg-[#f8f9fb] flex items-center justify-center transition-colors duration-150 cursor-pointer"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="size-3.5" /> : <PanelLeftClose className="size-3.5" />}
          </button>
        </div>

        {/* Navigation Link Items */}
        <nav className="p-3 space-y-1.5 mt-2 flex-1 overflow-y-auto min-h-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;

            const btn = (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-xs font-semibold transition-all duration-150 cursor-pointer ${
                  isActive
                    ? "bg-[#1a1a1c] text-white shadow-xs"
                    : "text-[#525866] hover:text-[#1a1a1c] hover:bg-[#f4f5f8]"
                } ${collapsed ? "justify-center px-0" : ""}`}
              >
                <Icon className={`size-4.5 shrink-0 ${isActive ? "text-white" : "text-[#525866]"}`} />

                {!collapsed && (
                  <>
                    <span className="flex-1 text-left truncate">{item.label}</span>
                    {item.badge && (
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                          isActive
                            ? "bg-white/20 text-white"
                            : "bg-[#f4f5f8] text-[#868c98]"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </button>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{btn}</TooltipTrigger>
                  <TooltipContent side="right">
                    <span>{item.label}</span>
                  </TooltipContent>
                </Tooltip>
              );
            }

            return btn;
          })}
        </nav>
      </div>

      {/* Bottom Profile Footer Card */}
      <div className="p-3 border-t border-[#dfe4eb] shrink-0">
        <button
          onClick={() => {
            soundEngine.playTick();
            if (user) {
              onSelectTab("profile");
            } else {
              openAuthModal();
            }
          }}
          title={user ? "View Profile" : "Account & Auth Settings"}
          className="w-full flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-[#f8f9fb] transition-colors duration-150 cursor-pointer text-left group"
        >
          <div className="relative shrink-0">
            {user && user.email ? (
              <ExtraAvatar seed={user.email} size={32} />
            ) : (
              <div className="size-8 rounded-full bg-[#1a1a1c] text-white flex items-center justify-center text-xs font-medium tracking-tight">
                {avatarInitials}
              </div>
            )}
            <span
              className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full bg-[#0e8345] ring-2 ring-white"
              title="Local Loopback Daemon Active"
            />
          </div>

          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-[#1a1a1c] truncate leading-tight">
                {displayName}
              </p>
              <p className="text-[11px] text-[#868c98] truncate leading-tight mt-0.5">
                {subtext}
              </p>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
}
