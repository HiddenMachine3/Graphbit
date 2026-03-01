import "./globals.css";

import type { Metadata } from "next";
import { Syne, DM_Sans } from "next/font/google";

import AppChrome from "../components/AppChrome";

const syne = Syne({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-heading",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Graphbit",
  description: "Graph-based active recall system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${dmSans.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-transparent overflow-hidden font-body">
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
