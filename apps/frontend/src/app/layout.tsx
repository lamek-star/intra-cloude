import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Private Data Cloud",
  description: "Self-hosted, local-first private organizational platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-950">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
