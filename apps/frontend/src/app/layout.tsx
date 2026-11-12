import type { Metadata } from "next";
import { Inter, Oswald } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/lib/query";
import { TourRequestCapture } from "@/components/TourRequestCapture";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";
import "./globals.css";

// next/font self-hosts the font files at build time (downloaded once,
// baked into the build output) -- no runtime request to Google, so this
// stays consistent with CLAUDE.md's "local-first, no internet dependency
// for normal operation" rule.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
// The Movie Shop's cinematic titles (covers, headings); self-hosted the same way.
const oswald = Oswald({ subsets: ["latin"], weight: ["500", "600"], variable: "--font-display" });

export const metadata: Metadata = {
  title: {
    default: "IntraForge",
    template: "%s · IntraForge",
  },
  description:
    "IntraForge — self-hosted, local-first business infrastructure. Build. Store. Connect. Privately.",
  manifest: "/brand/site.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/brand/icon-32.png", type: "image/png", sizes: "32x32" },
      { url: "/brand/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: [{ url: "/brand/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport = {
  themeColor: "#172554",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`h-full antialiased ${inter.variable} ${oswald.variable}`} suppressHydrationWarning>
      <head>
        {/* Sets data-theme before the first paint (dark mode without a white flash). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-surface-canvas text-text-primary font-sans">
        <QueryProvider>
          <TourRequestCapture />
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
