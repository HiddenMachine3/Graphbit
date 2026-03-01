"use client";

import { usePathname } from "next/navigation";

import Topbar from "./Topbar";
import FABCluster from "./FABCluster";
import { useAppStore } from "../lib/store";

type AppChromeProps = {
  children: React.ReactNode;
};

export default function AppChrome({ children }: AppChromeProps) {
  const pathname = usePathname();
  const isExtensionQuizRoute = pathname === "/extension-quiz";
  const isQuestioningMode = useAppStore((state) => state.isQuestioningMode);

  if (isExtensionQuizRoute) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen flex-col">
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isQuestioningMode
            ? "max-h-0 -translate-y-full opacity-0"
            : "max-h-40 translate-y-0 opacity-100"
        }`}
      >
        <Topbar />
      </div>
      <main className="flex-1 overflow-auto">{children}</main>
      <FABCluster />
    </div>
  );
}
