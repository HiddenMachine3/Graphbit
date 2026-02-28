import type { LeaderboardEntryDTO } from "../../lib/types";

type LeaderboardTableProps = {
  entries: LeaderboardEntryDTO[];
  currentUserId?: string | null;
};

export default function LeaderboardTable({
  entries,
  currentUserId,
}: LeaderboardTableProps) {
  return (
    <div className="rounded border border-border-default bg-bg-surface p-4">
      <div className="text-sm font-semibold font-heading text-text-primary">Leaderboard</div>
      <table className="mt-3 w-full text-left text-sm font-body">
        <thead className="text-xs text-text-muted">
          <tr>
            <th className="py-1">Rank</th>
            <th className="py-1">User</th>
            <th className="py-1">Score</th>
          </tr>
        </thead>
        <tbody className="text-text-secondary">
          {entries.map((entry) => (
            <tr
              key={entry.user_id}
              className={
                currentUserId && entry.user_id === currentUserId
                  ? "bg-bg-hover font-semibold"
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
          <div className="mt-2 text-xs font-body text-text-muted">No leaderboard data.</div>
      )}
    </div>
  );
}
