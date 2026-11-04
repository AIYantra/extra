import { useEffect } from "react";
import { DashboardLayout } from "./components/dashboard/DashboardLayout";
import { AuthModal } from "./components/auth/AuthModal";
import { FirstFlightWizard } from "./components/onboarding/FirstFlightWizard";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { useAuthStore } from "./store/useAuthStore";
import { useUpdateStore } from "./store/useUpdateStore";

const UPDATE_CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

export function App() {
  useEffect(() => {
    useAuthStore.getState().initFromSecureStorage?.();
  }, []);

  useEffect(() => {
    void useUpdateStore.getState().autoCheckIfDue();
    const timer = window.setInterval(() => {
      void useUpdateStore.getState().autoCheckIfDue();
    }, UPDATE_CHECK_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <TooltipProvider delayDuration={150}>
      <DashboardLayout />
      <FirstFlightWizard />
      <AuthModal />
      <Toaster
        position="bottom-right"
        toastOptions={{
          className: "font-sans text-xs border border-[#dfe4eb] bg-white text-[#1a1a1c] shadow-lg rounded-xl py-2.5 px-3.5 flex items-center gap-2",
        }}
      />
    </TooltipProvider>
  );
}

export default App;
