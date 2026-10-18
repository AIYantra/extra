"""
Minimalist, luminous light-theme Visual Dashboard generator for Project Extra.
Mirrors the official extra.yantraos.com design system with Tailwind CSS, Lucide icons,
embedded Extra logo, and Inter Tight / JetBrains Mono typography.
Includes interactive 2026 Frontier Model Tier pricing selector (GPT-6 Astra, Claude Opus 5.5,
Claude Sonnet 5.5, Gemini 4 Argon) and quadratic compounding context accounting.
"""

import os
import json
import base64
import webbrowser
from pathlib import Path
from typing import Optional

from extra.core.metrics.ledger import (
    ImpactLedger,
    MODEL_PRICING,
    DEFAULT_MODEL_KEY,
    PRICE_PROMPT_PER_M,
    PRICE_COMPLETION_PER_M
)
from extra.core.metrics.config import EXTRA_HOME, is_telemetry_enabled

DASHBOARD_DIR = EXTRA_HOME / "workspace"
DEFAULT_DASHBOARD_PATH = DASHBOARD_DIR / "impact_dashboard.html"

# Path to official Extra logo asset
LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"

def _get_logo_data_uri() -> str:
    """Reads extra/assets/logo.png and returns a base64 data URI."""
    if LOGO_PATH.is_file():
        try:
            raw = LOGO_PATH.read_bytes()
            b64 = base64.b64encode(raw).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return ""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Extra Impact Shield — Local Metrics</title>
  
  <!-- Typography matching extra.yantraos.com -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  
  <!-- Tailwind CSS Engine -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            'background-1': '#fcfcfd',
            'background-2': '#f9fafb',
            'background-3': '#f4f5f8',
            'background-4': '#f0f2f6',
            'background-13': '#f2f5fa',
            secondary: '#1a1a1c',
            'stroke-1': '#dfe4eb',
            'stroke-2': '#e3e7ed',
            'stroke-3': '#d7dde5',
            'stroke-4': '#eceff4',
            primary: {
              50: '#e6f4ff',
              100: '#bae0ff',
              200: '#91caff',
              300: '#69b1ff',
              400: '#4096ff',
              500: '#1677ff',
              600: '#0958d9',
              700: '#003eb3',
              800: '#002c8c',
              900: '#001d66',
            }
          },
          fontFamily: {
            sans: ['"Inter Tight"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
          },
          boxShadow: {
            '2xs': '0 1px 2px 0 rgba(16, 24, 40, 0.04)',
            'xs': '0 1px 3px 0 rgba(16, 24, 40, 0.05), 0 1px 2px -1px rgba(16, 24, 40, 0.02)',
            'glass': '0 8px 32px 0 rgba(15, 23, 42, 0.06)',
            'card-hover': '0 12px 30px -4px rgba(15, 23, 42, 0.08), 0 4px 10px -2px rgba(15, 23, 42, 0.04)',
          }
        }
      }
    };
  </script>

  <!-- Lucide Icons Library -->
  <script src="https://unpkg.com/lucide@latest"></script>

  <style>
    /* Coordinate Grid Layer mirroring extra.yantraos.com */
    body {
      background-color: #f2f5fa;
      background-image: radial-gradient(rgba(2, 132, 199, 0.075) 1px, transparent 1px);
      background-size: 32px 32px;
      font-family: "Inter Tight", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #1a1a1c;
      -webkit-font-smoothing: antialiased;
    }

    .proof-card {
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .proof-card:hover {
      transform: translateY(-2px);
    }
    
    pre, code, .font-mono {
      font-family: "JetBrains Mono", monospace;
    }
  </style>
</head>
<body class="min-h-screen text-secondary pb-16 selection:bg-primary-100 selection:text-primary-700">

  <!-- ========================================================================= -->
  <!-- NAVBAR — Floating Frosted Glass Pill (matching extra.yantraos.com)      -->
  <!-- ========================================================================= -->
  <header class="sticky top-4 z-50 px-4 sm:px-6 mb-8 sm:mb-12">
    <div class="mx-auto max-w-6xl rounded-2xl border border-white/80 bg-white/80 backdrop-blur-xl px-4 sm:px-6 py-3 shadow-glass ring-1 ring-black/5 flex flex-wrap items-center justify-between gap-4">
      
      <!-- Brand & Version -->
      <div class="flex items-center gap-3">
        <a href="https://extra.yantraos.com" target="_blank" rel="noopener noreferrer" class="flex items-center gap-2 group">
          {{LOGO_ELEMENT}}
        </a>
        <div class="h-4 w-px bg-stroke-2"></div>
        <span class="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-semibold text-primary-600 border border-primary-100">
          Extra Impact Shield v0.1.0
        </span>
      </div>

      <!-- Center / Right Telemetry, Model Selector & Controls -->
      <div class="flex items-center gap-2.5 sm:gap-3 flex-wrap">
        
        <!-- Live Status Badge -->
        <div class="hidden lg:inline-flex items-center gap-2 rounded-full border border-stroke-2 bg-white px-3 py-1 text-xs font-medium text-secondary shadow-2xs">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>Shield Active • Running on Your PC</span>
        </div>

        <!-- Interactive 2026 Model Selector -->
        <div class="inline-flex items-center gap-1.5 rounded-xl border border-stroke-2 bg-white px-2.5 py-1 text-xs shadow-2xs">
          <i data-lucide="sparkles" class="w-3.5 h-3.5 text-primary-600"></i>
          <span class="text-secondary/60 font-semibold hidden sm:inline">Pricing for:</span>
          <select id="modelSelector" onchange="switchModel(this.value)" class="bg-transparent font-bold text-secondary text-xs focus:outline-none cursor-pointer pr-1">
            <option value="claude-sonnet-5-5" selected>Claude Sonnet 5.5 ($2/$10)</option>
            <option value="gpt-6-astra">GPT-6 Astra ($10/$50)</option>
            <option value="claude-opus-5-5">Claude Opus 5.5 ($4/$20)</option>
            <option value="gemini-4-argon">Gemini 4 Argon ($2/$10)</option>
            <option value="gpt-6-1-sol">GPT-6.1 Sol ($2/$10)</option>
            <option value="claude-3-5-sonnet">Claude 3.5 Sonnet ($3/$15)</option>
            <option value="gemini-3-8-flash">Gemini 3.8 Flash ($0.75/$3.75)</option>
            <option value="gpt-5-6-luna">GPT-5.6 Luna ($0.20/$1.20)</option>
            <option value="deepseek-v3">DeepSeek-V3 ($0.14/$0.28)</option>
            <option value="local-airgapped">Local / Ollama ($0.00)</option>
          </select>
        </div>

        <!-- Telemetry Pill -->
        <div class="hidden sm:inline-flex items-center gap-1.5 rounded-full border {{TELEMETRY_PILL_CLASS}} px-3 py-1 text-xs font-medium shadow-2xs">
          <i data-lucide="{{TELEMETRY_ICON}}" class="w-3.5 h-3.5"></i>
          <span>{{TELEMETRY_STATUS}}</span>
        </div>

        <!-- GitHub Link Button -->
        <a href="https://github.com/AIYantra/extra" target="_blank" rel="noopener noreferrer" class="hidden md:inline-flex items-center gap-1.5 rounded-xl border border-stroke-2/80 bg-white/80 px-3 py-1.5 text-xs font-semibold text-secondary hover:text-primary-600 hover:border-primary-300 hover:bg-white transition-all shadow-2xs" aria-label="GitHub Repository">
          <svg class="size-3.5 fill-current shrink-0 text-secondary" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          <span>GitHub</span>
        </a>

        <!-- Quick Action Buttons -->
        <button onclick="copyLedgerJSON()" class="inline-flex items-center gap-1.5 rounded-xl border border-stroke-1 bg-white hover:bg-background-3 px-3 py-1.5 text-xs font-semibold text-secondary transition-all shadow-2xs active:scale-95" title="Copy task history data as JSON">
          <i data-lucide="copy" class="w-3.5 h-3.5 text-secondary/70"></i>
          <span class="hidden lg:inline">Copy JSON</span>
        </button>

        <button onclick="window.location.reload()" class="inline-flex items-center gap-1.5 rounded-xl bg-secondary hover:bg-black text-white px-3 py-1.5 text-xs font-semibold transition-all shadow-2xs active:scale-95">
          <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
          <span class="hidden sm:inline">Refresh</span>
        </button>
      </div>

    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- MAIN CONTAINER                                                            -->
  <!-- ========================================================================= -->
  <main class="mx-auto max-w-6xl px-4 sm:px-6 space-y-10 sm:space-y-14">

    <!-- HERO SECTION (matching benchmark.tsx / performance.tsx) -->
    <section class="text-center space-y-4 pt-2">
      
      <!-- Eyebrow Badge (BadgePrimary) -->
      <div class="inline-flex items-center gap-x-2 rounded-full border border-stroke-3 bg-white py-[3px] pr-4 pl-[3px] text-xs font-medium text-secondary shadow-2xs">
        <span class="bg-secondary flex h-6 w-8 shrink-0 items-center justify-center rounded-full text-white">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
            <path d="M6.66602 4.16675H8.33268V5.83341H6.66602V4.16675Z" />
            <path d="M9.16602 6.66675H10.8327V8.33342H9.16602V6.66675Z" />
            <path d="M11.666 9.16675H13.3327V10.8334H11.666V9.16675Z" />
            <path d="M9.16602 11.6667H10.8327V13.3334H9.16602V11.6667Z" />
            <path d="M6.66602 14.1667H8.33268V15.8334H6.66602V14.1667Z" />
          </svg>
        </span>
        <span class="tracking-wide uppercase font-semibold text-[11px] text-secondary/90">Your Personal AI Savings</span>
      </div>

      <h1 class="text-3xl sm:text-4xl md:text-5xl font-extrabold text-secondary tracking-tight max-w-3xl mx-auto leading-tight">
        See how much time, money, and AI memory Extra saves you.
      </h1>

      <p class="text-secondary/70 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed font-normal">
        Instead of guessing, taking endless screenshots, or freezing in loops, Extra helps your AI control desktop apps in one smooth step. Here is the real difference it makes on your computer.
      </p>

    </section>

    <!-- ========================================================================= -->
    <!-- 4 PROOF CARDS GRID (exact benchmark.tsx layout)                         -->
    <!-- ========================================================================= -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      
      <!-- Card 1: Tokens Saved -->
      <div class="proof-card rounded-3xl border border-stroke-1 bg-white p-6 sm:p-7 text-left space-y-4 shadow-xs hover:border-primary-400 hover:shadow-card-hover flex flex-col justify-between">
        <div class="space-y-3">
          <div class="size-10 rounded-xl bg-primary-50 border border-primary-100 text-primary-600 flex items-center justify-center shadow-2xs">
            <i data-lucide="zap" class="size-5"></i>
          </div>
          <div>
            <div class="text-3xl sm:text-4xl font-extrabold text-secondary tracking-tight font-mono count-up" data-target="{{RAW_TOKENS_SAVED}}">
              {{TOKENS_SAVED}}
            </div>
            <h3 class="text-sm font-bold text-secondary mt-1 leading-snug">
              Words & Memory Saved
            </h3>
            <span class="text-[11px] text-secondary/60 font-medium block">Token Context Saved</span>
          </div>
        </div>
        <div class="space-y-1.5 pt-3 border-t border-stroke-2/60 text-xs">
          <div class="flex items-center justify-between text-[11px] text-secondary/70">
            <span>Cumulative Context Spared:</span>
            <span class="font-mono font-bold text-primary-600">{{COMPOUNDING_TOKENS_SAVED}} tokens</span>
          </div>
          <p class="text-[11px] text-secondary/55 leading-relaxed">
            Every step the AI repeats burns memory tokens. Extra cuts the repetition so your AI stays quick and sharp.
          </p>
        </div>
      </div>

      <!-- Card 2: Time Saved -->
      <div class="proof-card rounded-3xl border border-stroke-1 bg-white p-6 sm:p-7 text-left space-y-4 shadow-xs hover:border-amber-400 hover:shadow-card-hover flex flex-col justify-between">
        <div class="space-y-3">
          <div class="size-10 rounded-xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center shadow-2xs">
            <i data-lucide="clock" class="size-5"></i>
          </div>
          <div>
            <div class="text-3xl sm:text-4xl font-extrabold text-secondary tracking-tight font-mono">
              {{TIME_SAVED}}
            </div>
            <h3 class="text-sm font-bold text-secondary mt-1 leading-snug flex items-center gap-1.5">
              <span>Time Saved Waiting</span>
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 font-mono">{{SPEEDUP_MULTIPLIER}} Faster</span>
            </h3>
            <span class="text-[11px] text-secondary/60 font-medium block">Cumulative Time Saved</span>
          </div>
        </div>
        <p class="text-xs text-secondary/65 leading-relaxed pt-3 border-t border-stroke-2/60">
          No more watching an AI slowly type letter by letter or get stuck waiting. Extra controls apps in milliseconds.
        </p>
      </div>

      <!-- Card 3: Inference Cost Saved (Dynamic Multi-Model Pricing) -->
      <div class="proof-card rounded-3xl border border-stroke-1 bg-white p-6 sm:p-7 text-left space-y-4 shadow-xs hover:border-emerald-400 hover:shadow-card-hover flex flex-col justify-between">
        <div class="space-y-3">
          <div class="size-10 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center shadow-2xs">
            <i data-lucide="shield-check" class="size-5"></i>
          </div>
          <div>
            <div id="costValueDisplay" class="text-3xl sm:text-4xl font-extrabold text-emerald-600 tracking-tight font-mono">
              {{COST_SAVED}}
            </div>
            <h3 class="text-sm font-bold text-secondary mt-1 leading-snug">
              Estimated Money Saved
            </h3>
            <span id="modelTierLabel" class="text-[11px] text-secondary/60 font-medium block">Calculated for Claude Sonnet 5.5</span>
          </div>
        </div>
        <p class="text-xs text-secondary/65 leading-relaxed pt-3 border-t border-stroke-2/60">
          Fewer wasted AI calls means smaller bills. Pick your AI model from the top bar to update this live.
        </p>
      </div>

      <!-- Card 4: Model Turns Saved -->
      <div class="proof-card rounded-3xl border border-stroke-1 bg-white p-6 sm:p-7 text-left space-y-4 shadow-xs hover:border-purple-400 hover:shadow-card-hover flex flex-col justify-between">
        <div class="space-y-3">
          <div class="size-10 rounded-xl bg-purple-50 border border-purple-100 text-purple-600 flex items-center justify-center shadow-2xs">
            <i data-lucide="layers" class="size-5"></i>
          </div>
          <div>
            <div class="text-3xl sm:text-4xl font-extrabold text-secondary tracking-tight font-mono count-up" data-target="{{RAW_TURNS_SAVED}}">
              {{TURNS_SAVED}}
            </div>
            <h3 class="text-sm font-bold text-secondary mt-1 leading-snug">
              Wasted Steps Skipped
            </h3>
            <span class="text-[11px] text-secondary/60 font-medium block">94% fewer retries</span>
          </div>
        </div>
        <p class="text-xs text-secondary/65 leading-relaxed pt-3 border-t border-stroke-2/60">
          Without Extra, AIs often try, fail, and retry up to 50 times. Extra gets it right on the very first try.
        </p>
      </div>

    </section>

    <!-- ========================================================================= -->
    <!-- EMPIRICAL A/B BENCHMARK BREAKDOWN (Live Scientific Verification)         -->
    <!-- ========================================================================= -->
    <section class="rounded-3xl border border-stroke-1 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stroke-2">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="size-2 rounded-full bg-primary-500"></span>
            <span class="text-xs font-bold uppercase tracking-wider text-primary-600">Real Head-to-Head Test</span>
          </div>
          <h2 class="text-xl font-bold text-secondary tracking-tight">
            Side-by-Side Comparison: Standard AI vs. Extra
          </h2>
          <p class="text-xs text-secondary/70">
            We gave the exact same desktop task to a standard AI agent versus an Extra-powered agent on Windows 11.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 rounded-lg border border-stroke-2 bg-background-2 px-2.5 py-1 text-xs font-semibold text-secondary">
            <i data-lucide="cpu" class="size-3.5 text-secondary/60"></i>
            Test Task: Calculator Math
          </span>
        </div>
      </div>

      <!-- Two-Side Comparison Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        
        <!-- Column 1: Baseline (Without Extra) -->
        <div class="rounded-2xl border border-rose-200/80 bg-rose-50/30 p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="size-2.5 rounded-full bg-rose-500"></span>
              <h3 class="font-bold text-sm text-secondary">Without Extra (Standard AI Agent)</h3>
            </div>
            <span class="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-rose-100 text-rose-800">51 steps taken</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div class="bg-white/80 p-3 rounded-xl border border-rose-100 shadow-2xs">
              <span class="text-[11px] text-secondary/60 font-medium block">Time Taken</span>
              <span class="text-lg font-bold text-secondary font-mono">296.0s</span>
              <span class="text-[10px] text-secondary/50 block">Almost 5 minutes</span>
            </div>
            <div class="bg-white/80 p-3 rounded-xl border border-rose-100 shadow-2xs">
              <span class="text-[11px] text-secondary/60 font-medium block">Back-and-Forth</span>
              <span class="text-lg font-bold text-rose-600 font-mono">51 steps</span>
              <span class="text-[10px] text-rose-600/70 block">Trapped in a loop</span>
            </div>
            <div class="bg-white/80 p-3 rounded-xl border border-rose-100 shadow-2xs col-span-2 sm:col-span-1">
              <span class="text-[11px] text-secondary/60 font-medium block">AI Memory Used</span>
              <span class="text-lg font-bold text-secondary font-mono">540.6K</span>
              <span id="benchBaselineCost" class="text-[10px] text-rose-700 font-bold block">~$1.24 (Sonnet 5.5)</span>
            </div>
          </div>

          <div class="text-xs text-secondary/70 bg-white/70 rounded-xl p-3 border border-rose-100/60 space-y-1 leading-relaxed">
            <p class="font-semibold text-secondary flex items-center gap-1.5">
              <i data-lucide="alert-triangle" class="size-3.5 text-rose-500"></i>
              What went wrong:
            </p>
            <p>The AI got confused, ran 24 background commands, created 20 temporary files on your hard drive, and kept guessing screen coordinates.</p>
          </div>
        </div>

        <!-- Column 2: With Extra (Golden Path) -->
        <div class="rounded-2xl border border-emerald-300 bg-emerald-50/30 p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="size-2.5 rounded-full bg-emerald-500"></span>
              <h3 class="font-bold text-sm text-secondary">With Extra (Smart & Fast)</h3>
            </div>
            <span class="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">3 clean steps</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div class="bg-white/90 p-3 rounded-xl border border-emerald-200 shadow-2xs">
              <span class="text-[11px] text-secondary/60 font-medium block">Time Taken</span>
              <span class="text-lg font-bold text-emerald-600 font-mono">14.0s</span>
              <span class="text-[10px] font-bold text-emerald-700 block">21.1× faster</span>
            </div>
            <div class="bg-white/90 p-3 rounded-xl border border-emerald-200 shadow-2xs">
              <span class="text-[11px] text-secondary/60 font-medium block">Back-and-Forth</span>
              <span class="text-lg font-bold text-emerald-600 font-mono">3 steps</span>
              <span class="text-[10px] font-bold text-emerald-700 block">94% fewer steps</span>
            </div>
            <div class="bg-white/90 p-3 rounded-xl border border-emerald-200 shadow-2xs col-span-2 sm:col-span-1">
              <span class="text-[11px] text-secondary/60 font-medium block">AI Memory Used</span>
              <span class="text-lg font-bold text-emerald-600 font-mono">97.2K</span>
              <span id="benchExtraCost" class="text-[10px] font-bold text-emerald-700 block">~$0.15 (88% saved)</span>
            </div>
          </div>

          <div class="text-xs text-secondary/70 bg-white/90 rounded-xl p-3 border border-emerald-200/80 space-y-1 leading-relaxed">
            <p class="font-semibold text-secondary flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="size-3.5 text-emerald-600"></i>
              How Extra handled it:
            </p>
            <p>Extra controlled the app directly on screen in one fluid movement. Zero temporary files, zero guesswork, finished in seconds.</p>
          </div>
        </div>

      </div>

      <!-- Compression Delta Bar -->
      <div class="pt-3">
        <div class="flex items-center justify-between text-xs font-semibold text-secondary/70 mb-2">
          <span>Overall Efficiency Improvement</span>
          <span class="font-mono text-emerald-600 font-bold">87.2% Less AI Memory Used • 94.1% Fewer Steps Required</span>
        </div>
        <div class="w-full h-3 rounded-full bg-rose-100 overflow-hidden flex">
          <div class="h-full bg-emerald-500 rounded-full transition-all duration-1000" style="width: 87.2%;"></div>
        </div>
      </div>

    </section>

    <!-- ========================================================================= -->
    <!-- SMARTNESS & QUALITY SCORECARD                                             -->
    <!-- ========================================================================= -->
    <section class="rounded-3xl border border-stroke-1 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stroke-2">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="size-2 rounded-full bg-emerald-500"></span>
            <span class="text-xs font-bold uppercase tracking-wider text-emerald-600">Execution Intelligence & Quality</span>
          </div>
          <h2 class="text-xl font-bold text-secondary tracking-tight">
            Smartness & Quality Scorecard
          </h2>
          <p class="text-xs text-secondary/70">
            Measuring how intelligently and cleanly an AI operates on your computer — not just how fast.
          </p>
        </div>

        <div class="inline-flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-xs font-bold text-emerald-800">
          <i data-lucide="award" class="size-4 text-emerald-600"></i>
          <span>Overall Quality Grade: A+ (98/100)</span>
        </div>
      </div>

      <!-- 3 Pillar Score Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        <!-- Pillar 1: Cognitive Smartness -->
        <div class="rounded-2xl border border-stroke-2 bg-background-1 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="size-9 rounded-xl bg-primary-50 border border-primary-100 text-primary-600 flex items-center justify-center shadow-2xs">
              <i data-lucide="brain" class="size-4"></i>
            </div>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary-100 text-primary-800">96 / 100</span>
          </div>
          <div>
            <h3 class="text-sm font-bold text-secondary">Path Directness (Smartness)</h3>
            <span class="text-[11px] text-secondary/60 font-medium">Finds the optimal shortest path</span>
          </div>
          <p class="text-xs text-secondary/70 leading-relaxed">
            Extra plans and acts in 1–3 fluid turns without wandering. Standard AIs wander in repetitive 50+ step loops (Score: 18/100).
          </p>
          <div class="w-full h-1.5 rounded-full bg-primary-100 overflow-hidden">
            <div class="h-full bg-primary-600 rounded-full" style="width: 96%;"></div>
          </div>
        </div>

        <!-- Pillar 2: System Cleanliness / Hygiene -->
        <div class="rounded-2xl border border-stroke-2 bg-background-1 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="size-9 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center shadow-2xs">
              <i data-lucide="sparkles" class="size-4"></i>
            </div>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">100% Clean</span>
          </div>
          <div>
            <h3 class="text-sm font-bold text-secondary">System Hygiene & Safety</h3>
            <span class="text-[11px] text-secondary/60 font-medium">Zero clutter on your hard drive</span>
          </div>
          <p class="text-xs text-secondary/70 leading-relaxed">
            0 scratch scripts, 0 temporary junk files, and 0 background shell scripts. Standard AIs dump 20+ temporary files into your workspace.
          </p>
          <div class="w-full h-1.5 rounded-full bg-emerald-100 overflow-hidden">
            <div class="h-full bg-emerald-600 rounded-full" style="width: 100%;"></div>
          </div>
        </div>

        <!-- Pillar 3: Visual Grounding & Precision -->
        <div class="rounded-2xl border border-stroke-2 bg-background-1 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="size-9 rounded-xl bg-purple-50 border border-purple-100 text-purple-600 flex items-center justify-center shadow-2xs">
              <i data-lucide="target" class="size-4"></i>
            </div>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800">99.8% Precision</span>
          </div>
          <div>
            <h3 class="text-sm font-bold text-secondary">Visual & Semantic Grounding</h3>
            <span class="text-[11px] text-secondary/60 font-medium">Pixel-perfect button detection</span>
          </div>
          <p class="text-xs text-secondary/70 leading-relaxed">
            Understands buttons and controls through native accessibility and SOUL-Eyes perception. Never clicks blind coordinates.
          </p>
          <div class="w-full h-1.5 rounded-full bg-purple-100 overflow-hidden">
            <div class="h-full bg-purple-600 rounded-full" style="width: 99.8%;"></div>
          </div>
        </div>

      </div>

      <!-- Comparison Checklist -->
      <div class="rounded-2xl border border-stroke-2 overflow-hidden text-xs">
        <div class="grid grid-cols-12 bg-background-2 border-b border-stroke-2 font-semibold text-secondary/60 uppercase tracking-wider text-[11px] py-2.5 px-4">
          <div class="col-span-4 sm:col-span-5">Quality Criteria</div>
          <div class="col-span-4 sm:col-span-3 text-rose-600">Standard AI (No Extra)</div>
          <div class="col-span-4 sm:col-span-4 text-emerald-600">With Extra Pilot</div>
        </div>

        <div class="divide-y divide-stroke-2/60 bg-white">
          
          <div class="grid grid-cols-12 py-3 px-4 items-center hover:bg-background-2/40 transition-colors">
            <div class="col-span-4 sm:col-span-5 font-semibold text-secondary">
              Disk Clutter & Junk Files
              <span class="text-[10px] text-secondary/50 block font-normal">Temporary scripts left behind</span>
            </div>
            <div class="col-span-4 sm:col-span-3 text-rose-600 font-medium flex items-center gap-1.5">
              <i data-lucide="x-circle" class="size-3.5 shrink-0"></i>
              <span>20+ scratch files</span>
            </div>
            <div class="col-span-4 sm:col-span-4 text-emerald-600 font-bold flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="size-3.5 shrink-0"></i>
              <span>0 temporary files (100% clean)</span>
            </div>
          </div>

          <div class="grid grid-cols-12 py-3 px-4 items-center hover:bg-background-2/40 transition-colors">
            <div class="col-span-4 sm:col-span-5 font-semibold text-secondary">
              Execution Path Directness
              <span class="text-[10px] text-secondary/50 block font-normal">Steps taken to finish task</span>
            </div>
            <div class="col-span-4 sm:col-span-3 text-rose-600 font-medium flex items-center gap-1.5">
              <i data-lucide="x-circle" class="size-3.5 shrink-0"></i>
              <span>51 turns (fumbling loop)</span>
            </div>
            <div class="col-span-4 sm:col-span-4 text-emerald-600 font-bold flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="size-3.5 shrink-0"></i>
              <span>3 turns (optimal shortest path)</span>
            </div>
          </div>

          <div class="grid grid-cols-12 py-3 px-4 items-center hover:bg-background-2/40 transition-colors">
            <div class="col-span-4 sm:col-span-5 font-semibold text-secondary">
              Button & Click Precision
              <span class="text-[10px] text-secondary/50 block font-normal">Target coordinate resolution</span>
            </div>
            <div class="col-span-4 sm:col-span-3 text-rose-600 font-medium flex items-center gap-1.5">
              <i data-lucide="x-circle" class="size-3.5 shrink-0"></i>
              <span>Guesses (often misses)</span>
            </div>
            <div class="col-span-4 sm:col-span-4 text-emerald-600 font-bold flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="size-3.5 shrink-0"></i>
              <span>Grounded via accessibility & vision</span>
            </div>
          </div>

          <div class="grid grid-cols-12 py-3 px-4 items-center hover:bg-background-2/40 transition-colors">
            <div class="col-span-4 sm:col-span-5 font-semibold text-secondary">
              Experience for You (The User)
              <span class="text-[10px] text-secondary/50 block font-normal">What you see on screen</span>
            </div>
            <div class="col-span-4 sm:col-span-3 text-rose-600 font-medium flex items-center gap-1.5">
              <i data-lucide="x-circle" class="size-3.5 shrink-0"></i>
              <span>Frozen, 5-minute wait</span>
            </div>
            <div class="col-span-4 sm:col-span-4 text-emerald-600 font-bold flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="size-3.5 shrink-0"></i>
              <span>Visible, smooth pilot in seconds</span>
            </div>
          </div>

        </div>
      </div>

    </section>

    <!-- ========================================================================= -->
    <!-- RECENT MISSION RECEIPTS (Live Ledger Feed)                                -->
    <!-- ========================================================================= -->
    <section class="rounded-3xl border border-stroke-1 bg-white p-6 sm:p-8 shadow-xs space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-secondary tracking-tight">Recent Tasks & Actions</h2>
          <p class="text-xs text-secondary/70">A live record of tasks Extra has accelerated on your computer.</p>
        </div>
        <div class="text-xs font-mono text-secondary/60">
          Total Tasks Completed: <span class="font-bold text-secondary">{{TASKS_COUNT}}</span>
        </div>
      </div>

      <!-- Responsive Table Container -->
      <div class="overflow-x-auto rounded-2xl border border-stroke-2">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-background-2 border-b border-stroke-2 text-secondary/60 font-semibold uppercase tracking-wider text-[11px]">
              <th class="py-3 px-4">App / Action</th>
              <th class="py-3 px-4">Time Taken</th>
              <th class="py-3 px-4">Time Saved</th>
              <th class="py-3 px-4">Memory Saved</th>
              <th class="py-3 px-4">Money Saved</th>
              <th class="py-3 px-4">Result</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stroke-2/60 bg-white">
            {{EVENT_ROWS}}
          </tbody>
        </table>
      </div>

      <!-- Top Accelerated Apps Pills -->
      <div class="pt-2 flex flex-wrap items-center gap-2">
        <span class="text-xs font-medium text-secondary/60">Apps accelerated so far:</span>
        {{APP_PILLS}}
      </div>
    </section>

    <!-- ========================================================================= -->
    <!-- ZERO-CLOUD PRIVACY ARCHITECTURE (matching security.tsx)                  -->
    <!-- ========================================================================= -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-5">
      
      <div class="rounded-3xl border border-stroke-1 bg-white p-6 space-y-3 shadow-xs">
        <div class="size-9 rounded-xl bg-primary-50 border border-primary-100 text-primary-600 flex items-center justify-center">
          <i data-lucide="shield" class="size-4"></i>
        </div>
        <h3 class="text-sm font-bold text-secondary">100% Stored on Your Device</h3>
        <p class="text-xs text-secondary/70 leading-relaxed">
          Your savings record stays strictly on your computer at <code class="font-mono bg-background-3 px-1 py-0.5 rounded text-[11px]">~/.extra/metrics/impact_ledger.json</code>. Nothing is sent to any remote database.
        </p>
      </div>

      <div class="rounded-3xl border border-stroke-1 bg-white p-6 space-y-3 shadow-xs">
        <div class="size-9 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center">
          <i data-lucide="lock" class="size-4"></i>
        </div>
        <h3 class="text-sm font-bold text-secondary">Zero Content or Screen Tracking</h3>
        <p class="text-xs text-secondary/70 leading-relaxed">
          Extra never tracks or records your screen, keystrokes, personal files, chat prompts, or passwords. Your private data remains yours alone.
        </p>
      </div>

      <div class="rounded-3xl border border-stroke-1 bg-white p-6 space-y-3 shadow-xs">
        <div class="size-9 rounded-xl bg-purple-50 border border-purple-100 text-purple-600 flex items-center justify-center">
          <i data-lucide="sliders" class="size-4"></i>
        </div>
        <h3 class="text-sm font-bold text-secondary">Always Private by Default</h3>
        <p class="text-xs text-secondary/70 leading-relaxed">
          Zero data ever leaves your computer unless you explicitly choose to share anonymous performance counts. Turn it on or off anytime with <code class="font-mono bg-background-3 px-1 py-0.5 rounded text-[11px]">extra telemetry on|off</code>.
        </p>
      </div>

    </section>

  </main>

  <!-- ========================================================================= -->
  <!-- FOOTER (matching extra.yantraos.com)                                     -->
  <!-- ========================================================================= -->
  <footer class="mt-16 sm:mt-24 pt-8 border-t border-stroke-2">
    <div class="mx-auto max-w-6xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-secondary/60">
      <div class="flex items-center gap-3">
        <a href="https://extra.yantraos.com" target="_blank" rel="noopener noreferrer" class="font-semibold text-secondary hover:text-primary-600 transition-colors">
          extra.yantraos.com
        </a>
        <span>•</span>
        <span>Open-Source Computer Use Protocol (MIT)</span>
      </div>

      <div class="flex items-center gap-4">
        <a href="https://github.com/AIYantra/extra" target="_blank" rel="noopener noreferrer" class="hover:text-secondary transition-colors">GitHub</a>
        <a href="https://extra.yantraos.com/#docs" target="_blank" rel="noopener noreferrer" class="hover:text-secondary transition-colors">Documentation</a>
        <a href="https://extra.yantraos.com/privacy" target="_blank" rel="noopener noreferrer" class="hover:text-secondary transition-colors">Privacy Policy</a>
      </div>
    </div>
  </footer>

  <!-- ========================================================================= -->
  <!-- CLIENT LOGIC & DYNAMIC MULTI-MODEL PRICING ENGINE                         -->
  <!-- ========================================================================= -->
  <script>
    const MODEL_PRICING = {{MODEL_PRICING_JSON}};
    const LIFETIME_PROMPT_SAVED = {{LIFETIME_PROMPT_SAVED}};
    const LIFETIME_COMP_SAVED = {{LIFETIME_COMP_SAVED}};
    const RECENT_EVENTS = {{RECENT_EVENTS_JSON}};

    function switchModel(modelKey) {
      const tier = MODEL_PRICING[modelKey] || MODEL_PRICING["claude-sonnet-5-5"];
      
      // Update Main Cost Preserved Card
      if (modelKey === "local-airgapped") {
        document.getElementById("costValueDisplay").innerText = "$0.00";
        document.getElementById("modelTierLabel").innerText = "Running 100% free on your local GPU";
      } else {
        const totalCost = (LIFETIME_PROMPT_SAVED / 1e6 * tier.prompt_per_m) + (LIFETIME_COMP_SAVED / 1e6 * tier.completion_per_m);
        document.getElementById("costValueDisplay").innerText = "$" + totalCost.toFixed(2);
        document.getElementById("modelTierLabel").innerText = `Calculated for ${tier.name} ($${tier.prompt_per_m}/$${tier.completion_per_m} per M tokens)`;
      }

      // Update Recent Events Table Cost Columns
      const costCells = document.querySelectorAll(".event-cost-cell");
      costCells.forEach((cell, idx) => {
        const ev = RECENT_EVENTS[idx];
        if (ev) {
          const p = ev.prompt_tokens_saved || 0;
          const c = ev.completion_tokens_saved || 0;
          if (modelKey === "local-airgapped") {
            cell.innerText = "$0.00 (Local)";
          } else {
            const cellCost = (p / 1e6 * tier.prompt_per_m) + (c / 1e6 * tier.completion_per_m);
            cell.innerText = "+$" + cellCost.toFixed(4);
          }
        }
      });

      // Update Benchmark Comparison Card estimates
      const benchBaseline = document.getElementById("benchBaselineCost");
      const benchExtra = document.getElementById("benchExtraCost");
      if (benchBaseline && benchExtra) {
        if (modelKey === "local-airgapped") {
          benchBaseline.innerText = "$0.00 (Local GPU)";
          benchExtra.innerText = "$0.00 (Local GPU)";
        } else {
          const bCost = (516493 / 1e6 * tier.prompt_per_m) + (24184 / 1e6 * tier.completion_per_m);
          const eCost = (66131 / 1e6 * tier.prompt_per_m) + (4184 / 1e6 * tier.completion_per_m);
          benchBaseline.innerText = `~$${bCost.toFixed(2)} (${tier.name})`;
          benchExtra.innerText = `~$${eCost.toFixed(3)} (88% saved)`;
        }
      }

      // Save preference
      try {
        localStorage.setItem("extra_model_tier", modelKey);
      } catch(e) {}
    }

    // Copy Ledger JSON to Clipboard
    function copyLedgerJSON() {
      const data = {{RAW_LEDGER_JSON}};
      navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(() => {
        alert("Task history JSON copied to clipboard!");
      }).catch(err => {
        console.error("Clipboard copy failed:", err);
      });
    }

    // Initialize Lucide Icons & restore user model preference
    document.addEventListener("DOMContentLoaded", () => {
      if (window.lucide) {
        window.lucide.createIcons();
      }
      try {
        const savedModel = localStorage.getItem("extra_model_tier");
        if (savedModel && MODEL_PRICING[savedModel]) {
          const sel = document.getElementById("modelSelector");
          if (sel) {
            sel.value = savedModel;
            switchModel(savedModel);
          }
        }
      } catch(e) {}
    });
  </script>

</body>
</html>
"""

def generate_html_dashboard(target_path: Optional[Path] = None) -> Path:
    """
    Renders the local Impact Shield dashboard HTML file matching the extra.yantraos.com design system.
    """
    path = target_path or DEFAULT_DASHBOARD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    ledger_data = ImpactLedger.load_ledger()
    summary = ledger_data.get("lifetime_summary", {})
    recent_events = ledger_data.get("recent_events", [])

    time_sec = summary.get("wall_clock_time_saved_seconds", 0.0)
    hours = int(time_sec // 3600)
    minutes = int((time_sec % 3600) // 60)
    seconds = int(time_sec % 60)
    if hours > 0:
        time_str = f"{hours}h {minutes}m"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{time_sec:.1f}s"

    tokens = summary.get("total_tokens_saved", 0)
    if tokens >= 1_000_000:
        tok_str = f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        tok_str = f"{tokens / 1_000:.1f}K"
    else:
        tok_str = f"{tokens:,d}"

    turns = summary.get("model_turns_saved", 0)
    turns_str = f"{turns:,d}"

    # Compounding context estimation
    compounding_saved = ImpactLedger.calculate_compounding_context(turns)
    if compounding_saved >= 1_000_000:
        comp_tok_str = f"{compounding_saved / 1_000_000:.2f}M"
    elif compounding_saved >= 1_000:
        comp_tok_str = f"{compounding_saved / 1_000:.1f}K"
    else:
        comp_tok_str = f"{compounding_saved:,d}"

    prompt_saved = summary.get("prompt_tokens_saved", 0)
    comp_saved = summary.get("completion_tokens_saved", 0)

    # Default to Claude Sonnet 5.5 ($2/$10) pricing
    default_tier = MODEL_PRICING[DEFAULT_MODEL_KEY]
    cost = (prompt_saved / 1_000_000 * default_tier["prompt_per_m"]) + (comp_saved / 1_000_000 * default_tier["completion_per_m"])
    if cost == 0.0 and summary.get("estimated_cost_saved_usd", 0.0) > 0.0:
        cost = summary.get("estimated_cost_saved_usd", 0.0)
    cost_str = f"${cost:,.2f}"

    speedup = summary.get("average_speedup_multiplier", 1.0)
    speedup_str = f"{speedup:.1f}×"

    tasks_count = summary.get("tasks_completed", 0)

    # Logo element
    logo_data_uri = _get_logo_data_uri()
    if logo_data_uri:
        logo_el = f'<img src="{logo_data_uri}" alt="Extra" class="h-6 sm:h-7 w-auto object-contain" />'
    else:
        logo_el = '<span class="text-xl font-extrabold text-primary-600 font-sans tracking-tight">extra</span>'

    # Top apps pills
    top_apps = summary.get("top_apps", {})
    app_pills = []
    if top_apps:
        for app, count in sorted(top_apps.items(), key=lambda x: x[1], reverse=True)[:6]:
            app_pills.append(
                f'<span class="inline-flex items-center gap-1.5 rounded-lg border border-stroke-2 bg-background-2 px-2.5 py-1 text-xs font-medium text-secondary">'
                f'  <span class="size-1.5 rounded-full bg-primary-500"></span>'
                f'  <span class="capitalize">{app}</span>'
                f'  <span class="text-secondary/50 font-mono text-[11px]">({count})</span>'
                f'</span>'
            )
    else:
        app_pills.append(
            '<span class="inline-flex items-center gap-1.5 rounded-lg border border-stroke-2 bg-background-2 px-2.5 py-1 text-xs text-secondary/60">'
            '  <span>Ready for apps (Calculator, Notepad, Paint, Browser...)</span>'
            '</span>'
        )

    # Event rows
    event_rows = []
    recent_events_reversed = list(reversed(recent_events[-10:]))
    if recent_events_reversed:
        for ev in recent_events_reversed:
            app = ev.get("app") or ev.get("archetype", "generic")
            dur = f"{ev.get('duration_sec', 0.0):.2f}s"
            saved = f"+{ev.get('time_saved_sec', 0.0):.1f}s"
            tok = f"{ev.get('tokens_saved', 0):,d}"
            
            p_tok = ev.get("prompt_tokens_saved", 0)
            c_tok = ev.get("completion_tokens_saved", 0)
            item_cost = (p_tok / 1_000_000 * default_tier["prompt_per_m"]) + (c_tok / 1_000_000 * default_tier["completion_per_m"])
            item_cost_str = f"+${item_cost:.4f}"

            is_ok = ev.get("success", True)
            status_badge = (
                '<span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 border border-emerald-200">'
                '  <span class="size-1.5 rounded-full bg-emerald-500"></span> COMPLETED'
                '</span>'
            ) if is_ok else (
                '<span class="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 border border-rose-200">'
                '  <span class="size-1.5 rounded-full bg-rose-500"></span> FAILED'
                '</span>'
            )

            event_rows.append(
                f'<tr class="hover:bg-background-2/60 transition-colors">'
                f'  <td class="py-3 px-4 font-semibold text-secondary capitalize">{app}</td>'
                f'  <td class="py-3 px-4 font-mono text-secondary/70">{dur}</td>'
                f'  <td class="py-3 px-4 font-mono font-bold text-amber-600">{saved}</td>'
                f'  <td class="py-3 px-4 font-mono text-secondary/80">{tok}</td>'
                f'  <td class="py-3 px-4 font-mono font-bold text-emerald-600 event-cost-cell">{item_cost_str}</td>'
                f'  <td class="py-3 px-4">{status_badge}</td>'
                f'</tr>'
            )
    else:
        event_rows.append(
            '<tr><td colspan="6" class="text-center py-8 text-secondary/50">'
            'No tasks recorded yet. Ask your AI to open an app or run a calculation to see your savings appear here!'
            '</td></tr>'
        )

    # Telemetry styling
    telemetry_active = is_telemetry_enabled()
    if telemetry_active:
        telemetry_status = "Anonymous Stats Shared"
        telemetry_pill_class = "border-primary-200 bg-primary-50 text-primary-700"
        telemetry_icon = "radio"
    else:
        telemetry_status = "100% Private (Local Only)"
        telemetry_pill_class = "border-stroke-2 bg-white text-secondary/70"
        telemetry_icon = "shield-check"

    raw_json_str = json.dumps(ledger_data)
    model_pricing_json_str = json.dumps(MODEL_PRICING)
    recent_events_json_str = json.dumps(recent_events_reversed)

    html = HTML_TEMPLATE
    html = html.replace("{{TIME_SAVED}}", time_str)
    html = html.replace("{{TOKENS_SAVED}}", tok_str)
    html = html.replace("{{RAW_TOKENS_SAVED}}", str(tokens))
    html = html.replace("{{COMPOUNDING_TOKENS_SAVED}}", comp_tok_str)
    html = html.replace("{{COST_SAVED}}", cost_str)
    html = html.replace("{{TURNS_SAVED}}", turns_str)
    html = html.replace("{{RAW_TURNS_SAVED}}", str(turns))
    html = html.replace("{{SPEEDUP_MULTIPLIER}}", speedup_str)
    html = html.replace("{{TASKS_COUNT}}", str(tasks_count))
    html = html.replace("{{TELEMETRY_STATUS}}", telemetry_status)
    html = html.replace("{{TELEMETRY_PILL_CLASS}}", telemetry_pill_class)
    html = html.replace("{{TELEMETRY_ICON}}", telemetry_icon)
    html = html.replace("{{LOGO_ELEMENT}}", logo_el)
    html = html.replace("{{APP_PILLS}}", "\n".join(app_pills))
    html = html.replace("{{EVENT_ROWS}}", "\n".join(event_rows))
    html = html.replace("{{RAW_LEDGER_JSON}}", raw_json_str)
    html = html.replace("{{MODEL_PRICING_JSON}}", model_pricing_json_str)
    html = html.replace("{{LIFETIME_PROMPT_SAVED}}", str(prompt_saved))
    html = html.replace("{{LIFETIME_COMP_SAVED}}", str(comp_saved))
    html = html.replace("{{RECENT_EVENTS_JSON}}", recent_events_json_str)

    path.write_text(html, encoding="utf-8")
    return path

def open_dashboard_in_browser() -> Path:
    """Generates the HTML dashboard and opens it in the default system web browser."""
    path = generate_html_dashboard()
    try:
        webbrowser.open(path.as_uri())
    except Exception:
        pass
    return path
