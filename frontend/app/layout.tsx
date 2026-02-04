import "./globals.css";

import type { Metadata } from "next";

import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";

export const metadata: Metadata = {
  title: "RecallGraph",
  description: "Graph-based active recall system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50">
        <div className="grid min-h-screen grid-cols-1 md:grid-cols-[240px_1fr]">
          <div className="hidden md:block">
            <Sidebar />
          </div>
          <div className="flex min-h-screen flex-col">
            <Topbar />
            <main className="flex-1 p-6">
              <div className="md:hidden mb-4 rounded border border-slate-200 bg-white p-3 text-xs text-slate-500">
                Menu available on larger screens.
              </div>
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
