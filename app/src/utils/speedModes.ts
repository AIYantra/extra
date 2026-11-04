import type { SpeedMode } from "../services/ipc";

export interface SpeedModeMeta {
  /** Display name shown in menus, pills, and settings. */
  label: string;
  /** One-line plain-language description for compact menus. */
  shortDesc: string;
  /** Plain-language description for the settings list. */
  desc: string;
  /** Small pace chip shown in settings. */
  pace: string;
  recommended: boolean;
}

/**
 * Single source of truth for execution speed mode copy.
 * Wire values stay "turbo" | "balanced" | "smart" for the engine contract;
 * only these display strings are user-facing, written in plain words.
 */
export const SPEED_MODE_META: Record<SpeedMode, SpeedModeMeta> = {
  turbo: {
    label: "Turbo",
    shortDesc: "No pauses, fastest",
    desc: "Works through each step with no pauses. Fastest, for routine work you want done quickly.",
    pace: "Fastest",
    recommended: false,
  },
  balanced: {
    label: "Balanced",
    shortDesc: "Waits for pages to load",
    desc: "Pauses briefly between steps so pages and buttons finish loading. The everyday choice.",
    pace: "Adaptive",
    recommended: true,
  },
  smart: {
    label: "Smart IT",
    shortDesc: "Checks each step",
    desc: "Double-checks each step before moving on. Slower, but steadiest for important work.",
    pace: "Steadiest",
    recommended: false,
  },
};
