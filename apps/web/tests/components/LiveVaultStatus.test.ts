import { describe, expect, it } from "vitest";
import { eventNameFromPayload } from "@/components/LiveVaultStatus";

describe("named SSE payloads", () => {
  it("maps named backend event records and refuses malformed data", () => {
    expect(eventNameFromPayload({ type: "index_completed" })).toBe("index_completed");
    expect(eventNameFromPayload({ event: "watcher_started" })).toBe("watcher_started");
    expect(eventNameFromPayload({})).toBeNull();
  });
});
