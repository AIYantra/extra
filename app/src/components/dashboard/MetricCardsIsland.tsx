import { Zap, ShieldCheck, Lock } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useEngineStore } from "../../store/useEngineStore";

export function MetricCardsIsland() {
  const telemetry = useEngineStore((state) => state.telemetry);
  const runs = useEngineStore((state) => state.runs);

  const completedRuns = telemetry.tasks_completed ?? runs.length ?? 0;

  // Real settle latency
  const settleLatency =
    telemetry.latency_ms > 0 ? `${telemetry.latency_ms.toFixed(1)}ms` : "< 15ms";

  const metrics = [
    {
      label: "Tasks Completed",
      value: completedRuns.toLocaleString(),
      subtext: completedRuns > 0 ? "Verified" : "Ready",
      subtextColor: "text-emerald-600 dark:text-emerald-400",
      icon: Zap,
      iconColor: "text-emerald-500",
      tooltip: "Total tasks completed locally on your desktop.",
    },
    {
      label: "Average Speed",
      value: settleLatency,
      subtext: "Instant Response",
      subtextColor: "text-indigo-600 dark:text-indigo-400",
      icon: ShieldCheck,
      iconColor: "text-indigo-500",
      tooltip: "Hardware dispatch latency across active applications.",
    },
    {
      label: "Privacy & Control",
      value: "100% Local",
      subtext: "Zero Cloud Data",
      subtextColor: "text-emerald-600 dark:text-emerald-400",
      icon: Lock,
      iconColor: "text-emerald-500",
      tooltip: "All actions and screenshots remain strictly on your device.",
    },
  ];

  return (
    <div className="rounded-xl border border-black/[0.06] dark:border-white/[0.08] bg-white dark:bg-[#121417] p-3.5 shadow-xs select-none">
      <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-black/[0.05] dark:divide-white/[0.06]">
        {metrics.map((m, idx) => {
          const Icon = m.icon;
          return (
            <Tooltip key={m.label}>
              <TooltipTrigger asChild>
                <div
                  className={`flex flex-col justify-between py-1 sm:py-0 ${
                    idx === 0
                      ? "sm:pr-4"
                      : idx === 1
                      ? "sm:px-4"
                      : "sm:pl-4"
                  } cursor-default group`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-medium text-xs text-slate-500 dark:text-zinc-400 tracking-tight">
                      {m.label}
                    </span>
                    <Icon
                      className={`size-3.5 ${m.iconColor} opacity-75 group-hover:opacity-100 transition-opacity`}
                    />
                  </div>

                  <div className="flex items-baseline justify-between">
                    <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white tabular-nums">
                      {m.value}
                    </span>
                    <span
                      className={`text-[11px] font-medium font-mono ${m.subtextColor}`}
                    >
                      {m.subtext}
                    </span>
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent
                side="bottom"
                className="text-xs font-sans max-w-[260px]"
              >
                {m.tooltip}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
