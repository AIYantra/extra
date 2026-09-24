#!/usr/bin/env node

/**
 * Extra Desktop — Flashless Computer-Use Engine & MCP Server Launcher
 * Official npm distribution runner for @yantraos/extra-desktop
 */

const { spawn, execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const process = require("node:process");

const isWin = process.platform === "win32";

function isIgnoredPath(p) {
  if (!p) return true;
  const norm = p.toLowerCase().replace(/\\/g, "/");
  return (
    norm.includes("node_modules") ||
    norm.includes("npm-cache") ||
    norm.includes("/_npx/")
  );
}

function findNativeExtra() {
  const home = process.env.USERPROFILE || process.env.HOME || "";

  // 1. Direct check in standard Extra installation directory
  const knownCandidates = isWin
    ? [
        path.join(home, ".extra", "bin", "extra.cmd"),
        path.join(home, ".extra", "bin", "extra.bat"),
        path.join(home, ".extra", "bin", "extra.exe"),
      ]
    : [
        path.join(home, ".extra", "bin", "extra"),
        "/opt/homebrew/bin/extra",
        "/usr/local/bin/extra",
      ];

  for (const candidate of knownCandidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // 2. PATH resolution excluding npm/npx wrappers
  try {
    const finder = isWin ? "where.exe" : "which";
    const stdout = execFileSync(finder, [isWin ? "extra.cmd" : "extra"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 3000,
    });
    const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      if (!isIgnoredPath(line) && fs.existsSync(line)) {
        return line;
      }
    }
  } catch {}

  // 2b. Secondary search for general 'extra' on Windows PATH
  if (isWin) {
    try {
      const stdout = execFileSync("where.exe", ["extra"], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 3000,
      });
      const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
      for (const line of lines) {
        if (
          !isIgnoredPath(line) &&
          /\.(cmd|bat|exe)$/i.test(line) &&
          fs.existsSync(line)
        ) {
          return line;
        }
      }
    } catch {}
  }

  return null;
}

function findExecutable(name) {
  try {
    const finder = isWin ? "where.exe" : "which";
    const stdout = execFileSync(finder, [name], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 3000,
    });
    const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      if (!isIgnoredPath(line) && fs.existsSync(line)) {
        return line;
      }
    }
  } catch {}
  return null;
}

function resolveRunner() {
  // Priority 1: Direct native Extra executable
  const extraBin = findNativeExtra();
  if (extraBin) {
    return { bin: extraBin, prefixArgs: [] };
  }

  // Priority 2: uvx (Astral's ultra-fast ephemeral Python runner)
  const home = process.env.USERPROFILE || process.env.HOME || "";
  const uvxCandidate = isWin
    ? path.join(home, ".local", "bin", "uvx.exe")
    : path.join(home, ".local", "bin", "uvx");
  const uvxBin = (fs.existsSync(uvxCandidate) && uvxCandidate) || findExecutable("uvx");
  if (uvxBin) {
    return { bin: uvxBin, prefixArgs: ["extra-desktop"] };
  }

  // Priority 3: pipx (Isolated tool runner)
  const pipxBin = findExecutable("pipx");
  if (pipxBin) {
    return { bin: pipxBin, prefixArgs: ["run", "extra-desktop"] };
  }

  // Priority 4: Python environment where extra is installed
  const pythonBin = findExecutable(isWin ? "python.exe" : "python3") || findExecutable("python");
  if (pythonBin) {
    try {
      execFileSync(pythonBin, ["-c", "import extra"], {
        stdio: "ignore",
        timeout: 3000,
      });
      return { bin: pythonBin, prefixArgs: ["-m", "extra.cli"] };
    } catch {
      // extra module not in this Python environment
    }
  }

  return null;
}

function run() {
  const userArgs = process.argv.slice(2);
  // Default to "run" (MCP server stdio mode) if invoked with no arguments (e.g. via npx in MCP clients)
  const targetArgs = userArgs.length === 0 ? ["run"] : userArgs;

  const runner = resolveRunner();

  if (!runner) {
    console.error(`
===================================================================
  EXTRA — Native Flashless Computer-Use Engine & MCP Server
===================================================================

[Notice] The underlying native Extra engine is not yet detected on this system.

To install the native Extra engine:
  * Windows (PowerShell): irm https://extra.yantraos.com/install.ps1 | iex
  * macOS (Bash):        curl -sSL https://extra.yantraos.com/install.sh | bash
  * Python pip:          pip install extra-desktop
  * Astral uv:           uv tool install extra-desktop

Homepage:      https://extra.yantraos.com
Documentation: https://extra.yantraos.com/docs
Repository:    https://github.com/AIYantra/extra
`);
    process.exit(1);
  }

  let child;
  const isCmdOrBat = isWin && /\.(cmd|bat)$/i.test(runner.bin);

  if (isCmdOrBat) {
    const comSpec = process.env.ComSpec || "cmd.exe";
    child = spawn(
      comSpec,
      ["/d", "/s", "/c", `"${runner.bin}"`, ...runner.prefixArgs, ...targetArgs],
      {
        stdio: "inherit",
        windowsVerbatimArguments: true,
      }
    );
  } else {
    child = spawn(runner.bin, [...runner.prefixArgs, ...targetArgs], {
      stdio: "inherit",
    });
  }

  child.on("error", (err) => {
    console.error(`[Error] Failed to start Extra process (${runner.bin}):`, err.message);
    process.exit(1);
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
    } else {
      process.exit(code ?? 0);
    }
  });

  const forwardSignals = ["SIGINT", "SIGTERM", "SIGHUP"];
  for (const sig of forwardSignals) {
    process.on(sig, () => {
      if (child.pid && !child.killed) {
        try {
          child.kill(sig);
        } catch {}
      }
    });
  }
}

run();
