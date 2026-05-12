import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Cadence — DSA Cross-Product Analytics for Spotify",
  description:
    "Unified analytics engineering layer for Spotify's four DSA Transparency Reports. Real data, 50+ dbt models, 219 tests, methodology rendered from source.",
};

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/lakehouse", label: "Lakehouse" },
  { href: "/detection-lab", label: "Detection Lab" },
  { href: "/methodology", label: "Methodology" },
];

function TopNav() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/40 bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full bg-[#1DB954]" />
          <span className="font-semibold tracking-tight">Cadence</span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            · Spotify DSA analytics engineering
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://cadence-ashen.vercel.app/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-md px-3 py-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
          >
            API ↗
          </a>
          <a
            href="https://github.com/AliHasan-786/Cadence"
            target="_blank"
            rel="noreferrer"
            className="rounded-md px-3 py-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
          >
            GitHub ↗
          </a>
        </nav>
      </div>
    </header>
  );
}

function HonestScopeFooter() {
  return (
    <footer className="mt-auto border-t border-border/40 bg-muted/30">
      <div className="mx-auto max-w-7xl px-6 py-8 text-xs text-muted-foreground">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <h4 className="mb-2 font-medium text-foreground">Real data</h4>
            <p>
              Spotify&apos;s four DSA Transparency Reports (Main, Artists, Authors,
              Creators) published 27 February 2026. Sourced verbatim from{" "}
              <a
                href="https://www.spotify.com/us/safetyandprivacy/transparency"
                className="underline-offset-2 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                spotify.com/safetyandprivacy/transparency
              </a>
              .
            </p>
          </div>
          <div>
            <h4 className="mb-2 font-medium text-foreground">Synthetic data</h4>
            <p>
              Stream-event data in the Detection Lab is synthetic, clearly labelled{" "}
              <code className="rounded bg-background px-1 py-0.5 font-mono text-[0.7rem]">
                _synth
              </code>{" "}
              in BigQuery. Fraud scenarios are pre-embedded with deterministic seeds.
            </p>
          </div>
          <div>
            <h4 className="mb-2 font-medium text-foreground">Provenance</h4>
            <p>
              Built by Ali Hasan as a Spotify Analytics Engineer (T&amp;S) portfolio piece.
              Cadence is not affiliated with Spotify.{" "}
              <a
                href="https://github.com/AliHasan-786/Cadence"
                className="underline-offset-2 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                github.com/AliHasan-786/Cadence
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <TopNav />
        <main className="flex-1">{children}</main>
        <HonestScopeFooter />
      </body>
    </html>
  );
}
