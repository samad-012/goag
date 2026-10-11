"use client";

import { useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";

export function WorkspaceControls() {
  const [refreshing, setRefreshing] = useState(false);

  const refreshWorkspace = () => {
    setRefreshing(true);
    window.dispatchEvent(new Event(WORKSPACE_REFRESH_EVENT));
    window.setTimeout(() => setRefreshing(false), 800);
  };

  return (
    <>
      <div className="hidden w-full max-w-md lg:block">
        <label className="relative block">
          <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-describedby="global-search-status"
            aria-label="Global search"
            className="h-9 rounded-xl bg-card pl-9"
            disabled
            placeholder="Search coming soon"
            title="Global search is not available yet"
          />
        </label>
        <span className="sr-only" id="global-search-status">Global search will support drone serials, component serials, and component requests in a later update.</span>
      </div>

      <Button
        aria-label={refreshing ? "Refreshing current workspace" : "Refresh current workspace"}
        className="hidden sm:inline-flex"
        disabled={refreshing}
        onClick={refreshWorkspace}
        size="icon"
        title="Refresh current workspace"
        type="button"
        variant="ghost"
      >
        <RefreshCw aria-hidden="true" className={refreshing ? "animate-spin" : undefined} />
      </Button>
    </>
  );
}
