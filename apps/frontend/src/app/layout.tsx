import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

// next/font self-hosts the font files at build time (downloaded once,
// baked into the build output) -- no runtime request to Google, so this
// stays consistent with CLAUDE.md's "local-first, no internet dependency
// for normal operation" rule.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Private Data Cloud",
  description: "Self-hosted, local-first private organizational platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`h-full antialiased ${inter.variable}`}>
      <body className="min-h-full flex flex-col bg-[#F5F6FB] font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
