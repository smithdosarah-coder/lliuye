import type { Metadata } from "next";
import {
  Noto_Serif_SC,
  Noto_Sans_SC,
  JetBrains_Mono,
  Fraunces,
  Newsreader,
  Funnel_Display,
  Instrument_Sans,
  Instrument_Serif,
} from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { AppShell } from "@/components/shell/AppShell";

const serif = Noto_Serif_SC({
  variable: "--font-serif",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const sans = Noto_Sans_SC({
  variable: "--font-sans",
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const mono = JetBrains_Mono({
  variable: "--font-mono",
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  display: "swap",
});

// Platform shell v2 —— Funnel Display / Instrument Sans / Instrument Serif
// 迁移自 Stage 2 CDN <link>，改为 next/font 自托管 (Stage 4 Task A)
const funnelDisplay = Funnel_Display({
  variable: "--font-funnel-display",
  weight: ["300", "400", "500", "600", "700", "800"],
  subsets: ["latin"],
  display: "swap",
});

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
});

// Editorial display 字体（legacy /credit 等 6 Agent 页使用 · Stage 5 清理）
const editorialDisplay = Fraunces({
  variable: "--font-editorial-display",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const editorialBody = Newsreader({
  variable: "--font-editorial-body",
  weight: ["300", "400", "500", "600"],
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "乾策 · 信贷 AI 矩阵",
  description: "众安信科 · 6 大智能体覆盖信贷全流程",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${serif.variable} ${sans.variable} ${mono.variable} ${funnelDisplay.variable} ${instrumentSans.variable} ${instrumentSerif.variable} ${editorialDisplay.variable} ${editorialBody.variable} ${GeistSans.variable} ${GeistMono.variable} h-full`}
    >
      <body className="min-h-full">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
