import type { Metadata } from "next";
import { Inter } from "next/font/google";
import ErrorBoundary from "@/components/ErrorBoundary";
import NavBar from "@/components/NavBar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Knowledge Base OS",
  description:
    "A local-first personal knowledge base: search, browse, visualize, and chat with your markdown notes — backed by wikilinks, a backlinks graph, and grounded citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-ink-50 text-ink-900 antialiased">
        <NavBar />
        <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
        <footer className="border-t border-ink-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-ink-400 sm:px-6">
            Knowledge Base OS — local-first, offline by default. Built with Next.js.
          </div>
        </footer>
      </body>
    </html>
  );
}
