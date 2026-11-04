import { useState, useEffect } from "react";
import { Minus, Square, X } from "lucide-react";
import { checkIsTauri } from "../../services/ipc";

export function DesktopWindowControls() {
  const [isTauriApp, setIsTauriApp] = useState(false);

  useEffect(() => {
    setIsTauriApp(checkIsTauri());
  }, []);

  const handleMinimize = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().minimize();
      } catch (err) {
        console.warn("[Window] Minimize failed:", err);
      }
    }
  };

  const handleToggleMaximize = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().toggleMaximize();
      } catch (err) {
        console.warn("[Window] Toggle maximize failed:", err);
      }
    }
  };

  const handleClose = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().close();
      } catch (err) {
        console.warn("[Window] Close failed:", err);
      }
    }
  };

  // Only render desktop window controls if inside a custom frameless Tauri desktop container
  if (!isTauriApp) {
    return null;
  }

  return (
    <div className="flex items-center gap-0.5 ml-2 -mr-1">
      <button
        onClick={handleMinimize}
        aria-label="Minimize Window"
        title="Minimize"
        className="w-7 h-7 rounded-md flex items-center justify-center text-station-text-muted hover:text-station-text-primary hover:bg-station-surface transition-colors cursor-pointer"
      >
        <Minus className="w-3.5 h-3.5" />
      </button>

      <button
        onClick={handleToggleMaximize}
        aria-label="Maximize Window"
        title="Maximize"
        className="w-7 h-7 rounded-md flex items-center justify-center text-station-text-muted hover:text-station-text-primary hover:bg-station-surface transition-colors cursor-pointer"
      >
        <Square className="w-3 h-3" />
      </button>

      <button
        onClick={handleClose}
        aria-label="Close Window"
        title="Close"
        className="w-7 h-7 rounded-md flex items-center justify-center text-station-text-muted hover:text-white hover:bg-rose-600 transition-colors cursor-pointer"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}