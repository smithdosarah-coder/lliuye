import type { Metadata } from "next";
import {
  Noto_Serif_SC,
  Noto_Sans_SC,
  JetBrains_Mono,
  Fraunces,
  Newsreader,
} from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

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

// Editorial display 字体（A 方向 · 朱印宣纸）
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
      className={`${serif.variable} ${sans.variable} ${mono.variable} ${editorialDisplay.variable} ${editorialBody.variable} ${GeistSans.variable} ${GeistMono.variable} h-full`}
    >
      <body className="min-h-full">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
