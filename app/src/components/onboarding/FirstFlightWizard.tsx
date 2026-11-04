import { useState, useEffect } from "react";
import {
  Sparkles,
  Calculator,
  Play,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Shield,
  Zap,
  ArrowRight,
  ArrowLeft,
  X,
  Flame,
} from "lucide-react";
import { ExtraLogoIcon } from "../ExtraLogo";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { useAuthStore } from "../../store/useAuthStore";
import { extraDataService } from "../../services/extraDataService";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";

// Import brand logos
import openaiLogo from "../../assets/logos/openai.svg";
import claudeLogo from "../../assets/logos/claude.svg";
import cursorLogo from "../../assets/logos/cursor.svg";
import geminiLogo from "../../assets/logos/gemini.svg";

export function FirstFlightWizard() {
  const {
    isOpen,
    step,
    selectedAI,
    hasCompletedOnboarding,
    isDemoRunning,
    demoResult,
    demoError,
    openOnboarding,
    closeOnboarding,
    setStep,
    selectAI,
    completeOnboarding,
    triggerLiveDemo,
  } = useOnboardingStore();

  const { isAuthenticated, user, relayToken, openAuthModal } = useAuthStore();
  const [copiedLink, setCopiedLink] = useState(false);

  // Auto-open on very first launch
  useEffect(() => {
    if (!hasCompletedOnboarding) {
      // Slight delay so the app renders cleanly first
      const timer = setTimeout(() => {
        openOnboarding("welcome");
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [hasCompletedOnboarding, openOnboarding]);

  if (!isOpen) return null;

  // Compute active relay link
  const activeRelayKey = user?.relay_token || relayToken || "";

  const connectorUrl = activeRelayKey
    ? `https://extra.yantraos.com/mcp?key=${activeRelayKey}`
    : "https://extra.yantraos.com/mcp?key=<get-your-key>";

  const handleCopyConnectorUrl = () => {
    if (!activeRelayKey && !isAuthenticated) {
      toast.info("Please sign in or sign up to generate your private relay key!");
      openAuthModal();
      return;
    }
    navigator.clipboard.writeText(connectorUrl);
    setCopiedLink(true);
    soundEngine.playTick();
    toast.success("Connector URL copied to clipboard!");
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const handleOpenBrowserForAI = async (url: string) => {
    if (activeRelayKey) {
      navigator.clipboard.writeText(connectorUrl);
      toast.success("Connector URL copied! Opening setup page...");
    }
    soundEngine.playTick();
    await extraDataService.openBrowserUrl(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop with subtle blur */}
      <div
        className="fixed inset-0 bg-[#0d1117]/70 backdrop-blur-md transition-opacity duration-300 animate-in fade-in"
        onClick={closeOnboarding}
      />

      {/* Modal Container */}
      <div className="relative z-10 w-full max-w-2xl rounded-3xl bg-white border border-[#dfe4eb] shadow-2xl transition-all duration-300 animate-in zoom-in-95 my-auto overflow-hidden flex flex-col">
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#f0f2f6] bg-[#fafbfd]">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-bold">
              <ExtraLogoIcon className="size-5" />
            </div>
            <div>
              <span className="font-bold text-xs uppercase tracking-wider text-primary">
                First Flight Setup
              </span>
              <h4 className="text-sm font-semibold text-[#1a1a1c]">
                {step === "welcome" && "Welcome to Extra"}
                {step === "select_ai" && "Choose Your AI Assistant"}
                {step === "connect" && "Connect in 1 Click"}
                {step === "demo" && "The 10-Second Magic Test"}
              </h4>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Step Indicators */}
            <div className="flex items-center gap-1.5 mr-2">
              {(["welcome", "select_ai", "connect", "demo"] as const).map((s, idx) => (
                <div
                  key={s}
                  className={`size-2 rounded-full transition-all duration-300 ${
                    step === s
                      ? "w-5 bg-primary"
                      : (["welcome", "select_ai", "connect", "demo"].indexOf(step) > idx)
                      ? "bg-emerald-500"
                      : "bg-[#dfe4eb]"
                  }`}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={closeOnboarding}
              className="size-8 rounded-full flex items-center justify-center text-[#868c98] hover:text-[#1a1a1c] hover:bg-[#f0f2f6] transition-colors cursor-pointer"
              aria-label="Close"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* ================= STEP 1: WELCOME ================= */}
          {step === "welcome" && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="text-center space-y-2 max-w-md mx-auto">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-1">
                  <Sparkles className="size-3.5" />
                  <span>Universal Computer-Use Engine</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1a1a1c] tracking-tight">
                  Give your AI hands and eyes on your computer.
                </h2>
                <p className="text-sm text-[#868c98] leading-relaxed">
                  Extra lets ChatGPT, Claude, and your AI tools see your screen, click buttons, and do real work on your PC — without screen lag or complicated setup.
                </p>
              </div>

              {/* 3 Core Pillars */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                <div className="p-4 rounded-2xl border border-[#dfe4eb] bg-[#fafbfd] space-y-1.5">
                  <div className="size-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                    <Zap className="size-4" />
                  </div>
                  <h4 className="text-xs font-bold text-[#1a1a1c]">Sub-15ms Vision</h4>
                  <p className="text-[11px] text-[#868c98] leading-normal">
                    Real-time desktop capture with zero cloud lag or screen freezing.
                  </p>
                </div>

                <div className="p-4 rounded-2xl border border-[#dfe4eb] bg-[#fafbfd] space-y-1.5">
                  <div className="size-8 rounded-xl bg-blue-50 text-primary flex items-center justify-center font-bold">
                    <Shield className="size-4" />
                  </div>
                  <h4 className="text-xs font-bold text-[#1a1a1c]">100% Private</h4>
                  <p className="text-[11px] text-[#868c98] leading-normal">
                    Runs locally on your PC. Your keystrokes and files stay strictly private.
                  </p>
                </div>

                <div className="p-4 rounded-2xl border border-[#dfe4eb] bg-[#fafbfd] space-y-1.5">
                  <div className="size-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
                    <Flame className="size-4" />
                  </div>
                  <h4 className="text-xs font-bold text-[#1a1a1c]">Hardware Safety</h4>
                  <p className="text-[11px] text-[#868c98] leading-normal">
                    Press <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-[#dfe4eb] text-[10px]">Ctrl+Alt+Esc</kbd> anytime to sever all actuators instantly.
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#f0f2f6]">
                <button
                  type="button"
                  onClick={completeOnboarding}
                  className="text-xs text-[#868c98] hover:text-[#1a1a1c] font-medium transition-colors cursor-pointer order-2 sm:order-1"
                >
                  Skip setup &amp; go directly to Cockpit
                </button>

                <button
                  type="button"
                  onClick={() => setStep("select_ai")}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-primary hover:bg-primary/95 text-white font-bold text-sm shadow-md shadow-primary/20 transition-all active:scale-[0.98] cursor-pointer order-1 sm:order-2"
                >
                  <span>Choose Your AI Assistant</span>
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 2: SELECT AI ================= */}
          {step === "select_ai" && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="space-y-1 text-center sm:text-left">
                <h3 className="text-xl font-bold text-[#1a1a1c]">
                  Which AI do you want to use?
                </h3>
                <p className="text-xs text-[#868c98]">
                  Select your primary tool. Extra can connect to multiple AIs simultaneously.
                </p>
              </div>

              {/* 4 Brand Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* ChatGPT Card */}
                <button
                  type="button"
                  onClick={() => selectAI("chatgpt")}
                  className="p-4 rounded-2xl border-2 border-[#dfe4eb] hover:border-emerald-500 bg-white hover:bg-emerald-50/20 text-left transition-all duration-200 flex items-start gap-3.5 group cursor-pointer active:scale-[0.98]"
                >
                  <div className="size-10 rounded-xl bg-[#10a37f]/10 flex items-center justify-center shrink-0 p-2">
                    <img src={openaiLogo} alt="ChatGPT" className="size-full object-contain" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#1a1a1c]">ChatGPT</span>
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                        Popular
                      </span>
                    </div>
                    <p className="text-xs text-[#868c98] leading-relaxed">
                      chatgpt.com (Web or Desktop). Pilot apps and run calculations via secure cloud tunnel.
                    </p>
                  </div>
                </button>

                {/* Claude Card */}
                <button
                  type="button"
                  onClick={() => selectAI("claude")}
                  className="p-4 rounded-2xl border-2 border-[#dfe4eb] hover:border-[#d97706] bg-white hover:bg-amber-50/20 text-left transition-all duration-200 flex items-start gap-3.5 group cursor-pointer active:scale-[0.98]"
                >
                  <div className="size-10 rounded-xl bg-[#d97706]/10 flex items-center justify-center shrink-0 p-2">
                    <img src={claudeLogo} alt="Claude" className="size-full object-contain" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#1a1a1c]">Claude</span>
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                        Native MCP
                      </span>
                    </div>
                    <p className="text-xs text-[#868c98] leading-relaxed">
                      claude.ai connectors or Claude Desktop. Instant 35+ tool suite with sub-millisecond actuation.
                    </p>
                  </div>
                </button>

                {/* Cursor & Windsurf Card */}
                <button
                  type="button"
                  onClick={() => selectAI("cursor")}
                  className="p-4 rounded-2xl border-2 border-[#dfe4eb] hover:border-primary bg-white hover:bg-primary/5 text-left transition-all duration-200 flex items-start gap-3.5 group cursor-pointer active:scale-[0.98]"
                >
                  <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 p-2">
                    <img src={cursorLogo} alt="Cursor" className="size-full object-contain" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#1a1a1c]">Cursor / Windsurf</span>
                      <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                        Pre-Wired
                      </span>
                    </div>
                    <p className="text-xs text-[#868c98] leading-relaxed">
                      AI Code Editors. Already auto-configured by the installer! Just open your editor.
                    </p>
                  </div>
                </button>

                {/* Google Gemini Card */}
                <button
                  type="button"
                  onClick={() => selectAI("gemini")}
                  className="p-4 rounded-2xl border-2 border-[#dfe4eb] hover:border-blue-500 bg-white hover:bg-blue-50/20 text-left transition-all duration-200 flex items-start gap-3.5 group cursor-pointer active:scale-[0.98]"
                >
                  <div className="size-10 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0 p-2">
                    <img src={geminiLogo} alt="Gemini" className="size-full object-contain" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#1a1a1c]">Google Gemini</span>
                      <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                        Cloud Relay
                      </span>
                    </div>
                    <p className="text-xs text-[#868c98] leading-relaxed">
                      gemini.google.com. Pair your workstation via 1-click OAuth consent dialog.
                    </p>
                  </div>
                </button>
              </div>

              {/* Navigation */}
              <div className="pt-4 flex items-center justify-between border-t border-[#f0f2f6]">
                <button
                  type="button"
                  onClick={() => setStep("welcome")}
                  className="inline-flex items-center gap-1.5 text-xs text-[#868c98] hover:text-[#1a1a1c] font-semibold transition-colors cursor-pointer"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Back</span>
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 3: CONNECT AI ================= */}
          {step === "connect" && (
            <div className="space-y-6 animate-in fade-in duration-200">
              {/* Header depending on chosen AI */}
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-xl bg-[#f0f2f6] flex items-center justify-center p-2 shrink-0">
                  {selectedAI === "chatgpt" && <img src={openaiLogo} alt="ChatGPT" className="size-full" />}
                  {selectedAI === "claude" && <img src={claudeLogo} alt="Claude" className="size-full" />}
                  {selectedAI === "cursor" && <img src={cursorLogo} alt="Cursor" className="size-full" />}
                  {selectedAI === "gemini" && <img src={geminiLogo} alt="Gemini" className="size-full" />}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#1a1a1c]">
                    {selectedAI === "chatgpt" && "Connect ChatGPT to Your PC"}
                    {selectedAI === "claude" && "Connect Claude to Your PC"}
                    {selectedAI === "cursor" && "Cursor & Windsurf Ready!"}
                    {selectedAI === "gemini" && "Connect Google Gemini"}
                  </h3>
                  <p className="text-xs text-[#868c98]">
                    {selectedAI === "cursor"
                      ? "Zero configuration needed. Your local MCP server is already wired."
                      : "Follow the 1-click setup below to bridge your AI with Extra."}
                  </p>
                </div>
              </div>

              {/* CHATGPT OR CLAUDE WEB SETUP */}
              {(selectedAI === "chatgpt" || selectedAI === "claude" || selectedAI === "gemini") && (
                <div className="space-y-4">
                  {/* Endpoint URL Card */}
                  <div className="rounded-2xl border border-[#dfe4eb] bg-[#fafbfd] p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-[#1a1a1c]">Your Private Connector URL</span>
                      {activeRelayKey ? (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          Active &amp; Authenticated
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={openAuthModal}
                          className="text-[11px] font-bold text-primary hover:underline cursor-pointer"
                        >
                          Sign In to Get Your Key →
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2 bg-white rounded-xl border border-[#dfe4eb] px-3 py-2 font-mono text-xs text-[#1a1a1c]">
                      <code className="flex-1 overflow-x-auto select-all text-primary font-semibold">
                        {connectorUrl}
                      </code>
                      <button
                        type="button"
                        onClick={handleCopyConnectorUrl}
                        className="p-1.5 rounded-lg hover:bg-[#f0f2f6] text-[#868c98] hover:text-[#1a1a1c] transition-colors cursor-pointer shrink-0"
                        title="Copy URL"
                      >
                        {copiedLink ? <Check className="size-4 text-emerald-600" /> : <Copy className="size-4" />}
                      </button>
                    </div>

                    <p className="text-[11px] text-[#868c98] leading-relaxed">
                      💡 <strong>Smooth Flow Tip:</strong> In your AI connector settings, choose <strong>"Always Allow"</strong> so your AI doesn't pause for confirmation on every single click or screenshot.
                    </p>
                  </div>

                  {/* 1-Click Launch Button */}
                  <div className="flex flex-col sm:flex-row items-center gap-3">
                    {selectedAI === "chatgpt" && (
                      <button
                        type="button"
                        onClick={() => handleOpenBrowserForAI("https://chatgpt.com")}
                        className="w-full flex-1 inline-flex items-center justify-center gap-2 py-3 px-5 rounded-2xl bg-[#10a37f] hover:bg-[#0e906f] text-white font-bold text-xs shadow-md shadow-[#10a37f]/20 transition-all active:scale-[0.98] cursor-pointer"
                      >
                        <ExternalLink className="size-4" />
                        <span>Open ChatGPT.com &amp; Copy URL</span>
                      </button>
                    )}

                    {selectedAI === "claude" && (
                      <button
                        type="button"
                        onClick={() => handleOpenBrowserForAI("https://claude.ai/settings/connectors")}
                        className="w-full flex-1 inline-flex items-center justify-center gap-2 py-3 px-5 rounded-2xl bg-[#d97706] hover:bg-[#b45309] text-white font-bold text-xs shadow-md shadow-[#d97706]/20 transition-all active:scale-[0.98] cursor-pointer"
                      >
                        <ExternalLink className="size-4" />
                        <span>Open Claude.ai Connectors &amp; Copy URL</span>
                      </button>
                    )}

                    {selectedAI === "gemini" && (
                      <button
                        type="button"
                        onClick={() => handleOpenBrowserForAI("https://gemini.google.com")}
                        className="w-full flex-1 inline-flex items-center justify-center gap-2 py-3 px-5 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-600/20 transition-all active:scale-[0.98] cursor-pointer"
                      >
                        <ExternalLink className="size-4" />
                        <span>Open Google Gemini &amp; Authorize</span>
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* CURSOR / WINDSURF LOCAL SETUP */}
              {selectedAI === "cursor" && (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-5 space-y-4">
                  <div className="flex items-center gap-2.5 text-emerald-800">
                    <CheckCircle2 className="size-5 text-emerald-600 shrink-0" />
                    <span className="font-bold text-sm">Automatic Local Setup Complete</span>
                  </div>

                  <p className="text-xs text-emerald-950/80 leading-relaxed">
                    The 1-liner installer automatically added Extra to your Cursor &amp; Windsurf configuration files. You have full access to all 35+ flashless computer use tools over sub-millisecond local pipes.
                  </p>

                  <div className="p-3 bg-white rounded-xl border border-emerald-200/80 space-y-1.5">
                    <span className="text-[11px] font-bold text-[#1a1a1c] block">Try this prompt in your editor:</span>
                    <div className="flex items-center justify-between gap-2 font-mono text-xs bg-[#f0f2f6] px-3 py-2 rounded-lg text-[#1a1a1c]">
                      <span>@extra calculate 125 * 8 in Calculator and snap to right</span>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText("@extra calculate 125 * 8 in Calculator and snap to right");
                          toast.success("Prompt copied!");
                        }}
                        className="text-primary hover:underline text-[11px] font-bold cursor-pointer shrink-0"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation */}
              <div className="pt-4 flex items-center justify-between border-t border-[#f0f2f6]">
                <button
                  type="button"
                  onClick={() => setStep("select_ai")}
                  className="inline-flex items-center gap-1.5 text-xs text-[#868c98] hover:text-[#1a1a1c] font-semibold transition-colors cursor-pointer"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Choose Another AI</span>
                </button>

                <button
                  type="button"
                  onClick={() => setStep("demo")}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-primary hover:bg-primary/95 text-white font-bold text-xs shadow-md shadow-primary/20 transition-all active:scale-[0.98] cursor-pointer"
                >
                  <span>Next: Try Live Magic Test</span>
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 4: MAGIC DEMO ================= */}
          {step === "demo" && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="text-center space-y-1.5 max-w-md mx-auto">
                <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200 mb-1">
                  <Play className="size-3 fill-emerald-600 text-emerald-600" />
                  <span>Interactive Proof of Flight</span>
                </div>
                <h3 className="text-2xl font-extrabold text-[#1a1a1c]">
                  The 10-Second Magic Test
                </h3>
                <p className="text-xs text-[#868c98] leading-relaxed">
                  Watch Extra safely control your screen right now. We'll open Windows Calculator, compute <code className="font-mono text-primary font-bold">125 * 8</code>, and snap the window cleanly.
                </p>
              </div>

              {/* Interactive Test Panel */}
              <div className="rounded-3xl border border-[#dfe4eb] bg-gradient-to-b from-[#fafbfd] to-white p-6 text-center space-y-4 shadow-sm">
                {!demoResult && !isDemoRunning && (
                  <div className="space-y-3">
                    <div className="size-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-inner">
                      <Calculator className="size-8" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-[#1a1a1c]">Zero Risk Demonstration</h4>
                      <p className="text-xs text-[#868c98] max-w-sm mx-auto">
                        This test only opens Calculator and verifies display vision + input injection. Nothing is saved or modified.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={triggerLiveDemo}
                      className="inline-flex items-center gap-2.5 px-8 py-3.5 rounded-2xl bg-primary hover:bg-primary/95 text-white font-extrabold text-sm shadow-lg shadow-primary/25 transition-all active:scale-95 cursor-pointer mt-2"
                    >
                      <Play className="size-4 fill-white" />
                      <span>Run Live Test on My PC</span>
                    </button>
                  </div>
                )}

                {isDemoRunning && (
                  <div className="py-8 space-y-3">
                    <div className="size-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin mx-auto" />
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-[#1a1a1c]">Executing live desktop test...</h4>
                      <p className="text-xs text-[#868c98]">
                        Opening Calculator, entering numbers, and snapping to right half.
                      </p>
                    </div>
                  </div>
                )}

                {demoResult && (
                  <div className="py-4 space-y-4 animate-in zoom-in-95 duration-300">
                    <div className="size-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                      <CheckCircle2 className="size-8" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-lg font-extrabold text-emerald-900">
                        Extra is Working Live on Your PC!
                      </h4>
                      <p className="text-xs text-[#868c98]">
                        Calculation result: <span className="font-mono font-bold text-emerald-700 text-sm">1,000</span>. Your screen capture, vision, and input injection are 100% active.
                      </p>
                    </div>
                  </div>
                )}

                {demoError && (
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 text-left">
                    <strong>Notice:</strong> {demoError}
                  </div>
                )}
              </div>

              {/* Completion Action */}
              <div className="pt-2 flex items-center justify-between border-t border-[#f0f2f6]">
                <button
                  type="button"
                  onClick={() => setStep("connect")}
                  className="inline-flex items-center gap-1.5 text-xs text-[#868c98] hover:text-[#1a1a1c] font-semibold transition-colors cursor-pointer"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Back</span>
                </button>

                <button
                  type="button"
                  onClick={completeOnboarding}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-[#1a1a1c] hover:bg-black text-white font-bold text-xs shadow-md transition-all active:scale-[0.98] cursor-pointer"
                >
                  <span>Enter Extra Cockpit</span>
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
