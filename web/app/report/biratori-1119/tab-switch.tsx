"use client";

import { useEffect, useState } from "react";

export type ReportTab = "farmer" | "investor";

const TAB_COOKIE = "farm-report-tab";
const THIRTY_DAYS_SECONDS = 60 * 60 * 24 * 30;

function isTab(value: string | undefined): value is ReportTab {
  return value === "farmer" || value === "investor";
}

/**
 * Audience switch (client-only behaviour over server-rendered panes).
 * Persists the choice in the farm-report-tab cookie, mirrors it into the
 * shareable URL (?tab=…) without navigating, and swaps pane visibility.
 */
export function TabSwitch({
  initial,
  farmerLabel,
  investorLabel,
  farmerPane,
  investorPane,
}: {
  initial: ReportTab;
  farmerLabel: string;
  investorLabel: string;
  farmerPane: React.ReactNode;
  investorPane: React.ReactNode;
}) {
  const [tab, setTab] = useState<ReportTab>(initial);

  useEffect(() => {
    if (!isTab(tab)) return;
    document.cookie = `${TAB_COOKIE}=${tab}; path=/; max-age=${THIRTY_DAYS_SECONDS}; samesite=lax`;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    window.history.replaceState(null, "", url.toString());
  }, [tab]);

  return (
    <div className="tabs" role="tablist" aria-label="audience">
      <button
        type="button"
        role="tab"
        aria-selected={tab === "farmer"}
        className={tab === "farmer" ? "tab active" : "tab"}
        onClick={() => setTab("farmer")}
      >
        {farmerLabel}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={tab === "investor"}
        className={tab === "investor" ? "tab active" : "tab"}
        onClick={() => setTab("investor")}
      >
        {investorLabel}
      </button>
      <div hidden={tab !== "farmer"} className="pane" role="tabpanel">
        {farmerPane}
      </div>
      <div hidden={tab !== "investor"} className="pane" role="tabpanel">
        {investorPane}
      </div>
    </div>
  );
}
