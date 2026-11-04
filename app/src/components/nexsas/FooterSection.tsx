import React from "react";
import { ButtonPrimary } from "@/src/components/ui/button";
import { ShieldCheck, Terminal } from "lucide-react";

export const FooterSection: React.FC = () => {
  return (
    <footer id="docs" className="bg-secondary text-white pt-20 pb-12 border-t border-stroke-5">
      <div className="main-container mx-auto max-w-[1200px] px-4 sm:px-6">
        {/* Pre-footer Callout Island */}
        <div className="p-8 sm:p-12 rounded-[24px] bg-gradient-to-br from-background-7 to-background-5 border border-stroke-7 shadow-2xl text-center space-y-6 mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 text-primary-300 border border-primary-500/20 text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>100% Local Sovereign Execution</span>
          </div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-white max-w-2xl mx-auto">
            Give your AI hands and eyes today.
          </h2>

          <p className="text-sm sm:text-base text-white/70 max-w-xl mx-auto leading-relaxed">
            Install Extra via standard MCP. Works with Claude Desktop, Cursor, Windsurf, and custom autonomous agents on Windows, macOS, and Linux.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <ButtonPrimary
              onClick={() => {
                const elem = document.getElementById("cockpit");
                elem?.scrollIntoView({ behavior: "smooth" });
              }}
              className="bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/25"
              textClassName="px-6 py-3 font-semibold text-sm text-white"
            >
              Open Active Cockpit
            </ButtonPrimary>

            <div className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-white/80">
              <Terminal className="w-3.5 h-3.5 text-primary-400" />
              <span>pip install extra-mcp</span>
            </div>
          </div>
        </div>

        {/* Footer Navigation & Copyright */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pt-8 border-t border-stroke-7 text-xs text-white/50">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-white text-secondary flex items-center justify-center font-bold text-[10px]">
              X
            </div>
            <span className="font-semibold text-white/90">Extra Protocol</span>
            <span>· Built for YantraOS Sovereign Ecosystem</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="https://extra.yantraos.com" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              extra.yantraos.com
            </a>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              GitHub Source
            </a>
            <a href="#cockpit" className="hover:text-white transition-colors">
              Desktop Cockpit
            </a>
          </div>

          <div className="font-mono text-[11px]">
            MIT License · Zero Telemetry Leaks
          </div>
        </div>
      </div>
    </footer>
  );
};
