# ADR-0026: Access requests from each app, approved by an administrator, confirmed by a single-use link

Status: accepted; implemented (2026-11-22).

## Problem

The shop owner wants each application (Spare Parts, IntraForge Pay, Pharmacy) to have its own sign-up and its own
member list: a new staff member registers from the application they will work in, an administrator approves them
and chooses their role, and IntraForge confirms the account. Before this ADR anyone who could reach the shop PC could
create an IntraForge account at `/register` (no organization or role, so it opened nothing, but nobody approved it
and no address was checked), and members were only added by an administrator who typed an existing account's email.

The owner also wants to approve IntraForge Pay credit requests (maker/checker) from their phone, with a sign-in that
only they hold.

## Decision

1. **IntraForge stays the one identity.** No application gets its own password store: one account per person, one
   place to disable it, one audit log, the existing rate limits, two-step sign-in and passkeys. "Each app's own login"
   is each application's own branded sign-in and **Request access** page and its own list of requests and members,
   all backed by IntraForge accounts, memberships and roles (ADR-0008, ADR-0018).
2. **An access request** (`organizations.AccessRequest`): who (an account), which organization, which installed
   application (or the organization itself), the role they *ask* for (only that application's roles, e.g.
   `spare-parts-sales`), an optional message, and its state: `pending`, `approved`, `rejected`. At most one pending
   request per person, organization and application.
   - **A new person** fills in the application's Request access page (name, email, phone, their own password, the job
     they want). IntraForge creates the account **inactive** (it cannot sign in) and the request. The answer is the
     same whether or not the email already has an account, so the page cannot be used to find out who works there.
   - **Someone who already has an account** signs in and requests from the same page; no second account is made.
3. **An administrator decides.** Approving needs both `users.manage` (add a member) and `permissions.manage` (give
   a role) in that organization, and goes through the same services as Organization > Members
   (`Membership`, `permissions.services.assign_role`, so the internet-gateway rule for administrative roles still
   applies). **The administrator chooses the role**: the requested one is only a suggestion, so nobody can give
   themselves a role. Rejecting records a reason. Requests are listed in IntraForge (Organization > Members >
   Requests) and inside the application (Spare Parts > Users > Requests) through the internal service API, which acts
   for the signed-in person and checks the same two capabilities for them. Every step is audited
   (`organization.access_request.create|approve|reject`).
4. **Step 3, the confirmation link** (as the owner asked, instead of a 6-digit code): approving a request from a new
   account creates a **single-use link**: 32 random bytes, only its SHA-256 kept, valid for **72 hours**
   (`accounts.AccountLink`). IntraForge e-mails it when an outgoing mail server is configured (`EMAIL_HOST`, off by
   default: the shop works offline); otherwise, and always, the administrator can copy it from the Requests screen
   once. The token travels in the URL **fragment** (`/confirm#t=...`), so it never reaches a server log or a Referer.
   Opening it confirms the email and activates the account. **No temporary password is ever shown**: a person who
   registered chose their own password at step 2; an account made by the system (below) sets its own sign-in on the
   link page, a password or a passkey. A used or expired link does nothing; the administrator can issue a new one,
   which ends the previous one. Created, used and expired links are audited.
5. **Who may register** (`system.FeatureSettings.registration`, changed by the Super Administrator on the Features
   page): `closed` (only administrators add people), `requests` (only through an application's Request access; the
   default) or `open` (anyone, as before). While no organization exists yet, the first account can always be created
   (first run). Installations from before this ADR therefore move from open registration to `requests`: an external
   application's plain "sign up" link stops creating accounts unless the Super Administrator sets `open`.
6. **The owner's phone approver.** Maker/checker refuses self-approval by account. For a shop with one owner, the
   Control Center (Settings > Owner > *Create the phone approver*, i.e. `manage.py approver_account create`) makes a
   separate account, **inactive and with no password**, gives it a chosen approving role (e.g. Pay Supervisor) and
   prints a link. The owner opens it on the shop PC and creates a **passkey on their phone** (the browser shows a QR
   code; the phone's password manager, e.g. Google Password Manager, keeps the passkey and confirms with fingerprint
   or face). The account is then **passkey-only**: it has no password at all, so it can only sign in with that phone.
   Only someone at the PC can create it, like the Super Administrator (ADR-0025).

## Consequences

- One person can be maker (their own account) and checker (their phone approver). That is **two devices, not two
  people**; the audit log shows both accounts honestly. When the shop has a second trusted person, give them the
  approving role instead, and remove the phone approver's role.
- A lost link costs nothing: it is single-use, expires, and the administrator issues a new one.
- E-mail is optional and off by default; without it the administrator hands the link over in person.
- Existing installations stop open registration (see 5); recorded in the User Guide.

## Not done

- Self-service password reset by e-mail (an administrator still uses Reset password).
- Requests for roles outside one application (administrators give those on the Members page).
