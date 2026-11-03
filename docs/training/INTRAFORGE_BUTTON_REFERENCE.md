# IntraForge -- button and action reference (Level 1)

Every button / action found in the code, page by page, with what it does. Small controls (Save, Cancel, Close, paging, sorting arrows) are included.

## Page: Landing page (`/`)

### Button: Get Started

- **Application:** IntraForge
- **Location:** Landing page
- **Purpose:** Start using IntraForge.
- **What happens:** Navigates to registration / sign-in.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/register`
- **Source evidence:** `app/page.tsx:70`

### Button: View Demo

- **Application:** IntraForge
- **Location:** Landing page
- **Purpose:** See the demonstration.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/page.tsx:93`

### Button: Go home

- **Application:** IntraForge
- **Location:** Landing page
- **Purpose:** Return to the start page.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/`
- **Source evidence:** `app/not-found.tsx:15`

## Page: Installed business app (definition) (`/app-instances/[instanceId]`)

### Button: Edit

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:202`

### Button: Starting… / Provision runtime

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Create the database tables of an installed business app.
- **What happens:** Builds its tables through the validated provisioning service.
- **Data affected:** Tenant database
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open models
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:235`

### Button: Retrying… / Retry

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Try the failed step again.
- **What happens:** Repeats it.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:248`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Installed business app (definition) -> dialog "Edit app"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:413`

### Button: Save

- **Application:** IntraForge
- **Location:** Installed business app (definition) -> dialog "Edit app"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:416`

### Button: Add model

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Add a model (table) to the template.
- **What happens:** Creates it (app_template.manage).
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** Add fields
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:467`

### Button: Add relationship

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Link two models.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:585`

### Button: Comparing… / Preview

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Preview an upgrade to a newer template version.
- **What happens:** Shows what would be added and any conflicts with your own changes (three-way comparison).
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Apply upgrade
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:717`

### Button: Applying… / Apply upgrade

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Apply the upgrade.
- **What happens:** Adds what is safe; never silently overwrites your own changes.
- **Data affected:** Installed app definition
- **Confirmation:** Depends
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:726`

### Button: Upgrade history ( … )

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Show the installed app's upgrade history.
- **What happens:** Expands the list.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:770`

### Button: Share

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/ShareSection.tsx:133`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Installed business app (definition)
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:166`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Installed business app (definition) -> dialog "Share"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:316`

### Button: Share

- **Application:** IntraForge
- **Location:** Installed business app (definition) -> dialog "Share"
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:319`

## Page: Model records (`/app-models/[modelId]`)

### Button: Add record

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Save the new record.
- **What happens:** Saves it (database.write).
- **Data affected:** Record
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:289`

### Button: Edit

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:520`

### Button: Delete

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:529`

### Button: Previous

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:548`

### Button: Next

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:560`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:775`

### Button: Save / Add record

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Save the new record.
- **What happens:** Saves it (database.write).
- **Data affected:** Record
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:778`

### Button: Add field

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Add a field to a model.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1146`

### Button: Add workflow

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Add an approval / status workflow.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add states and transitions
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1227`

### Button: Add state

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Add a workflow state.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1278`

### Button: Add transition

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Add a workflow step.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1402`

### Button: Add unique constraint

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Make a combination of fields unique.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1501`

### Button: Revoke unit grant

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Remove a unit-scoped grant.
- **What happens:** Access through the unit ends.
- **Data affected:** Grant
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/AppModelAccess.tsx:98`

### Button: Saving… / Grant unit access

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Give an organizational unit access to the installed app.
- **What happens:** Creates a unit-scoped grant.
- **Data affected:** Grant
- **Confirmation:** No
- **Can it be undone:** Revoke unit grant
- **Next step:** --
- **Source evidence:** `components/AppModelAccess.tsx:115`

### Button: Share

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/ShareSection.tsx:133`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Model records
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:166`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Model records -> dialog "Share"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:316`

### Button: Share

- **Application:** IntraForge
- **Location:** Model records -> dialog "Share"
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:319`

## Page: Record (`/app-models/[modelId]/records/[recordId]`)

### Button: Save

- **Application:** IntraForge
- **Location:** Record
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:300`

### Button: Attach file

- **Application:** IntraForge
- **Location:** Record
- **Purpose:** Attach a file to the record.
- **What happens:** Opens the attach dialog.
- **Data affected:** Attachment
- **Confirmation:** No
- **Can it be undone:** Detach
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:367`

### Button: Detach

- **Application:** IntraForge
- **Location:** Record
- **Purpose:** Remove an attachment from the record.
- **What happens:** The link is removed.
- **Data affected:** Attachment
- **Confirmation:** Depends
- **Can it be undone:** Attach again
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:403`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Record -> dialog "Attach a file"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:573`

### Button: Attach

- **Application:** IntraForge
- **Location:** Record -> dialog "Attach a file"
- **Purpose:** Attach the chosen file to the record.
- **What happens:** Links the file (stored in a bucket) to the record.
- **Data affected:** Attachment
- **Confirmation:** No
- **Can it be undone:** Detach
- **Next step:** --
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:576`

## Page: Template builder (`/app-templates/[templateId]`)

### Button: Edit details

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Edit the application's name / description.
- **What happens:** Opens the dialog.
- **Data affected:** Application
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:379`

### Button: Publish version

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Publish the template as a new immutable version.
- **What happens:** The version can be installed; it never changes afterwards (app_template.publish).
- **Data affected:** Template version
- **Confirmation:** No
- **Can it be undone:** No (publish a newer one)
- **Next step:** Install
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:382`

### Button: Rename

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Rename the item.
- **What happens:** Opens the rename dialog.
- **Data affected:** Name
- **Confirmation:** No
- **Can it be undone:** Rename again
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:421`

### Button: Delete

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:428`

### Button: Edit

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:472`

### Button: Add model

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Add a model (table) to the template.
- **What happens:** Creates it (app_template.manage).
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** Add fields
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:836`

### Button: Add field

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Add a field to a model.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:918`

### Button: Add unique constraint

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Make a combination of fields unique.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1020`

### Button: Add workflow

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Add an approval / status workflow.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add states and transitions
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1095`

### Button: Add state

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Add a workflow state.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1148`

### Button: Add transition

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Add a workflow step.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1258`

### Button: Add relationship

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Link two models.
- **What happens:** Creates it.
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1369`

### Button: ▲

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Move up / sort ascending.
- **What happens:** Changes the order.
- **Data affected:** Order only
- **Confirmation:** No
- **Can it be undone:** Press ▼
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1391`

### Button: ▼

- **Application:** IntraForge
- **Location:** Template builder
- **Purpose:** Move down / sort descending.
- **What happens:** Changes the order.
- **Data affected:** Order only
- **Confirmation:** No
- **Can it be undone:** Press ▲
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1400`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Rename"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1514`

### Button: Save

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Rename"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1517`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Edit field"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1579`

### Button: Save

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Edit field"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1582`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Edit template details"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1657`

### Button: Save

- **Application:** IntraForge
- **Location:** Template builder -> dialog "Edit template details"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1660`

## Page: Application (API client) (`/applications/[applicationId]`)

### Button: New environment

- **Application:** IntraForge
- **Location:** Application (API client)
- **Purpose:** Create an environment (Development / Staging / Production).
- **What happens:** Opens the dialog (environment.manage; production also environment.production.manage).
- **Data affected:** Environment
- **Confirmation:** No
- **Can it be undone:** Delete environment
- **Next step:** Add variables
- **Opens a dialog** first
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:254`

### Button: New credential

- **Application:** IntraForge
- **Location:** Application (API client)
- **Purpose:** Issue a credential (token) for the application.
- **What happens:** Creates a token shown ONCE (application.credentials.manage).
- **Data affected:** Credential
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** Copy the token now
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:293`

### Button: Rotate

- **Application:** IntraForge
- **Location:** Application (API client)
- **Purpose:** Replace a credential / secret with a new one.
- **What happens:** The old value stops working; the new one is shown once.
- **Data affected:** Credential / secret
- **Confirmation:** Usually yes
- **Can it be undone:** --
- **Next step:** Update the program using it
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:335`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Application (API client)
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:342`

### Button: Grant permission

- **Application:** IntraForge
- **Location:** Application (API client)
- **Purpose:** Give an application access to a resource.
- **What happens:** Opens the grant dialog: resource type / id, permission code (permissions.manage).
- **Data affected:** Resource grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:382`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Application (API client) -> dialog "Grant permission"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:529`

### Button: Grant

- **Application:** IntraForge
- **Location:** Application (API client) -> dialog "Grant permission"
- **Purpose:** Grant the permission to the application.
- **What happens:** Creates a resource grant (permissions.manage).
- **Data affected:** Grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:532`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Application (API client) -> dialog "New environment"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:604`

### Button: Create

- **Application:** IntraForge
- **Location:** Application (API client) -> dialog "New environment"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:607`

## Page: Apps (`/apps`)

### Button: Open

- **Application:** IntraForge
- **Location:** Apps
- **Purpose:** Open the item.
- **What happens:** Navigates to it.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/apps/_client.tsx:139`

### Button: Settings

- **Application:** IntraForge
- **Location:** Apps
- **Purpose:** Open the application's settings.
- **What happens:** Navigates to Settings.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/service-apps/:id/settings`
- **Source evidence:** `app/(app)/apps/_client.tsx:145`

### Button: Install

- **Application:** IntraForge
- **Location:** Apps
- **Purpose:** Install the application.
- **What happens:** Installs it into the chosen organization / project.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/apps/_client.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Apps -> dialog "Install …"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/apps/_client.tsx:277`

### Button: Install

- **Application:** IntraForge
- **Location:** Apps -> dialog "Install …"
- **Purpose:** Install the application.
- **What happens:** Installs it into the chosen organization / project.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/apps/_client.tsx:280`

## Page: Built-in Spare Parts business app: overview (`/apps/[instanceId]`)

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in Spare Parts business app: overview
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in Spare Parts business app: overview
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

## Page: Built-in app: Customers (`/apps/[instanceId]/customers`)

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Customers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Stock (`/apps/[instanceId]/inventory`)

### Button: Receive stock

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Built-in business app: receive goods.
- **What happens:** Opens Receive stock (inventory.receive).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/apps/:id/receive`
- **Source evidence:** `components/business/Inventory.tsx:71`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Stock
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Part numbers (`/apps/[instanceId]/part-numbers`)

### Button: Add part number

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Built-in business app: add a part number.
- **What happens:** Opens the dialog.
- **Data affected:** Part number
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/business/PartNumbers.tsx:89`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/PartNumbers.tsx:112`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers -> dialog "Add part number"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/PartNumbers.tsx:255`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers -> dialog "Add part number"
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/PartNumbers.tsx:258`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Change

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Change the selection.
- **What happens:** Lets you pick again.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/ProductPicker.tsx:94`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Part numbers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Products (`/apps/[instanceId]/products`)

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Products
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Product (`/apps/[instanceId]/products/[partId]`)

### Button: Add part number

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Built-in business app: add a part number.
- **What happens:** Opens the dialog.
- **Data affected:** Part number
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/business/ProductDetail.tsx:147`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Receive stock

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Built-in business app: receive goods.
- **What happens:** Opens Receive stock (inventory.receive).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/apps/:id/receive`
- **Source evidence:** `components/business/Inventory.tsx:71`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Product -> dialog "Add part number"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/PartNumbers.tsx:255`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Product -> dialog "Add part number"
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/PartNumbers.tsx:258`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

### Button: Change

- **Application:** IntraForge
- **Location:** Built-in app: Product
- **Purpose:** Change the selection.
- **What happens:** Lets you pick again.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/ProductPicker.tsx:94`

## Page: Built-in app: Receive stock (`/apps/[instanceId]/receive`)

### Button: Receive more

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Built-in business app: receive another delivery.
- **What happens:** Resets the form.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/ReceiveStock.tsx:129`

### Button: View stock

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Built-in business app: open stock.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/apps/:id/inventory`
- **Source evidence:** `components/business/ReceiveStock.tsx:130`

### Button: Receiving… / Confirm receive

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Built-in business app: save the stock receipt.
- **What happens:** Stock goes up (inventory.receive).
- **Data affected:** Stock
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** View stock
- **Source evidence:** `components/business/ReceiveStock.tsx:232`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Change

- **Application:** IntraForge
- **Location:** Built-in app: Receive stock
- **Purpose:** Change the selection.
- **What happens:** Lets you pick again.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/ProductPicker.tsx:94`

## Page: Built-in app: Sales (`/apps/[instanceId]/sales`)

### Button: New sale

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Built-in business app: record a sale.
- **What happens:** Opens New sale (inventory.sell).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/apps/:id/sales/new`
- **Source evidence:** `components/business/Sales.tsx:47`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Sales
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Sale (`/apps/[instanceId]/sales/[orderId]`)

### Button: Print invoice

- **Application:** IntraForge
- **Location:** Built-in app: Sale
- **Purpose:** Print the invoice.
- **What happens:** Opens the browser's print dialog.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/SalesDocument.tsx:89`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Sale
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Sale
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

## Page: Built-in app: New sale (`/apps/[instanceId]/sales/new`)

### Button: Open sales document

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Built-in business app: open the sale just recorded.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Print invoice
- **Goes to:** `/apps/:id/sales/:id`
- **Source evidence:** `components/business/SellStock.tsx:167`

### Button: New sale

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Built-in business app: record a sale.
- **What happens:** Opens New sale (inventory.sell).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/SellStock.tsx:170`

### Button: Add another item

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Add another line.
- **What happens:** Adds a line.
- **Data affected:** Draft
- **Confirmation:** No
- **Can it be undone:** Remove item
- **Next step:** --
- **Source evidence:** `components/business/SellStock.tsx:250`

### Button: Recording sale… / Confirm sale

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Built-in business app: save the sale.
- **What happens:** Order, lines, stock out and invoice are recorded (inventory.sell).
- **Data affected:** Sale, stock, invoice
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open sales document
- **Source evidence:** `components/business/SellStock.tsx:267`

### Button: Remove item

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Remove a line.
- **What happens:** Removes it.
- **Data affected:** Draft
- **Confirmation:** No
- **Can it be undone:** Add another item
- **Next step:** --
- **Source evidence:** `components/business/SellStock.tsx:320`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Change

- **Application:** IntraForge
- **Location:** Built-in app: New sale
- **Purpose:** Change the selection.
- **What happens:** Lets you pick again.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/ProductPicker.tsx:94`

## Page: Built-in app: Suppliers (`/apps/[instanceId]/suppliers`)

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Suppliers
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Built-in app: Warehouses (`/apps/[instanceId]/warehouses`)

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/BusinessApp.tsx:115`

### Button: Search

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `components/business/BusinessApp.tsx:152`

### Button: Previous

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:59`

### Button: Next

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:62`

### Button: Add

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:174`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:258`

### Button: Adding… / Add

- **Application:** IntraForge
- **Location:** Built-in app: Warehouses
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `components/business/RecordSection.tsx:261`

## Page: Bucket (files) (`/buckets/[bucketId]`)

### Button: Upload files

- **Application:** IntraForge
- **Location:** Bucket (files)
- **Purpose:** Upload files to the bucket.
- **What happens:** Files go to object storage (storage.write).
- **Data affected:** Files
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/buckets/[bucketId]/_client.tsx:148`

### Button: Delete

- **Application:** IntraForge
- **Location:** Bucket (files)
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/buckets/[bucketId]/_client.tsx:216`

### Button: Share

- **Application:** IntraForge
- **Location:** Bucket (files)
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/ShareSection.tsx:133`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Bucket (files)
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:166`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Bucket (files) -> dialog "Share"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:316`

### Button: Share

- **Application:** IntraForge
- **Location:** Bucket (files) -> dialog "Share"
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:319`

## Page: Connected database (`/connected-databases/[connectedDatabaseId]`)

### Button: Remove

- **Application:** IntraForge
- **Location:** Connected database
- **Purpose:** Remove this item.
- **What happens:** The item is removed.
- **Data affected:** The item
- **Confirmation:** Depends on page
- **Can it be undone:** Add it again
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/connected-databases/[connectedDatabaseId]/_client.tsx:184`

### Button: Previous

- **Application:** IntraForge
- **Location:** Connected database
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `app/(app)/connected-databases/[connectedDatabaseId]/_client.tsx:292`

### Button: Next

- **Application:** IntraForge
- **Location:** Connected database
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/connected-databases/[connectedDatabaseId]/_client.tsx:300`

### Button: Share

- **Application:** IntraForge
- **Location:** Connected database
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/ShareSection.tsx:133`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Connected database
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:166`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Connected database -> dialog "Share"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:316`

### Button: Share

- **Application:** IntraForge
- **Location:** Connected database -> dialog "Share"
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:319`

## Page: Dashboard (analytics) (`/dashboards/[dashboardId]`)

### Button: Delete

- **Application:** IntraForge
- **Location:** Dashboard (analytics)
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:134`

### Button: Refresh

- **Application:** IntraForge
- **Location:** Dashboard (analytics)
- **Purpose:** Reload the data.
- **What happens:** Fetches the latest values.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:138`

### Button: Add widget

- **Application:** IntraForge
- **Location:** Dashboard (analytics)
- **Purpose:** Add a widget to the dashboard.
- **What happens:** Opens the widget dialog (dataset.analyze).
- **Data affected:** Dashboard
- **Confirmation:** No
- **Can it be undone:** Remove widget
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:142`

### Button: Add one

- **Application:** IntraForge
- **Location:** Dashboard (analytics)
- **Purpose:** Add the first item.
- **What happens:** Opens the create form.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:163`

### Button: Remove widget

- **Application:** IntraForge
- **Location:** Dashboard (analytics)
- **Purpose:** Remove a widget.
- **What happens:** Removes it from the dashboard.
- **Data affected:** Dashboard
- **Confirmation:** No
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:207`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Dashboard (analytics) -> dialog "Add widget"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:416`

### Button: Add widget

- **Application:** IntraForge
- **Location:** Dashboard (analytics) -> dialog "Add widget"
- **Purpose:** Add a widget to the dashboard.
- **What happens:** Opens the widget dialog (dataset.analyze).
- **Data affected:** Dashboard
- **Confirmation:** No
- **Can it be undone:** Remove widget
- **Next step:** --
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:419`

## Page: Environment (`/environments/[environmentId]`)

### Button: Remove

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Remove this item.
- **What happens:** The item is removed.
- **Data affected:** The item
- **Confirmation:** Depends on page
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:336`

### Button: Save

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:363`

### Button: Saved / Save

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:432`

### Button: New secret

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Add a secret to the environment.
- **What happens:** The value is encrypted and shown only once (environment.secrets.manage).
- **Data affected:** Secret
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:494`

### Button: Rotate

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Replace a credential / secret with a new one.
- **What happens:** The old value stops working; the new one is shown once.
- **Data affected:** Credential / secret
- **Confirmation:** Usually yes
- **Can it be undone:** --
- **Next step:** Update the program using it
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:532`

### Button: Delete

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:535`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:610`

### Button: Create

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:613`

### Button: New credential

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Issue a credential (token) for the application.
- **What happens:** Creates a token shown ONCE (application.credentials.manage).
- **Data affected:** Credential
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** Copy the token now
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:698`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:748`

### Button: Disconnect

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Remove a connected database.
- **What happens:** Deletes the connection (not the external data).
- **Data affected:** Connection
- **Confirmation:** Yes
- **Can it be undone:** Connect again
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:826`

### Button: Connect

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Bind the selected tenant database / bucket to this environment.
- **What happens:** Credentials scoped to this environment can then reach that resource and no other environment's (environment.manage).
- **Data affected:** Environment binding
- **Confirmation:** No
- **Can it be undone:** Change the binding
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:847`

### Button: New webhook

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Subscribe another system to events.
- **What happens:** Opens the dialog: URL, event types; deliveries are signed, at-least-once.
- **Data affected:** Webhook
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1057`

### Button: Disable / Enable

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Enable it again.
- **What happens:** Re-enables it.
- **Data affected:** Item state
- **Confirmation:** No
- **Can it be undone:** Disable
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1095`

### Button: Previous

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1263`

### Button: Next

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1275`

### Button: Disable environment / Enable environment

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Enable the environment again.
- **What happens:** Its credentials work again (environment.manage).
- **Data affected:** Environment
- **Confirmation:** No
- **Can it be undone:** Disable environment
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1404`

### Button: Delete environment

- **Application:** IntraForge
- **Location:** Environment
- **Purpose:** Delete the environment.
- **What happens:** Asks for confirmation; a production environment needs a second explicit confirmation.
- **Data affected:** Environment
- **Confirmation:** Yes (twice for production)
- **Can it be undone:** No
- **Next step:** --
- **Opens a dialog** first
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1407`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Environment -> dialog "Delete "…"?"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1497`

### Button: Delete environment

- **Application:** IntraForge
- **Location:** Environment -> dialog "Delete "…"?"
- **Purpose:** Delete the environment.
- **What happens:** Asks for confirmation; a production environment needs a second explicit confirmation.
- **Data affected:** Environment
- **Confirmation:** Yes (twice for production)
- **Can it be undone:** No
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1500`

## Page: Sign in (`/login`)

### Button: Verify / Sign in

- **Application:** IntraForge
- **Location:** Sign in
- **Purpose:** Sign in.
- **What happens:** Checks email and password (and the authenticator code when asked); max 10 attempts a minute.
- **Data affected:** Session
- **Confirmation:** No
- **Can it be undone:** Log out
- **Next step:** Dashboard
- **Source evidence:** `app/login/page.tsx:123`

## Page: Organizations (`/orgs`)

### Button: New organization

- **Application:** IntraForge
- **Location:** Organizations
- **Purpose:** Create an organization (company).
- **What happens:** Opens the New organization dialog (Name).
- **Data affected:** New organization; you become its administrator
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open it, add workspaces and members
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/page.tsx:73`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Organizations -> dialog "New organization"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/page.tsx:165`

### Button: Create

- **Application:** IntraForge
- **Location:** Organizations -> dialog "New organization"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/page.tsx:168`

## Page: Organization (`/orgs/[orgId]`)

### Button: Apps

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Open Apps.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/app-templates`
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:81`

### Button: Developer

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Open the developer area.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/developer`
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:84`

### Button: Teams

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Open Teams.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/teams`
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:87`

### Button: Units

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Open Units.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/units`
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:90`

### Button: Audit log

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Open the organization's audit log.
- **What happens:** Navigates (audit.read).
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/audit`
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:93`

### Button: New workspace

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Create a workspace in the organization.
- **What happens:** Opens the dialog (workspace.manage).
- **Data affected:** Workspace
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Create a project
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:103`

### Button: Add member

- **Application:** IntraForge
- **Location:** Organization
- **Purpose:** Add a member (to the organization, a team or a unit).
- **What happens:** Opens the dialog: email of an existing user / member.
- **Data affected:** Membership
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:140`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Organization -> dialog "New workspace"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:247`

### Button: Create

- **Application:** IntraForge
- **Location:** Organization -> dialog "New workspace"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:250`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Organization -> dialog "Add member"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:311`

### Button: Add

- **Application:** IntraForge
- **Location:** Organization -> dialog "Add member"
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:314`

## Page: Business app templates (`/orgs/[orgId]/app-templates`)

### Button: New template

- **Application:** IntraForge
- **Location:** Business app templates
- **Purpose:** Create an application template.
- **What happens:** Opens the dialog (app_template.manage).
- **Data affected:** Template
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add models
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/app-templates/_client.tsx:62`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Business app templates -> dialog "New app template"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/app-templates/_client.tsx:179`

### Button: Create

- **Application:** IntraForge
- **Location:** Business app templates -> dialog "New app template"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/app-templates/_client.tsx:182`

## Page: Audit log (organization) (`/orgs/[orgId]/audit`)

### Button: Apply

- **Application:** IntraForge
- **Location:** Audit log (organization)
- **Purpose:** Apply the upgrade / transition.
- **What happens:** Applies it (safe additions only; local changes are never overwritten).
- **Data affected:** Installed app
- **Confirmation:** Depends
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:170`

### Button: Clear

- **Application:** IntraForge
- **Location:** Audit log (organization)
- **Purpose:** Clear the filters / search.
- **What happens:** All filters reset.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:173`

### Button: Previous

- **Application:** IntraForge
- **Location:** Audit log (organization)
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:246`

### Button: Next

- **Application:** IntraForge
- **Location:** Audit log (organization)
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:254`

## Page: Developer portal (`/orgs/[orgId]/developer`)

### Button: Manage applications

- **Application:** IntraForge
- **Location:** Developer portal
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/developer/applications`
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/_client.tsx:84`

### Button: New application

- **Application:** IntraForge
- **Location:** Developer portal
- **Purpose:** Register an application (API client).
- **What happens:** Opens the dialog (application.create).
- **Data affected:** Application + service account
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Grant permissions
- **Goes to:** `/orgs/:id/developer/applications`
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/_client.tsx:93`

## Page: Developer: Applications (`/orgs/[orgId]/developer/applications`)

### Button: New application

- **Application:** IntraForge
- **Location:** Developer: Applications
- **Purpose:** Register an application (API client).
- **What happens:** Opens the dialog (application.create).
- **Data affected:** Application + service account
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Grant permissions
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:67`

### Button: Connect application

- **Application:** IntraForge
- **Location:** Developer: Applications
- **Purpose:** Start the connect-an-application wizard.
- **What happens:** Opens the wizard.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/orgs/:id/developer/applications/connect`
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:70`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Developer: Applications -> dialog "New application"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:189`

### Button: Create

- **Application:** IntraForge
- **Location:** Developer: Applications -> dialog "New application"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:192`

## Page: Developer: Connect application (`/orgs/[orgId]/developer/applications/connect`)

### Button: Next

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:264`

### Button: Back

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Go back one step.
- **What happens:** Returns to the previous step.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:295`

### Button: Create application

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Finish registering the application.
- **What happens:** Creates it.
- **Data affected:** Application
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open application
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:298`

### Button: Skip for now

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Skip this wizard step.
- **What happens:** --
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:389`

### Button: Granting…

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** (busy state of Grant)
- **What happens:** Shown while the grant is being created.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:393`

### Button: Generating… / Generate credential

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Issue a credential in the connect wizard.
- **What happens:** The token is shown once.
- **Data affected:** Credential
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** Copy it
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:412`

### Button: Testing… / Test connection

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Check that IntraForge can reach the external database.
- **What happens:** Connects with the saved settings and lists its tables; read-only.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Browse a table
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:435`

### Button: Done — open application

- **Application:** IntraForge
- **Location:** Developer: Connect application
- **Purpose:** Finish the wizard and open the application.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:455`

## Page: Developer: Environments (`/orgs/[orgId]/developer/environments`)

### Button: Create environment

- **Application:** IntraForge
- **Location:** Developer: Environments
- **Purpose:** Create the environment.
- **What happens:** Creates it.
- **Data affected:** Environment
- **Confirmation:** No
- **Can it be undone:** Delete environment
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:136`

### Button: Go to Applications

- **Application:** IntraForge
- **Location:** Developer: Environments
- **Purpose:** Open the applications list.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:156`

### Button: Clone

- **Application:** IntraForge
- **Location:** Developer: Environments
- **Purpose:** Copy an environment.
- **What happens:** Creates a new environment with the same non-secret configuration (environment.manage).
- **Data affected:** New environment
- **Confirmation:** No
- **Can it be undone:** Delete environment
- **Next step:** Open it
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:223`

### Button: Disable / Enable

- **Application:** IntraForge
- **Location:** Developer: Environments
- **Purpose:** Enable it again.
- **What happens:** Re-enables it.
- **Data affected:** Item state
- **Confirmation:** No
- **Can it be undone:** Disable
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:230`

### Button: Delete

- **Application:** IntraForge
- **Location:** Developer: Environments
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:236`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Developer: Environments -> dialog "Create environment"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:366`

### Button: Create

- **Application:** IntraForge
- **Location:** Developer: Environments -> dialog "Create environment"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:369`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Developer: Environments -> dialog "Delete "…"?"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:455`

### Button: Delete environment

- **Application:** IntraForge
- **Location:** Developer: Environments -> dialog "Delete "…"?"
- **Purpose:** Delete the environment.
- **What happens:** Asks for confirmation; a production environment needs a second explicit confirmation.
- **Data affected:** Environment
- **Confirmation:** Yes (twice for production)
- **Can it be undone:** No
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:458`

## Page: Teams (`/orgs/[orgId]/teams`)

### Button: New team

- **Application:** IntraForge
- **Location:** Teams
- **Purpose:** Create a team.
- **What happens:** Opens the dialog (users.manage).
- **Data affected:** Team
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add member
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:89`

### Button: Add member

- **Application:** IntraForge
- **Location:** Teams
- **Purpose:** Add a member (to the organization, a team or a unit).
- **What happens:** Opens the dialog: email of an existing user / member.
- **Data affected:** Membership
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:120`

### Button: Remove

- **Application:** IntraForge
- **Location:** Teams
- **Purpose:** Remove this item.
- **What happens:** The item is removed.
- **Data affected:** The item
- **Confirmation:** Depends on page
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:138`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Teams -> dialog "New team"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:228`

### Button: Create

- **Application:** IntraForge
- **Location:** Teams -> dialog "New team"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:231`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Teams -> dialog "Add member to …"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:296`

### Button: Add

- **Application:** IntraForge
- **Location:** Teams -> dialog "Add member to …"
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:299`

## Page: Organizational units (`/orgs/[orgId]/units`)

### Button: Add sub-unit

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Create a unit under this one.
- **What happens:** Opens the dialog.
- **Data affected:** Unit
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:140`

### Button: Members

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Show / manage the unit's members.
- **What happens:** Opens the members dialog.
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:146`

### Button: Edit

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:152`

### Button: Delete

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:158`

### Button: New unit

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Create an organizational unit.
- **What happens:** Opens the dialog (org_unit.manage).
- **Data affected:** Unit
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** Add sub-unit
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:184`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:309`

### Button: Create

- **Application:** IntraForge
- **Location:** Organizational units
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:312`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Organizational units -> dialog "Edit …"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:386`

### Button: Save

- **Application:** IntraForge
- **Location:** Organizational units -> dialog "Edit …"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:389`

### Button: Remove

- **Application:** IntraForge
- **Location:** Organizational units -> dialog "Members of …"
- **Purpose:** Remove this item.
- **What happens:** The item is removed.
- **Data affected:** The item
- **Confirmation:** Depends on page
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:472`

### Button: Add

- **Application:** IntraForge
- **Location:** Organizational units -> dialog "Members of …"
- **Purpose:** Add the item.
- **What happens:** Adds it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:500`

## Page: Workspace (`/orgs/[orgId]/workspaces/[workspaceId]`)

### Button: New project

- **Application:** IntraForge
- **Location:** Workspace
- **Purpose:** Create a project in the workspace.
- **What happens:** Opens the dialog (workspace.manage).
- **Data affected:** Project
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Create buckets / databases
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/_client.tsx:69`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Workspace -> dialog "New project"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/_client.tsx:154`

### Button: Create

- **Application:** IntraForge
- **Location:** Workspace -> dialog "New project"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/_client.tsx:157`

## Page: Project (`/projects/[projectId]`)

### Button: Applications

- **Application:** IntraForge
- **Location:** Project
- **Purpose:** Open Applications.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/projects/:id/apps`
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:109`

### Button: New bucket

- **Application:** IntraForge
- **Location:** Project
- **Purpose:** Create a file bucket.
- **What happens:** Opens the dialog (storage.manage).
- **Data affected:** Bucket
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Upload files
- **Opens a dialog** first
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:118`

### Button: New database

- **Application:** IntraForge
- **Location:** Project
- **Purpose:** Create a tenant database.
- **What happens:** Opens the dialog (database.create).
- **Data affected:** Tenant database (real PostgreSQL schema)
- **Confirmation:** No
- **Can it be undone:** Drop database
- **Next step:** New table
- **Opens a dialog** first
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:155`

### Button: New connection

- **Application:** IntraForge
- **Location:** Project
- **Purpose:** Connect an external PostgreSQL database (read-only).
- **What happens:** Opens the dialog: host, port, database, username, SSL mode (connection.manage).
- **Data affected:** Connected database (encrypted credentials)
- **Confirmation:** No
- **Can it be undone:** Disconnect
- **Next step:** Test connection, browse
- **Opens a dialog** first
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:192`

### Button: Install app

- **Application:** IntraForge
- **Location:** Project
- **Purpose:** Install a service application (Spare Parts).
- **What happens:** Opens the install dialog: organization, name in Apps, shop name.
- **Data affected:** Service application (schema, role, bucket)
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Opens a dialog** first
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:237`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Project -> dialog "Install app"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:443`

### Button: Install

- **Application:** IntraForge
- **Location:** Project -> dialog "Install app"
- **Purpose:** Install the application.
- **What happens:** Installs it into the chosen organization / project.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:446`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Project -> dialog "New bucket"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:503`

### Button: Create

- **Application:** IntraForge
- **Location:** Project -> dialog "New bucket"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:506`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Project -> dialog "New database"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:564`

### Button: Create

- **Application:** IntraForge
- **Location:** Project -> dialog "New database"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:567`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Project -> dialog "Connect a database"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:710`

### Button: Connect

- **Application:** IntraForge
- **Location:** Project -> dialog "Connect a database"
- **Purpose:** Bind the selected tenant database / bucket to this environment.
- **What happens:** Credentials scoped to this environment can then reach that resource and no other environment's (environment.manage).
- **Data affected:** Environment binding
- **Confirmation:** No
- **Can it be undone:** Change the binding
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:713`

## Page: Applications (built-in business apps) (`/projects/[projectId]/apps`)

### Button: Open

- **Application:** IntraForge
- **Location:** Applications (built-in business apps)
- **Purpose:** Open the item.
- **What happens:** Navigates to it.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:245`

### Button: Finishing… / Finish setup

- **Application:** IntraForge
- **Location:** Applications (built-in business apps)
- **Purpose:** Finish the connect wizard.
- **What happens:** Completes the registration.
- **Data affected:** Application
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open application
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:249`

### Button: Install another copy

- **Application:** IntraForge
- **Location:** Applications (built-in business apps)
- **Purpose:** Install another copy of a built-in business app.
- **What happens:** Opens the install dialog.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:261`

### Button: Install

- **Application:** IntraForge
- **Location:** Applications (built-in business apps)
- **Purpose:** Install the application.
- **What happens:** Installs it into the chosen organization / project.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:265`

### Button: Close

- **Application:** IntraForge
- **Location:** Applications (built-in business apps) -> dialog "Install …"
- **Purpose:** Close the dialog.
- **What happens:** The dialog closes.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:307`

### Button: Open application

- **Application:** IntraForge
- **Location:** Applications (built-in business apps) -> dialog "Install …"
- **Purpose:** Open the installed application.
- **What happens:** Navigates to it (service apps: no second sign-in).
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:310`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Applications (built-in business apps) -> dialog "Install …"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:364`

### Button: Try again / Install

- **Application:** IntraForge
- **Location:** Applications (built-in business apps) -> dialog "Install …"
- **Purpose:** Install the application.
- **What happens:** Installs it into the chosen organization / project.
- **Data affected:** Installed app
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:367`

## Page: Create account (`/register`)

### Button: Create account

- **Application:** IntraForge
- **Location:** Create account
- **Purpose:** Create your IntraForge account.
- **What happens:** Registers the account with first name, email and password, and signs you in.
- **Data affected:** New user account
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Welcome / create an organization
- **Source evidence:** `app/register/page.tsx:100`

## Page: Open application (`/service-apps/[appId]/open`)

### Button: Back to Apps

- **Application:** IntraForge
- **Location:** Open application
- **Purpose:** Return to the Apps page.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Goes to:** `/apps`
- **Source evidence:** `app/(app)/service-apps/[appId]/open/_client.tsx:31`

## Page: Application settings (`/service-apps/[appId]/settings`)

### Button: Save

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:176`

### Button: Disable / Enable

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Enable it again.
- **What happens:** Re-enables it.
- **Data affected:** Item state
- **Confirmation:** No
- **Can it be undone:** Disable
- **Next step:** --
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:210`

### Button: Remove...

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Remove the installed application.
- **What happens:** Shows a preview of what is affected; keep data, or (option) delete data after a backup -- nothing is deleted if the backup fails.
- **Data affected:** Installation (and data, if chosen)
- **Confirmation:** Yes (type the name)
- **Can it be undone:** Reinstate (when data was kept)
- **Next step:** --
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:254`

### Button: Back up, then delete everything / Remove, keep data

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Remove an application but keep its data.
- **What happens:** Closes and hides it; Reinstate brings it back with everything.
- **Data affected:** Installation
- **Confirmation:** Yes
- **Can it be undone:** Reinstate
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:296`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:300`

### Button: Reinstate

- **Application:** IntraForge
- **Location:** Application settings
- **Purpose:** Bring back a removed application whose data was kept.
- **What happens:** Reinstates it.
- **Data affected:** Installation
- **Confirmation:** No
- **Can it be undone:** Remove
- **Next step:** Open
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:329`

## Page: Table (`/tables/[tableId]`)

### Button: Add column

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Add a column to the table.
- **What happens:** Opens the dialog (database.schema.manage).
- **Data affected:** Column
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:138`

### Button: Add row

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Save the new row.
- **What happens:** Saves it (database.write).
- **Data affected:** Row
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:141`

### Button: Edit

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:220`

### Button: Delete

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Delete this item.
- **What happens:** The item is deleted on the server.
- **Data affected:** The item
- **Confirmation:** Usually yes (confirmation prompt)
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:229`

### Button: Previous

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Go to the previous page of results.
- **What happens:** Loads the previous page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Next
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:248`

### Button: Next

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Go to the next page of results / next step.
- **What happens:** Loads the next page.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Previous
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:260`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Table -> dialog "Add column"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:449`

### Button: Add column

- **Application:** IntraForge
- **Location:** Table -> dialog "Add column"
- **Purpose:** Add a column to the table.
- **What happens:** Opens the dialog (database.schema.manage).
- **Data affected:** Column
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:452`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:576`

### Button: Save / Add row

- **Application:** IntraForge
- **Location:** Table
- **Purpose:** Save the new row.
- **What happens:** Saves it (database.write).
- **Data affected:** Row
- **Confirmation:** No
- **Can it be undone:** Delete
- **Next step:** --
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:579`

## Page: Table analytics (`/tables/[tableId]/analytics`)

### Button: Run

- **Application:** IntraForge
- **Location:** Table analytics
- **Purpose:** Run the chosen statistics operation.
- **What happens:** Shows the result (database.read).
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save to a dashboard
- **Source evidence:** `app/(app)/tables/[tableId]/analytics/_client.tsx:213`

## Page: CSV import (`/tables/[tableId]/import`)

### Button: Create bucket

- **Application:** IntraForge
- **Location:** CSV import
- **Purpose:** Create the file bucket.
- **What happens:** Creates it (storage.manage).
- **Data affected:** Bucket
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Upload files
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:277`

### Button: Use this file

- **Application:** IntraForge
- **Location:** CSV import
- **Purpose:** Pick this stored file for the import.
- **What happens:** Selects the file.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Change
- **Next step:** Preview
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:315`

### Button: Back

- **Application:** IntraForge
- **Location:** CSV import
- **Purpose:** Go back one step.
- **What happens:** Returns to the previous step.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:389`

### Button: Starting… / Start import

- **Application:** IntraForge
- **Location:** CSV import
- **Purpose:** Start the CSV import job.
- **What happens:** Rows are inserted in the background; the job shows pending / running / completed and rejected rows (dataset.import).
- **Data affected:** Table rows
- **Confirmation:** No
- **Can it be undone:** Delete rows
- **Next step:** Check the rows
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:399`

### Button: Import another file

- **Application:** IntraForge
- **Location:** CSV import
- **Purpose:** Start a new import.
- **What happens:** Resets the import form.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:460`

## Page: Database (`/tenant-databases/[dbId]`)

### Button: Drop database

- **Application:** IntraForge
- **Location:** Database
- **Purpose:** Delete the tenant database and all its tables.
- **What happens:** Asks to type the name to confirm (database.delete).
- **Data affected:** Database (all data)
- **Confirmation:** Yes (typed)
- **Can it be undone:** No (only from a backup)
- **Next step:** --
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:116`

### Button: New table

- **Application:** IntraForge
- **Location:** Database
- **Purpose:** Create a table in the database.
- **What happens:** Opens the dialog (database.schema.manage).
- **Data affected:** Table
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add columns
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:119`

### Button: New dashboard

- **Application:** IntraForge
- **Location:** Database
- **Purpose:** Create an analytics dashboard.
- **What happens:** Opens the dialog (dataset.analyze).
- **Data affected:** Dashboard
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Add widget
- **Opens a dialog** first
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:162`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Database -> dialog "New table"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:279`

### Button: Create

- **Application:** IntraForge
- **Location:** Database -> dialog "New table"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:282`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Database -> dialog "New dashboard"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:349`

### Button: Create

- **Application:** IntraForge
- **Location:** Database -> dialog "New dashboard"
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:352`

### Button: Share

- **Application:** IntraForge
- **Location:** Database
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `components/ShareSection.tsx:133`

### Button: Revoke

- **Application:** IntraForge
- **Location:** Database
- **Purpose:** Revoke a share / credential / secret.
- **What happens:** Access ends immediately.
- **Data affected:** Grant / credential
- **Confirmation:** Usually yes
- **Can it be undone:** Grant again
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:166`

### Button: Cancel

- **Application:** IntraForge
- **Location:** Database -> dialog "Share"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:316`

### Button: Share

- **Application:** IntraForge
- **Location:** Database -> dialog "Share"
- **Purpose:** Share this resource with a member or team.
- **What happens:** Opens the share dialog: who, read only / read & write (sharing.manage).
- **Data affected:** Share grant
- **Confirmation:** No
- **Can it be undone:** Revoke
- **Next step:** --
- **Source evidence:** `components/ShareSection.tsx:319`

## Page: Welcome (`/welcome`)

### Button: Continue

- **Application:** IntraForge
- **Location:** Welcome
- **Purpose:** Go on to the next step.
- **What happens:** --
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Back
- **Next step:** --
- **Source evidence:** `app/welcome/page.tsx:82`

### Button: Create

- **Application:** IntraForge
- **Location:** Welcome
- **Purpose:** Create the item.
- **What happens:** Creates it.
- **Data affected:** New item
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/welcome/page.tsx:95`

### Button: Hide / How?

- **Application:** IntraForge
- **Location:** Welcome
- **Purpose:** Show how to join / use this.
- **What happens:** Shows help text.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Hide
- **Next step:** --
- **Source evidence:** `app/welcome/page.tsx:109`

### Button: Organizations

- **Application:** IntraForge
- **Location:** Welcome
- **Purpose:** Open Organizations.
- **What happens:** Navigates.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/welcome/page.tsx:117`
