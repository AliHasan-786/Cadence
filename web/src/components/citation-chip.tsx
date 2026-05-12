/**
 * Inline citation chip. Renders as a small badge next to a number/claim.
 *
 * Three visual states by kind:
 *   - dbt:     a tiny code-bracket icon
 *   - spotify: a tiny disc icon
 *   - yaml:    a tiny gear icon
 *
 * Click → opens the resolved URL in a new tab.
 */

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Citation } from "@/lib/citations";

const KIND_LABEL: Record<Citation["kind"], string> = {
  dbt: "dbt",
  spotify: "src",
  yaml: "yml",
};

const KIND_TONE: Record<Citation["kind"], string> = {
  dbt: "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300",
  spotify: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  yaml: "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
};

export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <TooltipProvider delay={150}>
      <Tooltip>
        <TooltipTrigger
          render={
            <a
              href={citation.href}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex h-4 items-center gap-1 rounded-sm border px-1 align-middle font-mono text-[10px] leading-none transition ${KIND_TONE[citation.kind]}`}
            >
              <span className="opacity-60">{KIND_LABEL[citation.kind]}</span>
              <span className="max-w-[10rem] truncate">{citation.label}</span>
            </a>
          }
        />
        <TooltipContent side="top" sideOffset={6} className="max-w-xs text-xs">
          {citation.tooltip}
          <div className="mt-1 truncate font-mono text-[10px] opacity-70">↗ {citation.href}</div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
