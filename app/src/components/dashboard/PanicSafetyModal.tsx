import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { OctagonAlert, Play, ShieldAlert, CheckCircle2, Lock } from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";

interface PanicSafetyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PanicSafetyModal({ isOpen, onClose }: PanicSafetyModalProps) {
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const telemetry = useEngineStore((state) => state.telemetry);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const handleResume = () => {
    resumePilot();
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md border-rose-500/40 bg-station-well text-station-text-primary shadow-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2 text-rose-500">
            <span className="p-1 rounded-md bg-rose-500/10 border border-rose-500/20">
              <OctagonAlert className="size-5 text-rose-500" />
            </span>
            <DialogTitle className="text-sm font-semibold tracking-tight text-rose-600 dark:text-rose-200">
              Emergency Hardware Panic Stop Active
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-station-text-muted pt-1 leading-relaxed">
            All low-level Win32 hardware event injections (mouse flight, keyboard keystrokes, and vector drawing strokes) have been severed immediately at the OS kernel boundary.
          </DialogDescription>
        </DialogHeader>

        {/* Audit Status Checks */}
        <div className="p-3 rounded-lg border border-station-border bg-station-elevated space-y-2.5 text-xs font-mono">
          <div className="flex items-center justify-between">
            <span className="text-station-text-muted flex items-center gap-1.5">
              <ShieldAlert className="size-3.5 text-rose-500" />
              Hardware Actuator Hook
            </span>
            <Badge variant="destructive" size="sm" dot>
              Severed (Frozen)
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-station-text-muted flex items-center gap-1.5">
              <Lock className="size-3.5 text-amber-500" />
              Target Isolation
            </span>
            <Badge variant="mono" size="sm" className="bg-station-surface border-station-border text-station-text-muted">
              {telemetry.target_proc || "msedge.exe"} (PID {telemetry.target_pid || 372})
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-station-text-muted flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-emerald-500" />
              Human Operator Priority
            </span>
            <Badge variant="success" size="sm">
              Sovereign Control
            </Badge>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-station-border">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="text-xs border-station-border bg-station-surface text-station-text-muted hover:text-station-text-primary"
          >
            Keep Input Frozen
          </Button>

          {isPanicActive && (
            <Button
              variant="default"
              size="sm"
              onClick={handleResume}
              className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium gap-1.5"
            >
              <Play className="size-3.5 fill-current" />
              <span>Resume Autonomous Pilot</span>
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}