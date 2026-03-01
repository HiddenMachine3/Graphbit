"use client";

import { usePathname } from "next/navigation";

import Topbar from "./Topbar";
import FABCluster from "./FABCluster";

type AppChromeProps = {
  children: React.ReactNode;
};

export default function AppChrome({ children }: AppChromeProps) {
  const pathname = usePathname();
  const isExtensionQuizRoute = pathname === "/extension-quiz";

  if (isExtensionQuizRoute) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen flex-col">
      <Topbar />
      <main className="flex-1 overflow-auto">{children}</main>
      <FABCluster />
    </div>
  );
}
