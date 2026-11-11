import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    // jsdom with user-event is slow on a busy machine (a running IntraForge, a build): 5 s timed out walk-through tests.
    testTimeout: 15000,
  },
});
