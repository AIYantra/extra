/**
 * KùzuDB Memory Graph Simulation Data & Schema Engine
 * Mirrors the native KùzuDB schema defined in extra.core.memory.db.
 */

export type KuzuNodeType =
  | "Task"
  | "App"
  | "ActionStep"
  | "Artifact"
  | "StallEvent"
  | "AppQuirk"
  | "SoulDecision"
  | "AppSession";

export type KuzuRelType =
  | "TARGETED"
  | "EXECUTED"
  | "PRODUCED"
  | "ENCOUNTERED"
  | "EXHIBITS"
  | "REFINED_BY"
  | "DECIDED"
  | "HAS_SESSION";

export interface KuzuNode {
  id: string;
  type: KuzuNodeType;
  label: string;
  cluster: string;
  properties: Record<string, any>;
  embedding?: number[]; // 384-dimensional FastEmbed vector
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  radius?: number;
}

export interface KuzuEdge {
  id: string;
  source: string;
  target: string;
  type: KuzuRelType;
  label?: string;
  properties?: Record<string, any>;
}

export interface KuzuGraphData {
  nodes: KuzuNode[];
  edges: KuzuEdge[];
}

export interface NodeStyleConfig {
  fill: string;
  stroke: string;
  text: string;
  badgeBg: string;
  badgeText: string;
  radius: number;
  label: string;
}

export const NODE_STYLE_MAP: Record<KuzuNodeType, NodeStyleConfig> = {
  Task: {
    fill: "#1677ff",
    stroke: "#0958d9",
    text: "#ffffff",
    badgeBg: "#e6f4ff",
    badgeText: "#0958d9",
    radius: 18,
    label: "Task",
  },
  App: {
    fill: "#0a0d14",
    stroke: "#27272a",
    text: "#ffffff",
    badgeBg: "#f4f4f5",
    badgeText: "#18181b",
    radius: 20,
    label: "App",
  },
  ActionStep: {
    fill: "#525866",
    stroke: "#3f3f46",
    text: "#ffffff",
    badgeBg: "#f4f4f5",
    badgeText: "#3f3f46",
    radius: 12,
    label: "ActionStep",
  },
  Artifact: {
    fill: "#0e8345",
    stroke: "#096332",
    text: "#ffffff",
    badgeBg: "#edfcf2",
    badgeText: "#0e8345",
    radius: 14,
    label: "Artifact",
  },
  StallEvent: {
    fill: "#d97706",
    stroke: "#b45309",
    text: "#ffffff",
    badgeBg: "#fffbeb",
    badgeText: "#b45309",
    radius: 14,
    label: "StallEvent",
  },
  AppQuirk: {
    fill: "#334155",
    stroke: "#1e293b",
    text: "#ffffff",
    badgeBg: "#f1f5f9",
    badgeText: "#334155",
    radius: 15,
    label: "AppQuirk",
  },
  SoulDecision: {
    fill: "#0284c7",
    stroke: "#0369a1",
    text: "#ffffff",
    badgeBg: "#f0f9ff",
    badgeText: "#0369a1",
    radius: 13,
    label: "SoulDecision",
  },
  AppSession: {
    fill: "#64748b",
    stroke: "#475569",
    text: "#ffffff",
    badgeBg: "#f8fafc",
    badgeText: "#475569",
    radius: 13,
    label: "AppSession",
  },
};

/**
 * Deterministically generates a normalized 384-dimensional synthetic vector
 * using a string seed (e.g. goal or issue text) for reproducible cosine similarity.
 */
export function generateSyntheticEmbedding(seed: string): number[] {
  let h = 0x811c9dc5;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }

  const vec: number[] = new Array(384);
  let sumSq = 0;
  for (let i = 0; i < 384; i++) {
    h = Math.imul(h ^ (i * 2654435761), 0x01000193);
    const val = (h / 0x7fffffff) * 2 - 1;
    vec[i] = val;
    sumSq += val * val;
  }

  const norm = Math.sqrt(sumSq) || 1;
  return vec.map((v) => Number((v / norm).toFixed(5)));
}

/**
 * Computes cosine similarity between two 384-dimensional vectors.
 */
export function computeCosineSimilarity(a: number[], b: number[]): number {
  if (!a || !b || a.length !== b.length) return 0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : Math.max(0, Math.min(1, dot / denom));
}

/**
 * Canonical Initial Seed Graph representing 6 Core Desktop App ecosystems
 * matching Extra's actual hardware automation runs and crystallizations.
 */
export function getInitialSeedGraph(): KuzuGraphData {
  const nodes: KuzuNode[] = [
    // -------------------------------------------------------------------------
    // 1. APPLICATION NODES (Center Anchors)
    // -------------------------------------------------------------------------
    {
      id: "app_calc",
      type: "App",
      label: "Calculator",
      cluster: "calc",
      x: -240,
      y: -120,
      properties: {
        name: "Calculator",
        exe_path: "C:\\Windows\\System32\\calc.exe",
        ui_type: "WinUI3 / XAML",
        process_name: "CalculatorApp.exe",
        window_class: "ApplicationFrameWindow",
      },
    },
    {
      id: "app_sheets",
      type: "App",
      label: "Google Sheets",
      cluster: "sheets",
      x: 220,
      y: -140,
      properties: {
        name: "Google Sheets",
        exe_path: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        ui_type: "Chromium / WebGL Canvas",
        process_name: "msedge.exe",
        domain: "docs.google.com/spreadsheets",
      },
    },
    {
      id: "app_paint",
      type: "App",
      label: "MS Paint",
      cluster: "paint",
      x: -180,
      y: 200,
      properties: {
        name: "MS Paint",
        exe_path: "C:\\Windows\\System32\\mspaint.exe",
        ui_type: "Win32 / DirectWrite",
        process_name: "mspaint.exe",
        window_class: "MSPaintApp",
      },
    },
    {
      id: "app_freecad",
      type: "App",
      label: "FreeCAD",
      cluster: "freecad",
      x: 260,
      y: 180,
      properties: {
        name: "FreeCAD",
        exe_path: "C:\\Program Files\\FreeCAD 0.21\\bin\\FreeCADCmd.exe",
        ui_type: "Qt5 / Coin3D OpenInventor",
        process_name: "FreeCADCmd.exe",
        cli_harness: "freecad-cli",
      },
    },
    {
      id: "app_notepad",
      type: "App",
      label: "Notepad",
      cluster: "notepad",
      x: 0,
      y: -260,
      properties: {
        name: "Notepad",
        exe_path: "C:\\Windows\\System32\\notepad.exe",
        ui_type: "RichEdit Win32",
        process_name: "notepad.exe",
        window_class: "Notepad",
      },
    },
    {
      id: "app_canva",
      type: "App",
      label: "Canva Desktop",
      cluster: "canva",
      x: 0,
      y: 280,
      properties: {
        name: "Canva Desktop",
        exe_path: "C:\\Users\\Operator\\AppData\\Local\\Programs\\Canva\\Canva.exe",
        ui_type: "Electron / HTML5 Canvas",
        process_name: "Canva.exe",
        custom_titlebar: true,
      },
    },

    // -------------------------------------------------------------------------
    // 2. TASK NODES
    // -------------------------------------------------------------------------
    {
      id: "task_101",
      type: "Task",
      label: "Calculate 245.12/383.29",
      cluster: "calc",
      x: -360,
      y: -200,
      embedding: generateSyntheticEmbedding("Calculate division formula 245.12 / 383.29 in calculator"),
      properties: {
        goal: "Calculate 245.12/383.29=",
        summary: "Evaluated arithmetic expression with direct Win32 keystrokes; result verified via OCR.",
        duration_ms: 42.1,
        total_steps: 3,
        success: true,
        timestamp: 1731682100.0,
      },
    },
    {
      id: "task_102",
      type: "Task",
      label: "Nifty50 Financial Model",
      cluster: "sheets",
      x: 360,
      y: -220,
      embedding: generateSyntheticEmbedding("Generate Nifty50 financial model with openpyxl bar chart in Google Sheets"),
      properties: {
        goal: "Create Nifty50 Top 5 gainers model and render auto-updating bar chart",
        summary: "Staged openpyxl workbook with embedded BarChart; imported directly to avoid GUI menu stalls.",
        duration_ms: 1820.5,
        total_steps: 4,
        success: true,
        timestamp: 1731683200.0,
      },
    },
    {
      id: "task_103",
      type: "Task",
      label: "Vector Architecture Sketch",
      cluster: "paint",
      x: -320,
      y: 280,
      embedding: generateSyntheticEmbedding("Draw vector architecture diagram with cubic Bezier brush strokes in MS Paint"),
      properties: {
        goal: "Render system architecture diagram on canvas using cubic Bezier brush splines",
        summary: "Dispatched native Bezier spline waypoints with SOUL optical settle verification.",
        duration_ms: 840.2,
        total_steps: 6,
        success: true,
        timestamp: 1731684500.0,
      },
    },
    {
      id: "task_104",
      type: "Task",
      label: "Headless 3D STEP Export",
      cluster: "freecad",
      x: 380,
      y: 260,
      embedding: generateSyntheticEmbedding("Synthesize parametric 3D CAD mount bracket and export STEP file via FreeCAD harness"),
      properties: {
        goal: "Synthesize motor mount CAD model and export STEP format without UI launch",
        summary: "Executed headless CLI bridge via extra_execute_bridge with FreeCAD Python runtime.",
        duration_ms: 2150.0,
        total_steps: 2,
        success: true,
        timestamp: 1731685800.0,
      },
    },
    {
      id: "task_105",
      type: "Task",
      label: "Fast-Path Executive Brief",
      cluster: "notepad",
      x: -80,
      y: -360,
      embedding: generateSyntheticEmbedding("Write executive briefing report directly to disk and open notepad cleanly"),
      properties: {
        goal: "Draft executive incident report and stage visibly in Notepad",
        summary: "Staged briefing text via direct filesystem write, then invoked extra_launch with file arg.",
        duration_ms: 18.4,
        total_steps: 2,
        success: true,
        timestamp: 1731686900.0,
      },
    },
    {
      id: "task_106",
      type: "Task",
      label: "Marketing Banner Authoring",
      cluster: "canva",
      x: 80,
      y: 380,
      embedding: generateSyntheticEmbedding("Design product marketing banner in Canva desktop with keyboard accelerators"),
      properties: {
        goal: "Create product launch flyer and export high-res PNG",
        summary: "Navigated design canvas using native keyboard accelerators (T, R, C) and clean export gate.",
        duration_ms: 3410.8,
        total_steps: 8,
        success: true,
        timestamp: 1731688100.0,
      },
    },

    // -------------------------------------------------------------------------
    // 3. APP QUIRKS (Crystallized Fast-Paths)
    // -------------------------------------------------------------------------
    {
      id: "quirk_calc_paste",
      type: "AppQuirk",
      label: "VK_PACKET Keystrokes",
      cluster: "calc",
      x: -440,
      y: -60,
      properties: {
        issue: "Windows Calculator rejects Ctrl+V clipboard paste with 'Invalid input' error on formula strings.",
        workaround: "Dispatch raw Win32 KEYEVENTF_UNICODE (VK_PACKET) keystroke injection via extra_type.",
        playbook: "skills/extra-calc/SKILL.md",
        verified_date: "2026-10-24",
      },
    },
    {
      id: "quirk_sheets_menu",
      type: "AppQuirk",
      label: "openpyxl Staged Chart",
      cluster: "sheets",
      x: 390,
      y: -60,
      properties: {
        issue: "Web canvas menu clicks for inserting charts can be fragile and trigger submenu hover mis-clicks.",
        workaround: "Embed openpyxl.chart.BarChart directly in the staged XLSX workbook; Google Sheets auto-translates on import.",
        playbook: "skills/extra-google-sheets/SKILL.md",
        verified_date: "2026-10-28",
      },
    },
    {
      id: "quirk_paint_canvas",
      type: "AppQuirk",
      label: "SOUL Ink-Detection Settle",
      cluster: "paint",
      x: -120,
      y: 320,
      properties: {
        issue: "MS Paint canvas requires sub-15ms optical pixel settle verification before starting the next vector stroke.",
        workaround: "Use extra_soul_wait(condition='settled', timeout_sec=2.0) after dispatching continuous brush splines.",
        playbook: "skills/extra-paint/SKILL.md",
        verified_date: "2026-11-01",
      },
    },
    {
      id: "quirk_canva_titlebar",
      type: "AppQuirk",
      label: "Titlebar Focus Isolation",
      cluster: "canva",
      x: -120,
      y: 420,
      properties: {
        issue: "Canva Electron title bar swallows standard OS Alt+Tab hotkeys when in full-screen canvas mode.",
        workaround: "Actuate canvas center via zero-coordinate SOUL click before sending keyboard accelerators.",
        playbook: "skills/extra-canva/SKILL.md",
        verified_date: "2026-11-04",
      },
    },

    // -------------------------------------------------------------------------
    // 4. STALL EVENTS (Anomalies)
    // -------------------------------------------------------------------------
    {
      id: "stall_calc_01",
      type: "StallEvent",
      label: "Clipboard Paste Blocked",
      cluster: "calc",
      x: -480,
      y: -140,
      properties: {
        strike_count: 1,
        trigger_action: "hotkey(['ctrl', 'v'])",
        resolution: "Fallback to direct Win32 keystrokes",
        latency_lost_ms: 120.4,
      },
    },
    {
      id: "stall_sheets_01",
      type: "StallEvent",
      label: "Submenu Hover Timeout",
      cluster: "sheets",
      x: 480,
      y: -160,
      properties: {
        strike_count: 2,
        trigger_action: "click('Insert > Chart')",
        resolution: "Bypass GUI; stage chart programmatically in XLSX",
        latency_lost_ms: 450.0,
      },
    },

    // -------------------------------------------------------------------------
    // 5. ACTION STEPS
    // -------------------------------------------------------------------------
    {
      id: "step_calc_1",
      type: "ActionStep",
      label: "extra_launch",
      cluster: "calc",
      x: -290,
      y: -260,
      properties: {
        step_num: 1,
        tool_name: "extra_launch",
        parameters: '{"app_name": "calc"}',
        duration_ms: 12.1,
      },
    },
    {
      id: "step_calc_2",
      type: "ActionStep",
      label: "extra_type",
      cluster: "calc",
      x: -380,
      y: -280,
      properties: {
        step_num: 2,
        tool_name: "extra_type",
        parameters: '{"text": "245.12/383.29="}',
        duration_ms: 1.8,
      },
    },
    {
      id: "step_freecad_1",
      type: "ActionStep",
      label: "extra_execute_bridge",
      cluster: "freecad",
      x: 320,
      y: 340,
      properties: {
        step_num: 1,
        tool_name: "extra_execute_bridge",
        parameters: '{"runtime": "python", "payload": "import FreeCAD..."}',
        duration_ms: 1890.0,
      },
    },
    {
      id: "step_paint_1",
      type: "ActionStep",
      label: "extra_stroke",
      cluster: "paint",
      x: -240,
      y: 360,
      properties: {
        step_num: 1,
        tool_name: "extra_stroke",
        parameters: '{"points": [[100, 100], [250, 180]], "smooth": true}',
        duration_ms: 8.4,
      },
    },

    // -------------------------------------------------------------------------
    // 6. ARTIFACTS (Cryptographic Proof Deliverables)
    // -------------------------------------------------------------------------
    {
      id: "art_sheets_xlsx",
      type: "Artifact",
      label: "nifty50_model.xlsx",
      cluster: "sheets",
      x: 460,
      y: -290,
      properties: {
        file_path: "C:\\Users\\Operator\\.extra\\workspace\\nifty50_model.xlsx",
        mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes: 42104,
        sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        provenance: "official_staged_export",
      },
    },
    {
      id: "art_freecad_step",
      type: "Artifact",
      label: "motor_mount.step",
      cluster: "freecad",
      x: 470,
      y: 330,
      properties: {
        file_path: "C:\\Users\\Operator\\.extra\\workspace\\motor_mount.step",
        mime_type: "application/step",
        size_bytes: 189420,
        sha256: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        provenance: "cli_harness_export",
      },
    },
    {
      id: "art_notepad_txt",
      type: "Artifact",
      label: "exec_brief.txt",
      cluster: "notepad",
      x: -120,
      y: -420,
      properties: {
        file_path: "C:\\Users\\Operator\\.extra\\workspace\\exec_brief.txt",
        mime_type: "text/plain",
        size_bytes: 4290,
        sha256: "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
        provenance: "atomic_direct_disk_write",
      },
    },

    // -------------------------------------------------------------------------
    // 7. SOUL DECISIONS
    // -------------------------------------------------------------------------
    {
      id: "soul_dec_1",
      type: "SoulDecision",
      label: "Optical Settle Grounded",
      cluster: "paint",
      x: -380,
      y: 360,
      properties: {
        decision_type: "visual_grounding",
        condition: "Classify state of window 'Untitled - Paint'. Visual diff: phash=4, pixel=0.92.",
        result: "NORMAL_PROGRESS",
        confidence: 0.99,
        latency_ms: 1.2,
      },
    },
    {
      id: "soul_dec_2",
      type: "SoulDecision",
      label: "Actuator VK_PACKET Choice",
      cluster: "calc",
      x: -240,
      y: -320,
      properties: {
        decision_type: "actuator_choice",
        condition: "Formula string detected; standard clipboard paste known to reject.",
        result: "USE_VK_PACKET_UNICODE",
        confidence: 0.98,
        latency_ms: 0.6,
      },
    },

    // -------------------------------------------------------------------------
    // 8. APP SESSIONS
    // -------------------------------------------------------------------------
    {
      id: "sess_google",
      type: "AppSession",
      label: "Google Workspace Profile",
      cluster: "sheets",
      x: 180,
      y: -240,
      properties: {
        service_name: "Google Workspace",
        browser: "Microsoft Edge",
        profile_name: "Profile 1",
        profile_path: "C:\\Users\\Operator\\AppData\\Local\\Microsoft\\Edge\\User Data\\Profile 1",
        last_verified: 1731680000,
      },
    },
  ];

  // ---------------------------------------------------------------------------
  // EDGES (Relational Links)
  // ---------------------------------------------------------------------------
  const edges: KuzuEdge[] = [
    // Task -> App (TARGETED)
    { id: "e1", source: "task_101", target: "app_calc", type: "TARGETED", label: "TARGETED" },
    { id: "e2", source: "task_102", target: "app_sheets", type: "TARGETED", label: "TARGETED" },
    { id: "e3", source: "task_103", target: "app_paint", type: "TARGETED", label: "TARGETED" },
    { id: "e4", source: "task_104", target: "app_freecad", type: "TARGETED", label: "TARGETED" },
    { id: "e5", source: "task_105", target: "app_notepad", type: "TARGETED", label: "TARGETED" },
    { id: "e6", source: "task_106", target: "app_canva", type: "TARGETED", label: "TARGETED" },

    // App -> AppQuirk (EXHIBITS)
    { id: "e7", source: "app_calc", target: "quirk_calc_paste", type: "EXHIBITS", label: "EXHIBITS" },
    { id: "e8", source: "app_sheets", target: "quirk_sheets_menu", type: "EXHIBITS", label: "EXHIBITS" },
    { id: "e9", source: "app_paint", target: "quirk_paint_canvas", type: "EXHIBITS", label: "EXHIBITS" },
    { id: "e10", source: "app_canva", target: "quirk_canva_titlebar", type: "EXHIBITS", label: "EXHIBITS" },

    // Task -> StallEvent (ENCOUNTERED)
    { id: "e11", source: "task_101", target: "stall_calc_01", type: "ENCOUNTERED", label: "ENCOUNTERED" },
    { id: "e12", source: "task_102", target: "stall_sheets_01", type: "ENCOUNTERED", label: "ENCOUNTERED" },

    // StallEvent -> AppQuirk (REFINED_BY)
    { id: "e13", source: "stall_calc_01", target: "quirk_calc_paste", type: "REFINED_BY", label: "REFINED_BY" },
    { id: "e14", source: "stall_sheets_01", target: "quirk_sheets_menu", type: "REFINED_BY", label: "REFINED_BY" },

    // Task -> ActionStep (EXECUTED)
    { id: "e15", source: "task_101", target: "step_calc_1", type: "EXECUTED", label: "EXECUTED" },
    { id: "e16", source: "task_101", target: "step_calc_2", type: "EXECUTED", label: "EXECUTED" },
    { id: "e17", source: "task_104", target: "step_freecad_1", type: "EXECUTED", label: "EXECUTED" },
    { id: "e18", source: "task_103", target: "step_paint_1", type: "EXECUTED", label: "EXECUTED" },

    // Task -> Artifact (PRODUCED)
    { id: "e19", source: "task_102", target: "art_sheets_xlsx", type: "PRODUCED", label: "PRODUCED" },
    { id: "e20", source: "task_104", target: "art_freecad_step", type: "PRODUCED", label: "PRODUCED" },
    { id: "e21", source: "task_105", target: "art_notepad_txt", type: "PRODUCED", label: "PRODUCED" },

    // Task -> SoulDecision (DECIDED)
    { id: "e22", source: "task_103", target: "soul_dec_1", type: "DECIDED", label: "DECIDED" },
    { id: "e23", source: "task_101", target: "soul_dec_2", type: "DECIDED", label: "DECIDED" },

    // App -> AppSession (HAS_SESSION)
    { id: "e24", source: "app_sheets", target: "sess_google", type: "HAS_SESSION", label: "HAS_SESSION" },
  ];

  return { nodes, edges };
}

/**
 * Simulates the ingestion of a new autonomous task trace into the active graph.
 */
export function simulateNewTaskIngestion(currentGraph: KuzuGraphData): {
  newGraph: KuzuGraphData;
  addedTask: KuzuNode;
  summary: string;
} {
  const runId = Math.floor(Math.random() * 900) + 100;
  const taskId = `task_sim_${runId}`;
  const stepId = `step_sim_${runId}`;
  const artId = `art_sim_${runId}`;

  const taskNode: KuzuNode = {
    id: taskId,
    type: "Task",
    label: `CAD Flange Ingestion #${runId}`,
    cluster: "freecad",
    x: 200 + (Math.random() - 0.5) * 60,
    y: 280 + (Math.random() - 0.5) * 60,
    embedding: generateSyntheticEmbedding(`Synthesize circular mounting flange CAD model #${runId} and verify STEP lineage`),
    properties: {
      goal: `Synthesize parametric circular mounting flange #${runId}`,
      summary: "Parametric geometry synthesized via FreeCAD CLI bridge; SHA-256 deliverable validated in Lineage Vault.",
      duration_ms: 1420.0,
      total_steps: 3,
      success: true,
      timestamp: Date.now() / 1000,
    },
  };

  const stepNode: KuzuNode = {
    id: stepId,
    type: "ActionStep",
    label: "extra_harness_run",
    cluster: "freecad",
    x: 240 + (Math.random() - 0.5) * 40,
    y: 360 + (Math.random() - 0.5) * 40,
    properties: {
      step_num: 1,
      tool_name: "extra_harness_run",
      parameters: '{"harness": "freecad", "command": ["export-flange"]}',
      duration_ms: 980.0,
    },
  };

  const artifactNode: KuzuNode = {
    id: artId,
    type: "Artifact",
    label: `flange_${runId}.step`,
    cluster: "freecad",
    x: 340 + (Math.random() - 0.5) * 40,
    y: 380 + (Math.random() - 0.5) * 40,
    properties: {
      file_path: `C:\\Users\\Operator\\.extra\\workspace\\flange_${runId}.step`,
      mime_type: "application/step",
      size_bytes: 84210,
      sha256: Math.random().toString(36).substring(2) + "a89fc7",
      provenance: "cli_harness_export",
    },
  };

  const newEdges: KuzuEdge[] = [
    {
      id: `e_sim_t_app_${runId}`,
      source: taskId,
      target: "app_freecad",
      type: "TARGETED",
      label: "TARGETED",
    },
    {
      id: `e_sim_t_step_${runId}`,
      source: taskId,
      target: stepId,
      type: "EXECUTED",
      label: "EXECUTED",
    },
    {
      id: `e_sim_t_art_${runId}`,
      source: taskId,
      target: artId,
      type: "PRODUCED",
      label: "PRODUCED",
    },
  ];

  return {
    newGraph: {
      nodes: [...currentGraph.nodes, taskNode, stepNode, artifactNode],
      edges: [...currentGraph.edges, ...newEdges],
    },
    addedTask: taskNode,
    summary: `Ingested Task #${runId}: Parametric CAD Flange with 1 ActionStep and 1 Artifact linked to FreeCAD.`,
  };
}
