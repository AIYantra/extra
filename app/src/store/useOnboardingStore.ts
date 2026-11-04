import { create } from "zustand";
import { persist } from "zustand/middleware";
import { extraDataService } from "../services/extraDataService";
import { soundEngine } from "../utils/sound";

export type OnboardingStep = "welcome" | "select_ai" | "connect" | "demo";
export type TargetAI = "chatgpt" | "claude" | "cursor" | "gemini";

interface OnboardingStoreState {
  isOpen: boolean;
  step: OnboardingStep;
  selectedAI: TargetAI | null;
  hasCompletedOnboarding: boolean;
  isDemoRunning: boolean;
  demoResult: string | null;
  demoError: string | null;

  // Actions
  openOnboarding: (initialStep?: OnboardingStep) => void;
  closeOnboarding: () => void;
  setStep: (step: OnboardingStep) => void;
  selectAI: (ai: TargetAI) => void;
  completeOnboarding: () => void;
  triggerLiveDemo: () => Promise<boolean>;
}

export const useOnboardingStore = create<OnboardingStoreState>()(
  persist(
    (set) => ({
      isOpen: false,
      step: "welcome",
      selectedAI: null,
      hasCompletedOnboarding: false,
      isDemoRunning: false,
      demoResult: null,
      demoError: null,

      openOnboarding: (initialStep: OnboardingStep = "welcome") => {
        set({
          isOpen: true,
          step: initialStep,
          demoResult: null,
          demoError: null,
        });
      },

      closeOnboarding: () => {
        set({ isOpen: false });
      },

      setStep: (step: OnboardingStep) => {
        soundEngine.playTick();
        set({ step });
      },

      selectAI: (ai: TargetAI) => {
        soundEngine.playTick();
        set({ selectedAI: ai, step: "connect" });
      },

      completeOnboarding: () => {
        soundEngine.playSuccessChime();
        set({
          hasCompletedOnboarding: true,
          isOpen: false,
        });
        extraDataService.updateConfig({ onboarding_completed: true }).catch(() => {});
      },

      triggerLiveDemo: async () => {
        set({ isDemoRunning: true, demoResult: null, demoError: null });
        soundEngine.playTick();
        try {
          const res = await extraDataService.runLiveDemo();
          if (res.success) {
            soundEngine.playSuccessChime();
            set({
              isDemoRunning: false,
              demoResult: res.result || res.message || "1,000",
            });
            return true;
          } else {
            set({
              isDemoRunning: false,
              demoError: res.error || "Could not complete demonstration",
            });
            return false;
          }
        } catch (e: any) {
          set({
            isDemoRunning: false,
            demoError: e?.message || "Failed to run test",
          });
          return false;
        }
      },
    }),
    {
      name: "extra_first_flight_v1",
      partialize: (state) => ({
        hasCompletedOnboarding: state.hasCompletedOnboarding,
      }),
    }
  )
);
