import { CitationChip } from "@/components/citation-chip";
import { Card } from "@/components/ui/card";
import { citeDbtModel, citeSpotifyXlsx } from "@/lib/citations";
import type { CrossProductRow } from "@/lib/queries";

const PRODUCT_DISPLAY: Record<string, { name: string; tone: string }> = {
  main: { name: "Spotify Main", tone: "border-l-[#1DB954]" },
  artists: { name: "Spotify for Artists", tone: "border-l-blue-500" },
  authors: { name: "Spotify for Authors", tone: "border-l-amber-500" },
  creators: { name: "Spotify for Creators", tone: "border-l-purple-500" },
};

function fmt(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US", opts).format(n);
}

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(2)}%`;
}

function ProductColumn({ row, citation }: { row: CrossProductRow; citation: ReturnType<typeof citeSpotifyXlsx> }) {
  const display = PRODUCT_DISPLAY[row.product_line] ?? { name: row.product_line, tone: "border-l-border" };
  return (
    <Card className={`border-l-4 ${display.tone} p-5`}>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold tracking-tight">{display.name}</h3>
          <p className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            Annual 2025
          </p>
        </div>
        <CitationChip citation={citation} />
      </div>

      <dl className="space-y-3 text-sm">
        <Row label="Notices received" value={fmt(row.notices_received)} />
        <Row label="Items in notices" value={fmt(row.items_in_notices)} />
        <div className="border-t border-border/40 pt-3" />
        <Row label="Notice → actions on law" value={fmt(row.actions_on_law)} />
        <Row label="Notice → actions on T&amp;C" value={fmt(row.actions_on_tc)} />
        <Row label="Own-initiative measures" value={fmt(row.own_initiative_total)} />
        <div className="border-t border-border/40 pt-3" />
        <Row label="Total decisions" value={fmt(row.total_decisions)} bold />
        <Row label="Automated %" value={pct(row.automated_share_pct)} bold />
        <div className="border-t border-border/40 pt-3" />
        <Row label="Median time-to-act" value={`${row.median_time_to_take_action_hours ?? 0}h`} />
        <Row label="Internal complaints" value={fmt(row.complaints_submitted ?? 0)} />
        <div className="border-t border-border/40 pt-3" />
        <Row label="Automation accuracy" value={pct(row.automated_accuracy_pct)} />
        <Row label="Automation precision" value={pct(row.automated_precision_pct)} />
        <Row label="Automation recall" value={pct(row.automated_recall_pct)} />
      </dl>
    </Card>
  );
}

function Row({ label, value, bold = false }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">
        <span dangerouslySetInnerHTML={{ __html: label }} />
      </dt>
      <dd
        className={`font-mono tabular-nums ${bold ? "text-base font-semibold" : "text-sm"}`}
      >
        {value}
      </dd>
    </div>
  );
}

export function CrossProductGrid({ rows }: { rows: CrossProductRow[] }) {
  // Sort to canonical product order
  const order = ["main", "artists", "authors", "creators"];
  const sorted = [...rows].sort((a, b) => order.indexOf(a.product_line) - order.indexOf(b.product_line));

  const cite = citeDbtModel("rpt_cross_product_summary", { layer: "marts/transparency" });

  return (
    <div className="space-y-4">
      <div className="text-xs text-muted-foreground">
        Source · {" "}
        <CitationChip citation={cite} /> {" "}
        joined from {" "}
        <CitationChip citation={citeDbtModel("fct_dsa_decisions", { layer: "marts/transparency" })} /> + {" "}
        <CitationChip citation={citeDbtModel("int_dsa_appeals", { layer: "intermediate" })} /> + {" "}
        <CitationChip citation={citeDbtModel("int_dsa_automated_quality", { layer: "intermediate" })} />.
        Each column&apos;s right-corner chip resolves to the original Spotify-published XLSX.
      </div>
      <div className="grid gap-4 lg:grid-cols-4">
        {sorted.map((row) => (
          <ProductColumn
            key={row.product_line}
            row={row}
            citation={citeSpotifyXlsx(row.product_line as "main" | "artists" | "authors" | "creators")}
          />
        ))}
      </div>
    </div>
  );
}
