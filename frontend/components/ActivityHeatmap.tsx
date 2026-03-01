"use client";

import { useMemo } from "react";

interface ActivityData {
  date: string;
  count: number;
}

interface ActivityHeatmapProps {
  data?: ActivityData[];
  className?: string;
  nodesCount?: number | null;
  edgesCount?: number | null;
  streak?: number | null;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function ActivityHeatmap({
  data = [],
  className = "",
  streak = null,
  collapsed = false,
  onToggleCollapse,
}: ActivityHeatmapProps) {
  const heatmapData = useMemo(() => {
    const today = new Date();
    const startDate = new Date(today);
    startDate.setMonth(startDate.getMonth() - 3);

    const days: Array<{ date: string; count: number; day: number; week: number }> = [];
    const currentDate = new Date(startDate);

    while (currentDate <= today) {
      const dateStr = currentDate.toISOString().split("T")[0];
      const dayData = data.find((d) => d.date === dateStr);
      const count = dayData?.count ?? 0;

      days.push({
        date: dateStr,
        count,
        day: currentDate.getDay(),
        week: Math.floor(
          (currentDate.getTime() - startDate.getTime()) /
            (7 * 24 * 60 * 60 * 1000)
        ),
      });

      currentDate.setDate(currentDate.getDate() + 1);
    }

    return days;
  }, [data]);

  const getIntensityClass = (count: number) => {
    if (count === 0) return "bg-bg-elevated";
    if (count <= 1) return "bg-accent-dim";
    if (count <= 2) return "bg-accent/60";
    if (count <= 3) return "bg-accent/80";
    return "bg-accent";
  };

  const totalWeeks = useMemo(() => {
    if (heatmapData.length === 0) {
      return 1;
    }
    const maxWeek = Math.max(...heatmapData.map((d) => d.week));
    return maxWeek + 1;
  }, [heatmapData]);

  const weeks = Array.from({ length: totalWeeks }, (_, i) => i);
  const daysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const currentStreak = useMemo(() => {
    if (streak !== null && streak !== undefined) {
      return streak;
    }
    let computed = 0;
    for (let i = heatmapData.length - 1; i >= 0; i--) {
      if (heatmapData[i].count > 0) {
        computed++;
      } else {
        break;
      }
    }
    return computed;
  }, [heatmapData, streak]);

  return (
    <div className={`rounded-lg border border-border-default bg-bg-surface p-3 ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <h3 className="flex items-center space-x-2 text-sm font-medium font-heading text-text-primary">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <span>Recall Activity</span>
        </h3>
        <div className="flex items-center gap-3 text-xs font-body text-text-muted">
          <span className="text-text-secondary">Last 3 Months</span>
          {onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label={collapsed ? "Expand recall activity panel" : "Collapse recall activity panel"}
              title={collapsed ? "Expand recall activity panel" : "Collapse recall activity panel"}
              className="text-sm font-semibold text-text-secondary hover:text-text-primary"
            >
              {collapsed ? "^" : "v"}
            </button>
          )}
        </div>
      </div>

      {!collapsed && (
        <>
          <div className="mb-4 grid grid-cols-[28px_1fr] gap-2">
            <div className="flex flex-col space-y-1 text-xs font-body text-text-muted">
              {daysOfWeek.map((day) => (
                <div key={day} className="flex h-3 items-center leading-3">
                  {day}
                </div>
              ))}
            </div>

            <div className="flex space-x-1">
              {weeks.map((weekIndex) => (
                <div key={weekIndex} className="flex flex-col space-y-1">
                  {Array.from({ length: 7 }, (_, dayIndex) => {
                    const dayData = heatmapData.find(
                      (d) => d.week === weekIndex && d.day === dayIndex
                    );
                    return (
                      <div
                        key={`${weekIndex}-${dayIndex}`}
                        className={`h-3 w-3 rounded-sm transition-colors hover:ring-1 hover:ring-border-accent ${
                          dayData ? getIntensityClass(dayData.count) : "bg-bg-elevated"
                        }`}
                        title={
                          dayData ? `${dayData.date}: ${dayData.count} sessions` : ""
                        }
                      ></div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          <div className="text-sm font-medium font-body text-text-primary">
            Current streak: <span className="text-accent">{currentStreak}</span> days
          </div>
        </>
      )}
    </div>
  );
}