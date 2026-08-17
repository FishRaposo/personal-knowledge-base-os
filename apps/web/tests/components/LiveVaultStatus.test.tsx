import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import LiveVaultStatus, { eventNameFromPayload } from "@/components/LiveVaultStatus";
import { api } from "@/lib/api";

class MockEventSource {
  static instances: MockEventSource[] = [];
  readonly addEventListener = vi.fn((event: string, listener: EventListener) => this.listeners.set(event, listener));
  readonly close = vi.fn();
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  private readonly listeners = new Map<string, EventListener>();

  constructor(_url: string) {
    MockEventSource.instances.push(this);
  }

  dispatch(event: string, payload: unknown) {
    this.listeners.get(event)?.({ data: JSON.stringify(payload) } as MessageEvent<string>);
  }
}

describe("named SSE payloads", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.spyOn(api, "getWatcher").mockResolvedValue({ data: { vault_id: "default", running: false }, source: "live" });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("maps named backend event records and refuses malformed data", () => {
    expect(eventNameFromPayload({ type: "index_completed" })).toBe("index_completed");
    expect(eventNameFromPayload({ event: "watcher_started" })).toBe("watcher_started");
    expect(eventNameFromPayload({})).toBeNull();
  });

  it("registers named SSE handlers and maps their payloads into live status", async () => {
    render(<LiveVaultStatus />);

    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1));
    const source = MockEventSource.instances[0];
    expect(source.addEventListener).toHaveBeenCalledWith("index_completed", expect.any(Function));
    expect(source.addEventListener).toHaveBeenCalledWith("watcher_started", expect.any(Function));

    act(() => source.dispatch("index_completed", { id: "event-7", type: "index_completed", data: { indexed: 2 } }));

    expect(screen.getByText("index completed")).toBeVisible();
  });
});
