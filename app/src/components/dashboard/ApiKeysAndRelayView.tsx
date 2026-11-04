import { useState, useEffect } from "react";
import {
  Copy,
  Check,
  Eye,
  EyeOff,
  Cloud,
  Laptop,
  CheckCircle2,
  Plus,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { useAuthStore } from "../../store/useAuthStore";
import {
  extraDataService,
  type RealTelemetry,
  type RealApiKey,
  type CloudRelayInfo,
} from "../../services/extraDataService";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";

export function ApiKeysAndRelayView() {
  const { user, relayToken, isAuthenticated, openAuthModal } = useAuthStore();
  const [telemetry, setTelemetry] = useState<RealTelemetry | null>(null);
  const [keys, setKeys] = useState<RealApiKey[]>([]);
  const [relayInfo, setRelayInfo] = useState<CloudRelayInfo | null>(null);
  const [revealedKeyIds, setRevealedKeyIds] = useState<Record<string, boolean>>({});
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSyncingRelay, setIsSyncingRelay] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyScope, setNewKeyScope] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = async () => {
    try {
      const [tel, kList, rInfo] = await Promise.all([
        extraDataService.fetchTelemetry(),
        extraDataService.fetchApiKeys(),
        extraDataService.fetchRelayInfo(),
      ]);
      setTelemetry(tel);
      setKeys(kList);
      setRelayInfo(rInfo);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const machineId =
    telemetry?.anonymous_machine_id ||
    "4b048fc826fd654834ff7e5719890efdbe00f293310f51d822ece97f519736fd";
  const activeRelayToken = relayToken || `ext_live_${machineId.slice(0, 24)}`;

  const handleCopy = (text: string, id: string) => {
    soundEngine.playTick();
    navigator.clipboard.writeText(text);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
    toast.success("Copied to clipboard");
  };

  const toggleReveal = (id: string) => {
    soundEngine.playTick();
    setRevealedKeyIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setIsGenerating(true);
    soundEngine.playTick();
    try {
      const created = await extraDataService.createApiKey(
        newKeyName.trim(),
        newKeyScope,
        isAuthenticated
      );
      if (created) {
        setKeys((prev) => [...prev, created]);
        soundEngine.playSuccessChime();
        toast.success(`Key '${created.name}' created`);
        setNewKeyName("");
        setIsModalOpen(false);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    soundEngine.playTick();
    const success = await extraDataService.revokeApiKey(keyId);
    if (success) {
      setKeys((prev) => prev.filter((k) => k.id !== keyId));
      toast.info("API key revoked");
    }
  };

  const handleSyncRelay = async () => {
    setIsSyncingRelay(true);
    soundEngine.playTick();
    try {
      await extraDataService.syncRelayTelemetry();
      soundEngine.playSuccessChime();
      toast.success(`Synced edge telemetry`);
    } finally {
      setIsSyncingRelay(false);
    }
  };

  const clientJson = JSON.stringify(
    {
      mcpServers: {
        extra: {
          url: isAuthenticated ? "https://extra.yantraos.com/relay" : "http://127.0.0.1:8000/sse",
          headers: isAuthenticated ? { Authorization: `Bearer ${activeRelayToken}` } : {},
        },
      },
    },
    null,
    2
  );

  return (
    <div className="space-y-4 pb-12 animate-in fade-in duration-150">
      {/* Calm Unboxed Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#0a0d14] tracking-tight">
              API Keys & Relay Hub
            </h2>
            <span className="text-[10px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-1.5 py-0.5 rounded-md tabular-nums">
              {keys.length} keys active
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Local DPAPI key authorization and remote tunnel credentials
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <span className="text-xs font-mono text-[#1677ff] bg-blue-50 border border-blue-200/60 px-2 py-0.5 rounded-md">
              {user?.username || user?.email || "Authenticated"}
            </span>
          ) : (
            <button
              onClick={() => {
                soundEngine.playTick();
                openAuthModal();
              }}
              className="text-xs font-medium text-[#525866] hover:text-[#0a0d14] bg-[#f8f9fb] border border-[#dfe4eb] px-2.5 py-1 rounded-md transition-colors duration-150 cursor-pointer"
            >
              Connect cloud
            </button>
          )}

          <button
            onClick={() => {
              soundEngine.playTick();
              setIsModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#0958d9] text-white font-medium text-xs shadow-2xs transition-colors duration-150 cursor-pointer"
          >
            <Plus className="size-3.5" />
            <span>New key</span>
          </button>
        </div>
      </div>

      {/* Cloud Relay Status Strip */}
      <div className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="size-7 rounded-md bg-[#f8f9fb] border border-[#dfe4eb] text-[#525866] flex items-center justify-center shrink-0">
            <Cloud className="size-3.5" />
          </div>
          <div>
            <h3 className="font-semibold text-xs text-[#0a0d14]">
              Cloudflare Edge & AWS Bedrock Relay
            </h3>
            <p className="text-[11px] text-[#868c98] font-mono">
              {relayInfo?.cloudflare_edge || "https://extra.yantraos.com"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-emerald-700 bg-[#edfcf2] border border-[#bbf0cf] px-2 py-0.5 rounded-md tabular-nums">
            {relayInfo?.latency_ms || 14.2}ms
          </span>
          <button
            onClick={handleSyncRelay}
            disabled={isSyncingRelay}
            className="p-1 rounded border border-[#dfe4eb] bg-white text-[#868c98] hover:text-[#0a0d14] hover:bg-[#f8f9fb] transition-colors cursor-pointer"
            title="Sync"
          >
            <RefreshCw className={`size-3.5 ${isSyncingRelay ? "animate-spin text-[#1677ff]" : ""}`} />
          </button>
        </div>
      </div>

      {/* Active API Keys Table */}
      <div className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
        <h3 className="font-semibold text-xs text-[#0a0d14]">
          Scoped Keys
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#dfe4eb] text-[11px] font-medium text-[#868c98]">
                <th className="py-2 px-2.5">Name</th>
                <th className="py-2 px-2.5">Token</th>
                <th className="py-2 px-2.5">Scope</th>
                <th className="py-2 px-2.5">Status</th>
                <th className="py-2 px-2.5">Last Used</th>
                <th className="py-2 px-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#dfe4eb]/60">
              {keys.map((k) => {
                const isRevealed = revealedKeyIds[k.id];
                const isCopied = copiedKeyId === k.id;

                return (
                  <tr key={k.id} className="hover:bg-[#f8f9fb] transition-colors">
                    <td className="py-2 px-2.5 font-medium text-[#0a0d14]">
                      {k.name}
                    </td>

                    <td className="py-2 px-2.5 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[#525866]">
                          {isRevealed ? k.token : `${k.prefix || "ext_"}••••••••••••••••••••`}
                        </span>
                        <button
                          onClick={() => toggleReveal(k.id)}
                          className="p-0.5 rounded text-[#868c98] hover:text-[#0a0d14]"
                          title={isRevealed ? "Hide token" : "Reveal token"}
                        >
                          {isRevealed ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
                        </button>
                      </div>
                    </td>

                    <td className="py-2 px-2.5">
                      <span className="px-1.5 py-0.2 rounded font-mono text-[10px] bg-[#f8f9fb] text-[#1677ff] border border-[#dfe4eb]">
                        {k.scope}
                      </span>
                    </td>

                    <td className="py-2 px-2.5">
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-700 bg-[#edfcf2] border border-[#bbf0cf] px-1.5 py-0.2 rounded">
                        <CheckCircle2 className="size-2.5" />
                        <span>{k.status}</span>
                      </span>
                    </td>

                    <td className="py-2 px-2.5 text-[#868c98] font-mono text-[11px] tabular-nums">
                      {k.last_used_at}
                    </td>

                    <td className="py-2 px-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleCopy(k.token, k.id)}
                          className="p-1 rounded border border-[#dfe4eb] text-[#0a0d14] hover:bg-[#eceff4] transition-colors cursor-pointer"
                          title="Copy token"
                        >
                          {isCopied ? <Check className="size-3 text-emerald-600" /> : <Copy className="size-3 text-[#525866]" />}
                        </button>

                        {k.id !== "key_local_master" && (
                          <button
                            onClick={() => handleRevokeKey(k.id)}
                            className="p-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                            title="Revoke key"
                          >
                            <Trash2 className="size-3" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Client MCP JSON Snippet */}
      <div className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="size-6.5 rounded-md bg-[#f8f9fb] text-[#525866] border border-[#dfe4eb] flex items-center justify-center">
              <Laptop className="size-3" />
            </div>
            <h3 className="font-semibold text-xs text-[#0a0d14]">
              Client Configuration Snippet
            </h3>
          </div>

          <button
            onClick={() => {
              soundEngine.playTick();
              navigator.clipboard.writeText(clientJson);
              setCopiedSnippet(true);
              toast.success("Snippet copied");
              setTimeout(() => setCopiedSnippet(false), 2000);
            }}
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-white hover:bg-[#f8f9fb] border border-[#dfe4eb] text-[#0a0d14] text-xs font-medium shadow-2xs transition-colors cursor-pointer"
          >
            {copiedSnippet ? <Check className="size-3 text-[#0e8345]" /> : <Copy className="size-3 text-[#525866]" />}
            <span>{copiedSnippet ? "Copied" : "Copy"}</span>
          </button>
        </div>

        <pre className="p-2.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-xs text-[#0a0d14] overflow-x-auto">
          {clientJson}
        </pre>
      </div>

      {/* Generate Key Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="w-full max-w-sm p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#dfe4eb]">
              <h3 className="font-semibold text-xs text-[#0a0d14]">Generate API Key</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="size-6 rounded-md bg-[#f8f9fb] text-[#525866] hover:text-[#0a0d14] flex items-center justify-center text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateKey} className="space-y-3 text-xs">
              <div>
                <label className="font-medium text-[#0a0d14] block mb-1">Key Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Cursor IDE Workstation"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-[#dfe4eb] text-xs text-[#0a0d14] focus:outline-none focus:border-[#1677ff] shadow-2xs"
                />
              </div>

              <div>
                <label className="font-medium text-[#0a0d14] block mb-1">Scope</label>
                <select
                  value={newKeyScope}
                  onChange={(e) => setNewKeyScope(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-[#dfe4eb] text-xs text-[#0a0d14] focus:outline-none focus:border-[#1677ff] shadow-2xs"
                >
                  <option value="all">Full actuation + perception</option>
                  <option value="read_only">Perception only</option>
                  <option value="actuation_only">Actuation only</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-2.5 py-1 rounded-md border border-[#dfe4eb] text-[#525866] hover:bg-[#f8f9fb]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating || !newKeyName.trim()}
                  className="px-3 py-1 rounded-md bg-[#1677ff] hover:bg-[#0958d9] text-white font-medium shadow-2xs disabled:opacity-50"
                >
                  {isGenerating ? "Generating..." : "Create key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
