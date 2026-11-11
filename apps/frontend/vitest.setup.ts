import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Testing Library only auto-registers this when `globals` is enabled, which
// this project deliberately leaves off — without it, each render stays in the
// document and later queries match elements from earlier tests.
afterEach(cleanup);
