"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import type { LlmVerdictRow } from "@/lib/queries";

const PROVIDER_DISPLAY: Record<string, { name: string; tone: string }> = {
  anthropic: { name: "Claude (Anthropic)", tone: "border-l-orange-500" },
  openai: { name: "GPT-4o (OpenAI)", tone: "border-l-emerald-500" },
  google: { name: "Gemini (Google)", tone: "border-l-blue-500" },
};

const RECO_TONE: Record<string, string> = {
  recommend_remove: "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
  recommend_rank_lower: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  recommend_no_action: "bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-300",
};

export function VerdictCard({
  verdict,
  transcriptPrompt,
}: {
  verdict: LlmVerdictRow;
  transcriptPrompt?: string;
}) {
  const [open, setOpen] = useState(false);
  const provider = PROVIDER_DISPLAY[verdict.provider] ?? { name: verdict.provider, tone: "border-l-border" };

  return (
    <>
      <Card className={`border-l-4 ${provider.tone} p-5`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold tracking-tight">{provider.name}</h3>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {verdict.model_name}
            </p>
          </div>
          {verdict.status === "ok" ? (
            <Badge variant="secondary" className={`${RECO_TONE[verdict.llm_recommendation ?? ""] ?? ""} font-mono text-[10px]`}>
              {verdict.llm_recommendation}
            </Badge>
          ) : (
            <Badge variant="destructive" className="font-mono text-[10px]">
              {verdict.status}
            </Badge>
          )}
        </div>

        {verdict.status === "ok" && (
          <>
            <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
              <Stat label="Confidence" value={`${((verdict.llm_confidence ?? 0) * 100).toFixed(0)}%`} />
              <Stat label="Latency" value={`${verdict.latency_ms}ms`} />
              <Stat label="Cost" value={`$${verdict.cost_usd.toFixed(4)}`} />
            </div>

            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">Primary signal: </span>
              <span className="font-mono">{verdict.llm_primary_signal}</span>
            </p>
            {verdict.llm_reasoning && (
              <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                {verdict.llm_reasoning}
              </p>
            )}

            <button
              type="button"
              onClick={() => setOpen(true)}
              className="mt-4 text-xs font-medium text-[#1DB954] hover:underline"
            >
              View verbatim transcript →
            </button>
          </>
        )}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {provider.name} · {verdict.model_name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Prompt</h4>
              <pre className="mt-2 max-h-[40vh] overflow-y-auto rounded-md border border-border/60 bg-muted/40 p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                {transcriptPrompt ?? "(transcript not available — pre-cache JSON gitignored)"}
              </pre>
            </div>
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Verdict response (structured)
              </h4>
              <pre className="mt-2 rounded-md border border-border/60 bg-muted/40 p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                {JSON.stringify(
                  {
                    recommendation: verdict.llm_recommendation,
                    confidence: verdict.llm_confidence,
                    primary_signal: verdict.llm_primary_signal,
                    reasoning: verdict.llm_reasoning,
                  },
                  null,
                  2,
                )}
              </pre>
            </div>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <Stat label="Latency" value={`${verdict.latency_ms} ms`} />
              <Stat label="Cost" value={`$${verdict.cost_usd.toFixed(5)}`} />
              <Stat
                label="Heuristic match"
                value={verdict.llm_agrees_with_heuristic === 1 ? "Yes" : "No"}
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-muted/20 p-2 text-center">
      <p className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}
