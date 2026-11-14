# Chapter 3 — The frontend — Signing in — `src/lib/auth-context.tsx`

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

`useAuth()` exposes `user`, `login` (which may answer `mfaRequired`), `verifyMfa`, `signInWithPasskey`, `register`,
`logout`, `refresh`. Passkeys use WebAuthn through `src/lib/passkeys.ts`. After a password reset the backend refuses
everything except changing the password; `PasswordForm` handles that screen.
