export type RunStatus = "running" | "completed" | "failed" | "queued";
export type RiskLevel = "Low" | "Medium" | "High";
export type StepStatus = "done" | "doing" | "queued";

export interface NavItem {
  id: string;
  label: string;
  iconName: string;
  count?: string;
  badge?: string;
}

export interface ExecutionStep {
  id: string;
  tool: string;
  target: string;
  status: StepStatus;
  durationMs?: number;
  grounding?: string;
  coords?: string;
}

export interface Approval {
  id: string;
  title: string;
  risk: RiskLevel;
  detail: string;
  app: string;
  requestedAgo: string;
}

export interface MemoryFact {
  id: string;
  fact: string;
  source: string;
  verifiedAt: string;
}

export interface MissionRun {
  id: string;
  title: string;
  app: string;
  status: RunStatus;
  started: string;
  durationSec: number;
  steps: string;
  lineage: string;
  result: string;
  errorReason?: string;
  tokensSaved?: number;
  costSavedUsd?: number;
  speedup?: number;
}

export interface HarnessApp {
  id: string;
  name: string;
  plane: string;
  latency: string;
  status: "Active" | "Ready" | "Verified";
}

export const RECENT_PRESETS: { label: string; app: string; intent?: string; runs?: string }[] = [
  { label: "Quick Math: 245.12 / 383.29 in Calculator", app: "Calc", intent: "calculate 245.12/383.29=", runs: "Verified" },
  { label: "Check System Windows & Active Desktop", app: "System", intent: "inspect active desktop windows", runs: "Verified" },
  { label: "Organize Files in Downloads", app: "System", intent: "organize loose files in downloads", runs: "Verified" },
];

export const EXECUTION_STEPS: ExecutionStep[] = [];

export const INITIAL_APPROVALS: Approval[] = [];

export const INITIAL_MEMORIES: MemoryFact[] = [];

export const MISSION_RUNS: MissionRun[] = [];

export const HARNESS_APPS: HarnessApp[] = [
  { id: "calc", name: "Calculator", plane: "1-Turn Macro", latency: "11ms", status: "Active" },
  { id: "notepad", name: "Notepad", plane: "Direct File I/O", latency: "8ms", status: "Active" },
  { id: "paint", name: "MS Paint", plane: "Natural Splines", latency: "14ms", status: "Ready" },
  { id: "explorer", name: "File Explorer", plane: "CFA Batch", latency: "12ms", status: "Active" },
  { id: "browser", name: "Chromium / Edge", plane: "DOM + Optical", latency: "18ms", status: "Ready" },
];

export function formatDuration(totalSec: number): string {
  if (totalSec <= 0) return "—";
  const m = Math.floor(totalSec / 60);
  const s = Math.round(totalSec % 60);
  if (m === 0) return `${s}s`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
