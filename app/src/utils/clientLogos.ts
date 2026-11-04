import claudeLogo from "../assets/logos/claude.svg";
import cursorLogo from "../assets/logos/cursor.svg";
import openaiLogo from "../assets/logos/openai.svg";
import windsurfLogo from "../assets/logos/windsurf.svg";
import antigravityLogo from "../assets/logos/antigravity.png";
import copilotLogo from "../assets/logos/githubcopilot.svg";
import geminiLogo from "../assets/logos/gemini.svg";
import deepseekLogo from "../assets/logos/deepseek.svg";
import codeiumLogo from "../assets/logos/codeium.svg";

/**
 * Returns the bundled static SVG/PNG logo asset for known AI clients and coding environments.
 * 100% resilient against null/undefined inputs.
 */
export function getClientLogo(identifier?: string | null): string | null {
  if (!identifier || typeof identifier !== "string") return null;
  const lower = identifier.toLowerCase();
  if (lower.includes("claude")) return claudeLogo;
  if (lower.includes("cursor")) return cursorLogo;
  if (lower.includes("chatgpt") || lower.includes("openai")) return openaiLogo;
  if (lower.includes("windsurf")) return windsurfLogo;
  if (lower.includes("antigravity") || lower.includes("agy")) return antigravityLogo;
  if (lower.includes("copilot")) return copilotLogo;
  if (lower.includes("gemini")) return geminiLogo;
  if (lower.includes("deepseek")) return deepseekLogo;
  if (lower.includes("codeium")) return codeiumLogo;
  return null;
}
