import { ReferenceDashboardView } from "./ReferenceDashboardView";

interface DashboardOverviewProps {
  onNavigateTab?: (tab: string) => void;
}

export function DashboardOverview({ onNavigateTab }: DashboardOverviewProps) {
  return (
    <div className="w-full max-w-[1280px] mx-auto animate-in fade-in duration-150">
      <ReferenceDashboardView onNavigateTab={onNavigateTab} />
    </div>
  );
}
