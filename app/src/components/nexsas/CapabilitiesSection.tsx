import React from "react";
import { BadgePrimary } from "@/src/components/ui/badge";
import {
  FolderCheck,
  FileSpreadsheet,
  Globe,
  Monitor,
  CheckCircle2
} from "lucide-react";

export const CapabilitiesSection: React.FC = () => {
  const capabilities = [
    {
      category: "Files & Folders",
      title: "Automate desktop file triage",
      description:
        "Sort downloads, tax receipts, screenshots, and raw archives into structured folders without manual drag-and-drop.",
      outcome: "Zero Controlled Folder Access blocks · 100% local audit log",
      badge: "extra_fs_batch",
      badgeColor: "bg-primary-50 text-primary-700 border-primary-200",
      icon: FolderCheck,
      iconBg: "bg-primary-50 text-primary-700",
    },
    {
      category: "Spreadsheets & Models",
      title: "Calculate & format spreadsheets",
      description:
        "Open Excel or Google Sheets, calculate totals, format tables, and export verified financial PDF deliverables.",
      outcome: "Shift+F11 tab insertion · Alt+/ menu accelerators",
      badge: "Dual-Plane Sheets",
      badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: FileSpreadsheet,
      iconBg: "bg-emerald-50 text-emerald-700",
    },
    {
      category: "Web & SaaS Automation",
      title: "Pilot browser workflows",
      description:
        "Navigate web apps, extract data, synthesize reports, and interact with complex SPAs with automatic crash bubble suppression.",
      outcome: "Playwright headless + live visible desktop pilot",
      badge: "extra_browser",
      badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
      icon: Globe,
      iconBg: "bg-blue-50 text-blue-700",
    },
    {
      category: "Creative Desktop Apps",
      title: "Design in Canva & MS Paint",
      description:
        "Create graphics in Canva or MS Paint with natural Bezier vector brush strokes. Strictly no clipboard image paste cheats.",
      outcome: "Continuous vector ink synthesis & 4K PNG export",
      badge: "extra_stroke",
      badgeColor: "bg-purple-50 text-purple-700 border-purple-200",
      icon: Monitor,
      iconBg: "bg-purple-50 text-purple-700",
    },
  ];

  return (
    <section id="capabilities" className="py-20 md:py-28 bg-white">
      <div className="main-container mx-auto max-w-[1200px] px-4 sm:px-6">
        <div className="text-center space-y-4 mb-16">
          <div className="flex justify-center">
            <BadgePrimary>
              <span>BUILT-IN DESKTOP PLAYBOOKS</span>
            </BadgePrimary>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-secondary tracking-tight">
            Engineered for sovereign desktop mastery
          </h2>
          <p className="text-secondary/70 max-w-2xl mx-auto text-base sm:text-lg">
            Hardened automation SOPs across Windows and macOS applications, preventing multi-turn exploratory loops.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {capabilities.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="p-6 sm:p-8 rounded-[20px] border border-stroke-1 bg-white hover:border-stroke-3 hover:shadow-lg transition-all duration-300 flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-11 h-11 rounded-xl ${item.iconBg} flex items-center justify-center transition-transform group-hover:scale-105`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] font-mono px-2.5 py-1 rounded-full border font-semibold ${item.badgeColor}`}>
                      {item.badge}
                    </span>
                  </div>

                  <span className="text-xs font-semibold uppercase tracking-wider text-secondary/50 font-mono">
                    {item.category}
                  </span>
                  <h3 className="text-lg sm:text-xl font-bold text-secondary mt-1 group-hover:text-primary-600 transition-colors">
                    {item.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-secondary/70 mt-2 leading-relaxed">
                    {item.description}
                  </p>
                </div>

                <div className="mt-6 pt-3.5 border-t border-stroke-2 flex items-center gap-2 text-xs font-medium text-secondary/80 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{item.outcome}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
