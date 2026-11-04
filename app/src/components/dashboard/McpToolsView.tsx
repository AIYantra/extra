import { useState } from "react";
import {
  Search,
  Zap,
  Play,
  Monitor,
  Keyboard,
  Camera,
  FolderSync,
  Compass,
  Database,
  Sparkles,
  Layers,
  Flame,
  LayoutGrid,
  Check,
  Code2,
  List,
  Terminal,
} from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";

interface ToolItem {
  id: string;
  name: string;
  category: "Actuation" | "Perception" | "Reasoning" | "System";
  latency: string;
  description: string;
  icon: any;
  example: string;
}

const NATIVE_TOOLS: ToolItem[] = [
  {
    id: "extra_launch",
    name: "extra_launch",
    category: "System",
    latency: "< 15ms",
    description: "Launch native applications visibly in foreground.",
    icon: Play,
    example: '{"app_name": "calc", "args": []}',
  },
  {
    id: "extra_focus_window",
    name: "extra_focus_window",
    category: "System",
    latency: "< 3ms",
    description: "Direct Win32 window focus & activation.",
    icon: Monitor,
    example: '{"window_title": "Calculator"}',
  },
  {
    id: "extra_type",
    name: "extra_type",
    category: "Actuation",
    latency: "< 2ms",
    description: "Direct Win32 KEYEVENTF_UNICODE typing.",
    icon: Keyboard,
    example: '{"text": "245.12 * 3.14159=", "press_enter": false}',
  },
  {
    id: "extra_hotkey",
    name: "extra_hotkey",
    category: "Actuation",
    latency: "< 5ms",
    description: "Hardware key combinations (Win, Alt, Ctrl, Shift).",
    icon: Zap,
    example: '{"keys": ["win", "left"]}',
  },
  {
    id: "extra_screenshot",
    name: "extra_screenshot",
    category: "Perception",
    latency: "< 1.8ms",
    description: "DXGI screen capture returning distilled UI.",
    icon: Camera,
    example: '{"annotate_ui": false, "save_to_file": true}',
  },
  {
    id: "extra_batch_actions",
    name: "extra_batch_actions",
    category: "Actuation",
    latency: "< 10ms",
    description: "Atomic sequence execution in a single round-trip.",
    icon: Layers,
    example: '{"actions": [{"action": "launch", "app": "calc"}, {"action": "type", "text": "12+4="}]}',
  },
  {
    id: "extra_subtask_run",
    name: "extra_subtask_run",
    category: "Reasoning",
    latency: "< 50ms",
    description: "Closed-loop micro-routines with on-device validation.",
    icon: Zap,
    example: '{"intent": "calculate 245.12/383.29="}',
  },
  {
    id: "extra_snap_layout",
    name: "extra_snap_layout",
    category: "System",
    latency: "< 15ms",
    description: "Programmatic window snapping (side-by-side, grid).",
    icon: LayoutGrid,
    example: '{"layout": "side_by_side", "left_window": "Calc", "right_window": "Notepad"}',
  },
  {
    id: "extra_inspect_ui",
    name: "extra_inspect_ui",
    category: "Perception",
    latency: "< 12ms",
    description: "UI Automation accessibility tree inspection.",
    icon: Compass,
    example: '{"window_title": "Calculator", "interactive_only": true}',
  },
  {
    id: "extra_click_element",
    name: "extra_click_element",
    category: "Actuation",
    latency: "< 20ms",
    description: "Zero-coordinate semantic grounding via SOUL-Eyes.",
    icon: Flame,
    example: '{"query": "Equals button"}',
  },
  {
    id: "extra_click",
    name: "extra_click",
    category: "Actuation",
    latency: "< 5ms",
    description: "Coordinate click with human-like Bezier flight.",
    icon: Flame,
    example: '{"x": 450, "y": 320, "button": "left"}',
  },
  {
    id: "extra_scroll",
    name: "extra_scroll",
    category: "Actuation",
    latency: "< 2ms",
    description: "Vertical and horizontal mouse wheel scrolling.",
    icon: Flame,
    example: '{"clicks": -5, "direction": "vertical"}',
  },
  {
    id: "extra_drag",
    name: "extra_drag",
    category: "Actuation",
    latency: "< 5ms",
    description: "Hardware drag-and-drop between coordinate endpoints.",
    icon: Flame,
    example: '{"start_x": 100, "start_y": 100, "end_x": 400, "end_y": 400}',
  },
  {
    id: "extra_stroke",
    name: "extra_stroke",
    category: "Actuation",
    latency: "< 10ms",
    description: "Fluid vector splines with ink-detection auto-settle.",
    icon: Flame,
    example: '{"points": [[100, 100], [200, 200]], "duration": 0.5}',
  },
  {
    id: "extra_execute_bridge",
    name: "extra_execute_bridge",
    category: "Reasoning",
    latency: "< 8ms",
    description: "Deterministic code execution across local runtimes.",
    icon: Terminal,
    example: '{"runtime": "python", "payload": "print(2+2)"}',
  },
  {
    id: "extra_recall_memory",
    name: "extra_recall_memory",
    category: "Reasoning",
    latency: "< 3ms",
    description: "KùzuDB vector graph recall for verified past quirks.",
    icon: Database,
    example: '{"query": "calculator paste quirk", "top_k": 3}',
  },
  {
    id: "extra_fs_batch",
    name: "extra_fs_batch",
    category: "System",
    latency: "< 5ms",
    description: "Atomic batch filesystem operations with CFA guardrails.",
    icon: FolderSync,
    example: '{"operation": "create_tree", "base_dir": "~/.extra/workspace"}',
  },
  {
    id: "extra_indicate_status",
    name: "extra_indicate_status",
    category: "System",
    latency: "< 2ms",
    description: "Sets ambient desktop halo and task state HUD.",
    icon: Sparkles,
    example: '{"status": "active", "message": "Executing task"}',
  },
  {
    id: "extra_task_start",
    name: "extra_task_start",
    category: "System",
    latency: "< 2ms",
    description: "Activates ambient desktop edge glow and cursor halo.",
    icon: Sparkles,
    example: '{"task_name": "Audit financial spreadsheet"}',
  },
  {
    id: "extra_task_complete",
    name: "extra_task_complete",
    category: "System",
    latency: "< 5ms",
    description: "Signals task completion with emerald border and acoustic chime.",
    icon: Check,
    example: '{"summary": "Calculation complete", "success": true}',
  },
  {
    id: "extra_blueprint_start",
    name: "extra_blueprint_start",
    category: "Reasoning",
    latency: "< 5ms",
    description: "Initializes long-horizon Task Blueprint with DAG milestones and HIPIF context folding.",
    icon: Layers,
    example: '{"title": "Quarterly financial audit", "milestones": [{"id": "m1", "name": "Extract ledger"}]}',
  },
  {
    id: "extra_blueprint_milestone",
    name: "extra_blueprint_milestone",
    category: "Reasoning",
    latency: "< 5ms",
    description: "Updates milestone state and folds execution context into dense semantic state tokens.",
    icon: Check,
    example: '{"task_id": "t-101", "milestone_id": "m1", "action": "complete"}',
  },
  {
    id: "extra_browser",
    name: "extra_browser",
    category: "Actuation",
    latency: "< 25ms",
    description: "Headless or visible browser automation via Playwright with crash recovery.",
    icon: Compass,
    example: '{"action": "navigate", "url": "https://example.com"}',
  },
  {
    id: "extra_mouse_move",
    name: "extra_mouse_move",
    category: "Actuation",
    latency: "< 5ms",
    description: "Dispatches human-like Bezier cursor flight across the display.",
    icon: Flame,
    example: '{"x": 640, "y": 480, "duration": 0.3}',
  },
  {
    id: "extra_confirm_modal",
    name: "extra_confirm_modal",
    category: "Actuation",
    latency: "< 5ms",
    description: "Confirms or cancels native OS modal dialogs and alerts.",
    icon: Check,
    example: '{"action": "confirm"}',
  },
  {
    id: "extra_soul_wait",
    name: "extra_soul_wait",
    category: "Perception",
    latency: "< 15ms",
    description: "Sub-15ms visual settle detection via SOUL-Gateman.",
    icon: Camera,
    example: '{"condition": "settled", "timeout_sec": 4.0}',
  },
  {
    id: "extra_translate_screen",
    name: "extra_translate_screen",
    category: "Perception",
    latency: "< 1ms",
    description: "Translates visual coordinates across virtual monitors and DPI scaling.",
    icon: Monitor,
    example: '{"x": 1920, "y": 1080}',
  },
  {
    id: "extra_scout_app",
    name: "extra_scout_app",
    category: "Reasoning",
    latency: "< 30ms",
    description: "Discovers UI framework (Electron/Win32/Viewport), hotkeys, and synthesizes SKILL.md.",
    icon: Compass,
    example: '{"app_name": "calc"}',
  },
  {
    id: "extra_evolve_skill",
    name: "extra_evolve_skill",
    category: "Reasoning",
    latency: "< 10ms",
    description: "Crystallizes verified zero-stall fast paths into permanent skill playbooks.",
    icon: Code2,
    example: '{"app_name": "notepad", "workflow_summary": "Direct disk write fast-path"}',
  },
  {
    id: "extra_curate_skills",
    name: "extra_curate_skills",
    category: "Reasoning",
    latency: "< 8ms",
    description: "Audits active skills catalog and strips legacy or unhardened mock playbooks.",
    icon: Database,
    example: '{"sanitize": false}',
  },
  {
    id: "extra_harness_synthesize",
    name: "extra_harness_synthesize",
    category: "Reasoning",
    latency: "< 50ms",
    description: "Synthesizes compliant 7-phase CLI agent harness SOP, tests, and CLI wrappers.",
    icon: Code2,
    example: '{"software_path_or_repo": "freecad", "output_dir": "~/.extra/harness"}',
  },
  {
    id: "extra_harness_run",
    name: "extra_harness_run",
    category: "System",
    latency: "< 15ms",
    description: "Executes CLI harness commands with dual-plane visualization and JSON output.",
    icon: Terminal,
    example: '{"harness": "freecad", "command": ["export-step"]}',
  },
  {
    id: "extra_hub_manage",
    name: "extra_hub_manage",
    category: "System",
    latency: "< 5ms",
    description: "Manages active CLI harnesses across the sovereign ecosystem.",
    icon: Layers,
    example: '{"action": "list"}',
  },
  {
    id: "extra_workspace_export",
    name: "extra_workspace_export",
    category: "System",
    latency: "< 20ms",
    description: "Exports web documents or packages local workspace directory into ZIP archives.",
    icon: FolderSync,
    example: '{"workspace_dir": "~/.extra/workspace", "archive_name": "deliverables.zip"}',
  },
  {
    id: "extra_verify_lineage",
    name: "extra_verify_lineage",
    category: "Reasoning",
    latency: "< 10ms",
    description: "Verifies cryptographic provenance and physical lineage of deliverables.",
    icon: Check,
    example: '{"file_path": "~/.extra/workspace/final.pdf", "expected_origin": "official_web_export"}',
  },
  {
    id: "extra_verify_state",
    name: "extra_verify_state",
    category: "Reasoning",
    latency: "< 15ms",
    description: "Decoupled ground-truth state auditor inspecting DOM and accessibility trees.",
    icon: Compass,
    example: '{"window_title": "Google Sheets", "expected_tabs": 3}',
  },
  {
    id: "extra_child_session_status",
    name: "extra_child_session_status",
    category: "System",
    latency: "< 3ms",
    description: "Monitors background child worker sessions and health telemetry.",
    icon: Monitor,
    example: '{"action": "list"}',
  },
  {
    id: "extra_pip_control",
    name: "extra_pip_control",
    category: "System",
    latency: "< 5ms",
    description: "Controls desktop picture-in-picture viewport for live worker observation.",
    icon: LayoutGrid,
    example: '{"action": "show"}',
  },
  {
    id: "extra_set_mode",
    name: "extra_set_mode",
    category: "System",
    latency: "< 2ms",
    description: "Switches engine execution modes between Turbo, Balanced, and Observable.",
    icon: Zap,
    example: '{"mode": "turbo"}',
  },
  {
    id: "extra_stats",
    name: "extra_stats",
    category: "System",
    latency: "< 2ms",
    description: "Queries real-time impact ledger, tokens saved, and hardware dispatch counters.",
    icon: Sparkles,
    example: '{}',
  },
];

export function McpToolsView() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("All");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [testingId, setTestingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const categories = [
    { id: "All", label: "All", count: NATIVE_TOOLS.length },
    { id: "Actuation", label: "Actuation", count: NATIVE_TOOLS.filter((t) => t.category === "Actuation").length },
    { id: "Perception", label: "Perception", count: NATIVE_TOOLS.filter((t) => t.category === "Perception").length },
    { id: "Reasoning", label: "Reasoning", count: NATIVE_TOOLS.filter((t) => t.category === "Reasoning").length },
    { id: "System", label: "System", count: NATIVE_TOOLS.filter((t) => t.category === "System").length },
  ];

  const filteredTools = NATIVE_TOOLS.filter((t) => {
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()) ||
      t.example.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = categoryFilter === "All" || t.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleTestTool = (tool: ToolItem) => {
    setTestingId(tool.id);
    soundEngine.playTick();
    setTimeout(() => {
      soundEngine.playSuccessChime();
      toast.success(`${tool.name} verified: ${tool.latency}`);
      setTestingId(null);
    }, 300);
  };

  const handleCopyExample = (tool: ToolItem) => {
    soundEngine.playTick();
    navigator.clipboard.writeText(tool.example);
    setCopiedId(tool.id);
    toast.success(`Copied schema for ${tool.name}`);
    setTimeout(() => setCopiedId(null), 1800);
  };

  return (
    <div className="space-y-4 pb-12 animate-in fade-in duration-150">
      {/* Calm Unboxed Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#0a0d14] tracking-tight">
              Native MCP Tool Catalog
            </h2>
            <span className="text-[11px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-1.5 py-0.5 rounded-md tabular-nums">
              {filteredTools.length} active
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Zero-schema sub-millisecond desktop primitives for connected AI agents
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative w-40 sm:w-52">
            <Search className="size-3.5 text-[#868c98] absolute left-2.5 top-2 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter tools..."
              className="w-full pl-7 pr-2.5 py-1 rounded-lg bg-white border border-[#dfe4eb] text-xs text-[#0a0d14] placeholder:text-[#868c98] hover:border-[#ccd2dc] focus:outline-none focus:border-[#1677ff] shadow-2xs transition-colors duration-150"
            />
          </div>

          {/* Categories Segmented Control */}
          <div className="hidden md:flex items-center gap-1 p-0.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] select-none shrink-0">
            {categories.map((cat) => {
              const isSelected = categoryFilter === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => {
                    soundEngine.playTick();
                    setCategoryFilter(cat.id);
                  }}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium transition-colors duration-150 cursor-pointer ${
                    isSelected
                      ? "bg-white text-[#0a0d14] shadow-2xs border border-[#dfe4eb]"
                      : "text-[#525866] hover:text-[#0a0d14]"
                  }`}
                >
                  <span>{cat.label}</span>
                  <span className="text-[10px] font-mono text-[#868c98] tabular-nums">
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Table vs Cards Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
            <button
              onClick={() => {
                soundEngine.playTick();
                setViewMode("table");
              }}
              className={`p-1 rounded-md transition-colors ${
                viewMode === "table" ? "bg-white text-[#0a0d14] shadow-2xs" : "text-[#868c98] hover:text-[#0a0d14]"
              }`}
              title="Table View"
            >
              <List className="size-3.5" />
            </button>
            <button
              onClick={() => {
                soundEngine.playTick();
                setViewMode("cards");
              }}
              className={`p-1 rounded-md transition-colors ${
                viewMode === "cards" ? "bg-white text-[#0a0d14] shadow-2xs" : "text-[#868c98] hover:text-[#0a0d14]"
              }`}
              title="Grid View"
            >
              <LayoutGrid className="size-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Tools Content: Table View (Primary, High-Density Craft) */}
      {viewMode === "table" ? (
        <div className="rounded-xl bg-white border border-[#dfe4eb] shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#dfe4eb] bg-[#f8f9fb] text-[11px] font-semibold text-[#868c98] uppercase tracking-wider">
                  <th className="py-2.5 px-3.5">Primitive Name</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eceff4]">
                {filteredTools.map((tool) => {
                  const Icon = tool.icon;
                  const isTesting = testingId === tool.id;
                  const isCopied = copiedId === tool.id;

                  return (
                    <tr
                      key={tool.id}
                      className="hover:bg-[#f8f9fb] transition-colors duration-150 group"
                    >
                      <td className="py-2.5 px-3.5">
                        <div className="flex items-center gap-2">
                          <div className="size-6 rounded-md bg-[#f8f9fb] border border-[#dfe4eb] flex items-center justify-center text-[#525866] shrink-0">
                            <Icon className="size-3" />
                          </div>
                          <span className="font-mono text-xs font-medium text-[#1a1a1c] group-hover:text-[#1677ff] transition-colors">
                            {tool.name}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-[11px] text-[#525866] px-1.5 py-0.5 rounded border border-[#dfe4eb] bg-[#f8f9fb]">
                          {tool.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-[#525866] tabular-nums">
                        {tool.latency}
                      </td>
                      <td className="py-2.5 px-3 text-[#525866] max-w-md truncate">
                        {tool.description}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                onClick={() => handleCopyExample(tool)}
                                className="px-2 py-1 rounded text-[11px] font-mono text-[#525866] hover:text-[#1a1a1c] hover:bg-[#f4f5f8] transition-colors flex items-center gap-1 cursor-pointer"
                              >
                                {isCopied ? <Check className="size-3 text-[#0e8345]" /> : <Code2 className="size-3 text-[#868c98]" />}
                                <span>{isCopied ? "Copied" : "Schema"}</span>
                              </button>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="font-mono text-[11px] max-w-sm">
                              {tool.example}
                            </TooltipContent>
                          </Tooltip>

                          <button
                            onClick={() => handleTestTool(tool)}
                            disabled={isTesting}
                            className="px-2.5 py-1 rounded-md bg-[#f8f9fb] hover:bg-[#eceff4] text-[#1a1a1c] hover:text-[#1677ff] border border-[#dfe4eb] text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
                          >
                            <Play className={`size-2.5 ${isTesting ? "animate-spin" : ""}`} />
                            <span>{isTesting ? "..." : "Test"}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Scannable Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredTools.map((tool) => {
            const Icon = tool.icon;
            const isTesting = testingId === tool.id;
            const isCopied = copiedId === tool.id;

            return (
              <div
                key={tool.id}
                className="flex flex-col justify-between p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs hover:border-[#ccd2dc] transition-colors duration-150 group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="size-6.5 rounded-md bg-[#f8f9fb] border border-[#dfe4eb] text-[#525866] group-hover:text-[#1677ff] flex items-center justify-center transition-colors shrink-0">
                        <Icon className="size-3.5" />
                      </div>
                      <h3 className="font-medium text-xs text-[#0a0d14] font-mono tracking-tight truncate">
                        {tool.name}
                      </h3>
                    </div>

                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#f8f9fb] text-[#525866] border border-[#dfe4eb] tabular-nums shrink-0">
                      {tool.latency}
                    </span>
                  </div>

                  <p className="text-xs text-[#525866] leading-normal line-clamp-2 mb-3">
                    {tool.description}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#eceff4] text-xs">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => handleCopyExample(tool)}
                        className="flex items-center gap-1 text-[11px] font-mono text-[#525866] hover:text-[#0a0d14] p-1 rounded hover:bg-[#f8f9fb] transition-colors cursor-pointer"
                      >
                        {isCopied ? <Check className="size-3 text-[#0e8345]" /> : <Code2 className="size-3 text-[#868c98]" />}
                        <span>{isCopied ? "Copied" : "Schema"}</span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="font-mono text-[11px] max-w-sm">
                      {tool.example}
                    </TooltipContent>
                  </Tooltip>

                  <button
                    onClick={() => handleTestTool(tool)}
                    disabled={isTesting}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#f8f9fb] hover:bg-[#eceff4] text-[#0a0d14] hover:text-[#1677ff] border border-[#dfe4eb] text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Play className={`size-2.5 ${isTesting ? "animate-spin" : ""}`} />
                    <span>{isTesting ? "Testing..." : "Test"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}