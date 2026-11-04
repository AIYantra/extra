import React, { useState, useEffect } from "react";
import { ButtonPrimary } from "@/src/components/ui/button";

export const Navbar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex justify-center px-4 transition-all duration-300">
      <div
        className={`w-full max-w-[1200px] transition-all duration-300 ${
          isScrolled ? "mt-2" : "mt-4"
        }`}
      >
        <div className="flex items-center justify-between rounded-full bg-white/95 backdrop-blur-md px-5 py-2.5 shadow-md border border-stroke-1">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-full bg-secondary text-white flex items-center justify-center font-bold text-xs tracking-tight shadow-sm">
              X
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-secondary text-base tracking-tight">Extra</span>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-primary-50 text-primary-700 border border-primary-200">
                v2.4
              </span>
            </div>
          </a>

          {/* Nav links */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-secondary/70">
            <a
              href="#cockpit"
              className="px-3.5 py-1.5 rounded-full hover:text-secondary hover:bg-background-3 transition-colors"
            >
              Cockpit
            </a>
            <a
              href="#architecture"
              className="px-3.5 py-1.5 rounded-full hover:text-secondary hover:bg-background-3 transition-colors"
            >
              Architecture
            </a>
            <a
              href="#capabilities"
              className="px-3.5 py-1.5 rounded-full hover:text-secondary hover:bg-background-3 transition-colors"
            >
              Capabilities
            </a>
            <a
              href="#benchmarks"
              className="px-3.5 py-1.5 rounded-full hover:text-secondary hover:bg-background-3 transition-colors"
            >
              Benchmarks
            </a>
            <a
              href="#docs"
              className="px-3.5 py-1.5 rounded-full hover:text-secondary hover:bg-background-3 transition-colors"
            >
              Protocol Docs
            </a>
          </nav>

          {/* Action Button */}
          <div className="flex items-center gap-3">
            <ButtonPrimary
              onClick={() => {
                const elem = document.getElementById("cockpit");
                elem?.scrollIntoView({ behavior: "smooth" });
              }}
              className="h-10 text-xs px-1"
              textClassName="px-3 font-semibold text-xs text-white"
            >
              Launch Pilot
            </ButtonPrimary>
          </div>
        </div>
      </div>
    </header>
  );
};
