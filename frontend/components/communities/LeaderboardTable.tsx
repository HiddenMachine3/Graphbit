import type { LeaderboardEntryDTO } from "../../lib/types";

type LeaderboardTableProps = {
  entries: LeaderboardEntryDTO[];
  currentUserId: string;
};

export default function LeaderboardTable({
  entries,
  currentUserId,
}: LeaderboardTableProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <div className="text-sm font-semibold text-slate-800">Leaderboard</div>
      <table className="mt-3 w-full text-left text-sm">
        <thead className="text-xs text-slate-400">
          <tr>
            <th className="py-1">Rank</th>
            <th className="py-1">User</th>
            <th className="py-1">Score</th>
          </tr>
        </thead>
        <tbody className="text-slate-700">
          {entries.map((entry) => (
            <tr
              key={entry.user_id}
              className={
                entry.user_id === currentUserId
                  ? "bg-slate-50 font-semibold"
                  : ""
              }
            >
              <td className="py-1">{entry.rank}</td>
              <td className="py-1">{entry.user_id}</td>
              <td className="py-1">{entry.score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {entries.length === 0 && (
        <div className="mt-2 text-xs text-slate-500">No leaderboard data.</div>
      )}
    </div>
  );
}
