'use client';

import ErrorState from "../components/ErrorState";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="p-6">
      <ErrorState title="Application error" message={error.message} />
      <button
        className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white"
        onClick={reset}
      >
        Try again
      </button>
    </div>
  );
}
