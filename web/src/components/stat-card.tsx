import { Card } from "@/components/ui/card";

export function StatCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "accent";
}) {
  return (
    <Card className="border-border/60 bg-card p-5 transition hover:border-border">
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
        <span
          className={`font-mono text-3xl font-semibold tabular-nums ${
            tone === "accent" ? "text-[#1DB954]" : "text-foreground"
          }`}
        >
          {value}
        </span>
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
    </Card>
  );
}
