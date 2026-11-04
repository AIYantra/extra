import { create } from "zustand";
import {
  checkIsTauri,
  ipcPanicAbort,
  ipcResumePilot,
  ipcGetTelemetry,
  ipcSetSpeedMode,
  ipcListenPanicChange,
  DEFAULT_TELEMETRY,
  type EngineTelemetry,
  type SpeedMode,
} from "../services/ipc";
import {
  telemetryClient,
  type LiveTelemetryResponse,
  type LineageDeliverable,
  type DesktopWindow,
  type SkillCatalogItem,
} from "../services/telemetryClient";
import type { MissionRun } from "../data/dashboard";

interface EngineState {
  isTauri: boolean;
  isServerOnline: boolean;
  serverStatus: "online" | "standby";
  isPanicActive: boolean;
  activeMode: "chat" | "work";
  speedMode: SpeedMode;
  theme: "dark" | "light" | "system";
  telemetry: EngineTelemetry;
  tasksCompleted: number;
  actionsDispatched: number;
  activeTool: string;
  isInitialized: boolean;
  lastPanicTimestamp: number | null;
  lastSyncedAt: number | null;

  // Active execution state for contextual flight deck
  isExecuting: boolean;
  activeMission: string | null;
  executionStartTime: number | null;
  activeStep: string | null;

  // Real connected Extra data
  runs: MissionRun[];
  deliverables: LineageDeliverable[];
  windows: DesktopWindow[];
  skills: SkillCatalogItem[];
  inspectElements: any[];
  lastAction: any;

  // Actions
  init: () => Promise<() => void>;
  panicStop: () => Promise<void>;
  resumePilot: () => Promise<void>;
  setTheme: (theme: "dark" | "light" | "system") => void;
  setActiveMode: (mode: "chat" | "work") => void;
  setSpeedMode: (mode: SpeedMode) => Promise<void>;
  refreshTelemetry: () => Promise<void>;
  fetchRuns: () => Promise<void>;
  fetchLineage: () => Promise<void>;
  fetchWindows: () => Promise<void>;
  fetchSkills: () => Promise<void>;
  fetchInspect: () => Promise<void>;
  dispatchIntent: (intent: string) => Promise<any>;
  setIsExecuting: (executing: boolean, mission?: string | null) => void;
  setActiveStep: (step: string | null) => void;
}

export const useEngineStore = create<EngineState>((set, get) => ({
  isTauri: checkIsTauri(),
  isServerOnline: false,
  serverStatus: "standby",
  isPanicActive: false,
  activeMode: "chat",
  speedMode: "balanced",
  theme: "light",
  telemetry: DEFAULT_TELEMETRY,
  tasksCompleted: 0,
  actionsDispatched: 0,
  activeTool: "Standing by",
  isInitialized: false,
  lastPanicTimestamp: null,
  lastSyncedAt: null,

  isExecuting: false,
  activeMission: null,
  executionStartTime: null,
  activeStep: null,

  runs: [],
  deliverables: [],
  windows: [],
  skills: [],
  inspectElements: [],
  lastAction: null,

  init: async () => {
    // 0. Force light theme (only light theme is supported)
    if (typeof document !== "undefined") {
      document.documentElement.classList.remove("dark");
    }
    if (typeof window !== "undefined") {
      localStorage.setItem("extra_theme", "light");
    }
    set({ theme: "light" });

    const isT = checkIsTauri();
    set({ isTauri: isT });

    // 1. Fetch initial IPC telemetry
    const initialTelemetry = await ipcGetTelemetry();
    set({ telemetry: initialTelemetry, isInitialized: true });

    // 2. Initial fetch of real Extra data
    get().fetchRuns();
    get().fetchLineage();
    get().fetchWindows();
    get().fetchSkills();
    get().fetchInspect();

    // 3. Listen to native Tauri panic changes (System Tray / OS hotkey)
    const unlistenNative = await ipcListenPanicChange((isPanicked) => {
      set({
        isPanicActive: isPanicked,
        lastPanicTimestamp: isPanicked ? Date.now() : null,
      });
    });

    let syncCounter = 0;

    // 4. Start loopback HTTP polling to http://127.0.0.1:8000
    const unlistenPolling = telemetryClient.startPolling(
      (data: LiveTelemetryResponse | null, isOnline: boolean) => {
        if (isOnline && data) {
          syncCounter++;
          const isCompleted = ["completed", "verified", "failed"].includes(
            data.last_action?.status || ""
          );
          const isToolActive = Boolean(
            data.active_tool &&
            data.active_tool !== "Standing by" &&
            data.active_tool !== "idle" &&
            !isCompleted
          );

          set({
            isServerOnline: true,
            serverStatus: "online",
            activeTool: data.active_tool || "Standing by",
            isExecuting: isToolActive,
            activeMission: isToolActive ? (data.last_action?.intent || get().activeMission) : null,
            executionStartTime: isToolActive ? (get().executionStartTime || Date.now()) : null,
            activeStep: isToolActive ? `Dispatching ${data.active_tool}` : null,
            tasksCompleted: data.tasks_completed ?? get().tasksCompleted,
            actionsDispatched: data.actions_dispatched ?? get().actionsDispatched,
            speedMode: data.speed_mode || get().speedMode,
            isPanicActive: data.is_paused ?? get().isPanicActive,
            lastAction: data.last_action ?? get().lastAction,
            telemetry: {
              active_pilot: data.active_client || "Extra Engine",
              target_window: data.target_window || get().telemetry.target_window,
              target_pid: data.target_pid ?? get().telemetry.target_pid,
              target_proc: data.target_proc ?? get().telemetry.target_proc,
              latency_ms: data.latency_ms ?? get().telemetry.latency_ms,
              memory_mb: data.memory_mb ?? get().telemetry.memory_mb,
              tokens_saved: data.tokens_saved ?? get().telemetry.tokens_saved,
              cost_saved_usd: data.cost_saved_usd ?? get().telemetry.cost_saved_usd,
              tasks_completed: data.tasks_completed ?? get().telemetry.tasks_completed,
              actions_dispatched: data.actions_dispatched ?? get().telemetry.actions_dispatched,
              is_paused: data.is_paused ?? false,
            },
            lastSyncedAt: Date.now(),
          });

          // Refresh auxiliary datasets every 3 ticks (~6 seconds)
          if (syncCounter % 3 === 0) {
            get().fetchRuns();
            get().fetchWindows();
            get().fetchLineage();
          }
        } else {
          set({
            isServerOnline: false,
            serverStatus: "standby",
          });
        }
      },
      2000
    );

    return () => {
      unlistenNative();
      unlistenPolling();
    };
  },

  fetchRuns: async () => {
    const runs = await telemetryClient.fetchRuns();
    if (runs && runs.length > 0) {
      set({ runs });
    }
  },

  fetchLineage: async () => {
    const deliverables = await telemetryClient.fetchLineage();
    if (deliverables && deliverables.length > 0) {
      set({ deliverables });
    }
  },

  fetchWindows: async () => {
    const windows = await telemetryClient.fetchWindows();
    if (windows) {
      set({ windows });
    }
  },

  fetchSkills: async () => {
    const skills = await telemetryClient.fetchSkills();
    if (skills && skills.length > 0) {
      set({ skills });
    }
  },

  fetchInspect: async () => {
    const res = await telemetryClient.fetchInspect();
    if (res && res.elements) {
      set({ inspectElements: res.elements });
    }
  },

  setIsExecuting: (executing: boolean, mission: string | null = null) => {
    set({
      isExecuting: executing,
      activeMission: mission,
      executionStartTime: executing ? Date.now() : null,
      activeStep: executing ? (get().activeStep || "In flight...") : null,
    });
  },

  setActiveStep: (step: string | null) => {
    set({ activeStep: step });
  },

  dispatchIntent: async (intent: string) => {
    set({
      isExecuting: true,
      activeMission: intent,
      executionStartTime: Date.now(),
      activeStep: "Initializing subtask compiler...",
    });
    try {
      const result = await telemetryClient.dispatchIntent(intent);
      await get().fetchRuns();
      await get().fetchLineage();
      await get().refreshTelemetry();
      return result;
    } finally {
      set({
        isExecuting: false,
        activeMission: null,
        executionStartTime: null,
        activeStep: null,
      });
    }
  },

  panicStop: async () => {
    set({
      isPanicActive: true,
      isExecuting: false,
      activeMission: null,
      executionStartTime: null,
      activeStep: null,
      lastPanicTimestamp: Date.now(),
    });
    await Promise.allSettled([
      ipcPanicAbort(),
      telemetryClient.sendPanicStop(),
    ]);
  },

  resumePilot: async () => {
    set({ isPanicActive: false, lastPanicTimestamp: null });
    await Promise.allSettled([
      ipcResumePilot(),
      telemetryClient.sendResume(),
    ]);
  },

  setActiveMode: (mode: "chat" | "work") => {
    set({ activeMode: mode });
  },

  setTheme: (_theme: "dark" | "light" | "system") => {
    set({ theme: "light" });
    if (typeof window !== "undefined") {
      localStorage.setItem("extra_theme", "light");
    }
    if (typeof document !== "undefined") {
      document.documentElement.classList.remove("dark");
    }
  },

  setSpeedMode: async (mode: SpeedMode) => {
    set({ speedMode: mode });
    await Promise.allSettled([
      ipcSetSpeedMode(mode),
      telemetryClient.setSpeedMode(mode),
    ]);
  },

  refreshTelemetry: async () => {
    const isT = checkIsTauri();
    if (isT) {
      const data = await ipcGetTelemetry();
      set({ telemetry: data });
    } else {
      const data = await telemetryClient.fetchTelemetry();
      if (data) {
        set({
          telemetry: {
            active_pilot: data.active_client,
            target_window: data.target_window,
            target_pid: data.target_pid ?? 0,
            target_proc: data.target_proc ?? "Desktop",
            latency_ms: data.latency_ms,
            memory_mb: data.memory_mb,
            tokens_saved: data.tokens_saved,
            cost_saved_usd: data.cost_saved_usd,
            tasks_completed: data.tasks_completed,
            actions_dispatched: data.actions_dispatched ?? 0,
            is_paused: data.is_paused,
          },
          tasksCompleted: data.tasks_completed,
          actionsDispatched: data.actions_dispatched ?? 0,
          speedMode: data.speed_mode,
          isPanicActive: data.is_paused,
          lastAction: data.last_action,
        });
      }
    }
  },
}));
