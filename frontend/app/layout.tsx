import "./globals.css";

import type { Metadata } from "next";
import { Syne, DM_Sans } from "next/font/google";

import Topbar from "../components/Topbar";
import FABCluster from "../components/FABCluster";

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
        <div className="flex h-screen flex-col">
          <Topbar />
          <main className="flex-1 overflow-auto">{children}</main>
          <FABCluster />
        </div>
      </body>
    </html>
  );
}
