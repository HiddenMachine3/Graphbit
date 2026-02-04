import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/session", label: "Session" },
  { href: "/graph", label: "Graph" },
  { href: "/communities", label: "Communities" },
];

export default function Sidebar() {
  return (
    <aside className="flex h-full w-full flex-col gap-4 border-r border-slate-200 bg-white p-4">
      <div className="text-lg font-semibold">RecallGraph</div>
      <nav className="flex flex-col gap-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
