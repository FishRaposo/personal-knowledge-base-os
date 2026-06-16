import { test, expect } from "@playwright/test";

// These run over the demo-mode UI with NO backend required: the app falls back
// to bundled fixtures when the API is unreachable.

test("home page loads with hero and nav", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Knowledge Base OS/i);
  await expect(
    page.getByRole("heading", { name: /second brain/i })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Search/i }).first()).toBeVisible();
});

test("search returns demo results and a demo badge", async ({ page }) => {
  await page.goto("/search");
  await page.getByLabel("Search query").fill("wikilinks");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("results-list")).toBeVisible();
  await expect(page.getByTestId("search-result").first()).toBeVisible();
  await expect(page.getByTestId("demo-badge").first()).toBeVisible();
});

test("opening a search result shows the note with backlinks", async ({ page }) => {
  await page.goto("/notes/backlinks_graph");
  // The note title appears in the page header; scope to the header heading.
  await expect(
    page.getByRole("banner").getByText("Knowledge Base OS")
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Backlinks Graph" }).first()
  ).toBeVisible();
  await expect(page.getByTestId("backlinks")).toBeVisible();
  await expect(page.getByTestId("note-markdown")).toBeVisible();
});

test("tags page lists tags and notes for a tag", async ({ page }) => {
  await page.goto("/tags");
  await expect(page.getByTestId("tag-cloud")).toBeVisible();
  await page.getByTestId("tag-cloud-item").first().click();
  await expect(page.getByTestId("tag-notes")).toBeVisible();
});

test("chat returns a cited answer", async ({ page }) => {
  await page.goto("/chat");
  await page.getByLabel("Chat message").fill("How do wikilinks work?");
  await page.getByRole("button", { name: /Send/i }).click();
  await expect(page.getByTestId("citations")).toBeVisible({ timeout: 15_000 });
});

test("graph page renders the canvas", async ({ page }) => {
  await page.goto("/graph");
  await expect(page.getByTestId("graph-canvas")).toBeVisible();
});
