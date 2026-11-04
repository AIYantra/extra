# ExtraApp — Design System & Visual Specification (DESIGN.md)
**Aesthetic Style:** Modern Isomorphic High-Density Light Cockpit & Desktop HUD (Matching `extra.yantraos.com` & `nexsas-270`)  
**Framework:** Tailwind CSS v4 + Radix UI Primitives + Lucide Icons + In-Code Procedural SVGs  
**Target Viewport:** 440px System Tray Slide-Out HUD / Expandable to 960px Mission Cockpit  

---

## 1. Visual Identity & Design Principles

ExtraApp adopts the modern **Isomorphic & Nexsas** luminous design language: clean, high-density, card-based surfaces with crisp blueprint paper foundations, electric blue accents, and purposeful tactile micro-interactions.

### The 4 Design Pillars:
1. **High-Density Utility:** Every pixel communicates actionable status. Minimal dead whitespace, zero generic decorative filler.
2. **Crisp Luminous Light Theme (Zero "AI Slop"):** Uses the Stripe/Linear/Nexsas blueprint. Never blinding `#ffffff` on `#ffffff`, but a nuanced 3-step elevation ladder (`#FCFCFD` canvas → `#FFFFFF` cards with sub-pixel inner highlights → `#F4F5F8` control wells).
3. **Tactile Safety Rails:** Interactive controls (especially the Panic Switch and Client Toggles) feel physically distinct with crisp borders, subtle shadows, and active feedback states.
4. **Sub-Pixel Hairlines & Tabular Numbers:** 1px borders (`border-slate-200/80`), tactile inner reflection (`shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]`), and strictly aligned tabular numbers (`font-mono tabular-nums`).

---

## 2. Color Palette & Design Tokens (Synchronized with `extra.yantraos.com`)

### 2.1 Primary Light Theme (Default)
```css
/* Surface Tokens */
--bg-app:        #FCFCFD; /* Primary base canvas */
--bg-card:       #FFFFFF; /* Elevated cockpit cards */
--bg-well:       #F4F5F8; /* Recessed containers & telemetry wells */
--bg-control:    #F0F2F6; /* Inactive pills & badge containers */
--bg-accent-ice: #F2F5FA; /* Selected rows & highlight wells */

/* Border & Hairline Tokens */
--stroke-subtle:   #DFE4EB; /* Hairline borders (Slate-200/80) */
--stroke-strong:   #D7DDE5; /* Active tab & control boundaries */
--stroke-divider:  #ECEFF4; /* Table row dividers */
--shadow-inner:    inset 0 1px 0 0 rgba(255, 255, 255, 0.85);

/* Brand & Functional Accents */
--color-primary:    #1677FF; /* Electric Tech Blue (From extra.yantraos.com) */
--color-primary-50: #E6F4FF; /* Soft blue pill background */
--color-primary-600:#0958D9; /* Button hover & active state */
--color-emerald:    #10B981; /* Verified / Active SOUL State */
--color-emerald-bg: #E8FBC6; /* Soft green pill background */
--color-amber:      #F59E0B; /* Attention / Visual Settle Wait */
--color-amber-bg:   #FDF7BC; /* Soft amber pill background */
--color-crimson:    #EF4444; /* Panic Kill Switch */
--color-crimson-bg: #FEE2E2; /* Panic button backdrop */

/* High-Contrast Typography Tokens */
--text-primary:   #1A1A1C; /* Deep Obsidian Onyx (16.5:1 WCAG AAA contrast) */
--text-secondary: #475569; /* Slate-600 body & labels */
--text-muted:     #94A3B8; /* Slate-400 microcopy & shortcuts */
--text-mono:      "JetBrains Mono", "Geist Mono", monospace;
```

### 2.2 Dark Theme Tokens (Alternative / Night Ops Mode)
```css
--bg-app-dark:        #090D16;
--bg-card-dark:       #0F172A;
--bg-well-dark:       #1E2230;
--border-subtle-dark: rgba(255, 255, 255, 0.08);
--text-primary-dark:  #F8FAFC;
--text-secondary-dark:#94A3B8;
```

---

## 3. Typography Hierarchy

| Level | Size | Weight | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Cockpit Header** | 16px | Bold (700) | -0.02em | App title, primary modal titles |
| **Section Title** | 12px | Semibold (600) | +0.05em (Caps) | Panel headers (`PILOT RADAR`, `IMPACT SHIELD`) |
| **Metric Hero** | 22px | Bold (700) | -0.03em | Counters (Tokens saved, dollars saved) |
| **Body Regular** | 13px | Regular (400) | Normal | Descriptions, helper labels |
| **Status Tag** | 10px | Bold (700) | +0.06em (Caps) | Pill tags (`ACTIVE`, `TURBO`, `IDLE`) |
| **Code / Log** | 11px | Medium (500) | Normal | Audit log, PID tags, coordinates |

---

## 4. Layout Architecture & Panel System

The application operates in two interchangeable modes:

### Mode A: System Tray Slide-Out HUD (Default: 440px × 640px)
Pops open directly above/below the Windows Taskbar or macOS Menu Bar.
- **Top Bar (48px):** Live Pilot status indicator + Emergency Panic Button.
- **Body Area:** Vertically stacked Isomorphic cards:
  1. Active Task & Pilot Radar card.
  2. Impact Shield metrics grid (3 columns: Tokens, Dollars, Time).
  3. Client Configurator row (compact icons with green status dots).
  4. Quick Mission trigger buttons.
- **Footer (32px):** Extra version badge + Expand Window button.

### Mode B: Full Mission Cockpit (Expandable: 960px × 680px)
Pops out into a freestanding window for deep monitoring and audit reviews.
- **Left Sidebar (220px):** Navigation rail (`Cockpit`, `AI Clients`, `Perception Radar`, `Memory & Skills`, `Audit Log`, `Settings`).
- **Main Content Area:** Multi-column Isomorphic layout featuring full screen stream, interactive SoM coordinates inspection, live impact charts, and continuous action history.

---

## 5. Micro-Interactions & Sensory Delight

1. **Active Pilot Breathing Pulse:**
   When an AI assistant is injecting commands, the status pill pulses gently (`animate-pulse`) in electric emerald (`#10B981`) with a subtle radial glow.
2. **Panic Switch Feedback:**
   Hovering over the Panic Button scales it up by 2% (`scale-102`). Clicking triggers a crisp haptic sound effect and instantaneously converts the window border to crimson.
3. **Counter Rollup (NumberFlow):**
   When Extra saves vision tokens or completes a mission, the metric counter rolls smoothly using Spring physics (`@number-flow/react`).
4. **Audit Stream Highlight:**
   Newly dispatched actions flash in subtle cyan before fading to slate, showing the user the exact sub-millisecond heartbeat of the engine.
