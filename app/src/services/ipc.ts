import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

export interface EngineTelemetry {
  active_pilot: string;
  target_window: string;
  target_pid: number;
  target_proc: string;
  latency_ms: number;
  memory_mb: number;
  tokens_saved: number;
  cost_saved_usd: number;
  tasks_completed: number;
  actions_dispatched: number;
  is_paused: boolean;
}

export type SpeedMode = "turbo" | "balanced" | "smart";

export const DEFAULT_TELEMETRY: EngineTelemetry = {
  active_pilot: "Extra Engine",
  target_window: "Desktop Workspace",
  target_pid: 0,
  target_proc: "System",
  latency_ms: 0,
  memory_mb: 0,
  tokens_saved: 0,
  cost_saved_usd: 0,
  tasks_completed: 0,
  actions_dispatched: 0,
  is_paused: false,
};

export function checkIsTauri(): boolean {
  try {
    return isTauri();
  } catch {
    return false;
  }
}

export async function ipcPanicAbort(): Promise<boolean> {
  if (checkIsTauri()) {
    try {
      return await invoke<boolean>("panic_abort");
    } catch (err) {
      console.error("[IPC] Failed to invoke panic_abort:", err);
    }
  } else {
    console.warn("[IPC Browser Fallback] panic_abort invoked in web mode");
  }
  return true;
}

export async function ipcResumePilot(): Promise<boolean> {
  if (checkIsTauri()) {
    try {
      return await invoke<boolean>("resume_pilot");
    } catch (err) {
      console.error("[IPC] Failed to invoke resume_pilot:", err);
    }
  } else {
    console.warn("[IPC Browser Fallback] resume_pilot invoked in web mode");
  }
  return false;
}

export async function ipcGetTelemetry(): Promise<EngineTelemetry> {
  if (checkIsTauri()) {
    try {
      return await invoke<EngineTelemetry>("get_engine_telemetry");
    } catch (err) {
      console.error("[IPC] Failed to invoke get_engine_telemetry:", err);
    }
  }
  return DEFAULT_TELEMETRY;
}

export async function ipcSetSpeedMode(mode: SpeedMode): Promise<string> {
  if (checkIsTauri()) {
    try {
      return await invoke<string>("set_speed_mode", { mode });
    } catch (err) {
      console.error("[IPC] Failed to invoke set_speed_mode:", err);
    }
  } else {
    console.log("[IPC Browser Fallback] set_speed_mode:", mode);
  }
  return mode;
}

export async function ipcListenPanicChange(
  callback: (isPanicked: boolean) => void
): Promise<UnlistenFn> {
  if (checkIsTauri()) {
    try {
      return await listen<boolean>("extra://panic-state-change", (event) => {
        console.log("[IPC Event] extra://panic-state-change received:", event.payload);
        callback(event.payload);
      });
    } catch (err) {
      console.error("[IPC] Failed to register extra://panic-state-change listener:", err);
    }
  }
  return () => {};
}
