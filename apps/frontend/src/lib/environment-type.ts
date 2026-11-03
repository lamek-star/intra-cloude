export const ENVIRONMENT_TYPES = ["development", "staging", "production", "custom"] as const;

/** An example name for the chosen type. The forms used to suggest "Production" whatever the type,
 * while the type defaulted to development -- typing the suggested name gave a "Production" without
 * production's extra protection. */
export function exampleEnvironmentName(environmentType: string): string {
  switch (environmentType) {
    case "production":
      return "Production";
    case "staging":
      return "Staging";
    case "custom":
      return "Testing";
    default:
      return "Development";
  }
}

/** True when the name reads as production but the type is not production, so the environment would
 * not get the production permission gate or the second delete confirmation. */
export function namesProductionWithoutType(name: string, environmentType: string): boolean {
  return environmentType !== "production" && /\bprod(uction)?\b/i.test(name.trim());
}
