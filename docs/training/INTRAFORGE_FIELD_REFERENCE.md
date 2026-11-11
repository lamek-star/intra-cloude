# IntraForge -- field reference (Level 1)

Every user-visible form field found in the code, page by page. *Required* is what the form itself enforces; the server checks again. Purposes marked NOT CONFIRMED are fields whose meaning the code does not make clear enough to state.

## Page: Installed business app (definition) (`/app-instances/[instanceId]`)

### Field: Name

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Edit app"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Edit app" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Archived
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:405`

### Field: Archived

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Edit app"
- **Type:** checkbox
- **Purpose:** Hide the item from normal use without deleting it.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Edit app" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:408`

### Field: New model name

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** text
- **Purpose:** Name of a new model (table) in a template.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, New relationship name, From, References, Type, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:446`

### Field: Key

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** text
- **Purpose:** Name of a variable / secret.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, New relationship name, From, References, Type, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:458`

### Field: New relationship name

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** text
- **Purpose:** Name of a new relationship.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, From, References, Type, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:520`

### Field: From

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** select
- **Purpose:** Start (period) / origin.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New relationship name, References, Type, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:542`

### Field: References

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** select (options: Many-to-one (reference), Many-to-many)
- **Purpose:** The model a relationship points to.
- **What user enters:** Choose one option: Many-to-one (reference), Many-to-many.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New relationship name, From, Type, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:552`

### Field: Type

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** select (options: Many-to-one (reference), Many-to-many, Restrict, Set null)
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option: Many-to-one (reference), Many-to-many, Restrict, Set null.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New relationship name, From, References, On delete, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:562`

### Field: On delete

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** select (options: Restrict, Set null)
- **Purpose:** What happens to linked records when the target is deleted.
- **What user enters:** Choose one option: Restrict, Set null.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New relationship name, From, References, Type, Target version
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:574`

### Field: Target version

- **Application:** IntraForge
- **Page:** Installed business app (definition)
- **Type:** select (options: Select a version…)
- **Purpose:** The template version to upgrade an installed app to.
- **What user enters:** Choose one option: Select a version….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New relationship name, From, References, Type, On delete
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:700`

### Field: Share with

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Share"
- **Type:** select (options: A specific member, A team, Everyone in this organization)
- **Purpose:** Member or team to share with.
- **What user enters:** Choose one option: A specific member, A team, Everyone in this organization.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Member, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:259`

### Field: Member

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Share"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:272`

### Field: Team

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Share"
- **Type:** select
- **Purpose:** A team of members.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Access level
- **Source evidence:** `components/ShareSection.tsx:288`

### Field: Access level

- **Application:** IntraForge
- **Page:** Installed business app (definition) -> dialog "Share"
- **Type:** select
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Team
- **Source evidence:** `components/ShareSection.tsx:303`

## Page: Model records (`/app-models/[modelId]`)

### Field: New field name

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a new field.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Type, Default, Required, New workflow name, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1100`

### Field: Key

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a variable / secret.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Type, Default, Required, New workflow name, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1112`

### Field: Type

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Default, Required, New workflow name, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1122`

### Field: Default

- **Application:** IntraForge
- **Page:** Model records
- **Type:** checkbox
- **Purpose:** Default value for new records.
- **What user enters:** Tick to switch on.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Required, New workflow name, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1139`

### Field: Required

- **Application:** IntraForge
- **Page:** Model records
- **Type:** checkbox
- **Purpose:** The field must be filled in.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, New workflow name, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1142`

### Field: New workflow name

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a new workflow.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, State field, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1196`

### Field: State field

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select
- **Purpose:** The field that holds a record's workflow state.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, New state name, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1218`

### Field: New state name

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a new workflow state.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New transition name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1257`

### Field: New transition name

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a new workflow step.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1339`

### Field: From

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select (options: (any state))
- **Purpose:** Start (period) / origin.
- **What user enters:** Choose one option: (any state).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1361`

### Field: To

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select
- **Purpose:** End (period) / destination.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1376`

### Field: Requires approval

- **Application:** IntraForge
- **Page:** Model records
- **Type:** checkbox
- **Purpose:** The workflow step needs an approver (app_instance.workflow.approve).
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1389`

### Field: Notify URL (optional)

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Address notified about an operation.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1394`

### Field: Unique constraint name

- **Application:** IntraForge
- **Page:** Model records
- **Type:** text
- **Purpose:** Name of a rule that combinations of values are unique.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1446`

### Field: Fields and relationships (select 2 or more)

- **Application:** IntraForge
- **Page:** Model records
- **Type:** checkbox
- **Purpose:** Members of a combined uniqueness rule.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1468`

### Field: Default to current time

- **Application:** IntraForge
- **Page:** Model records
- **Type:** checkbox
- **Purpose:** New records get the current date/time.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:1536`

### Field: Member

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select (options: Choose a member, Choose a unit, View records, View and edit records)
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option: Choose a member, Choose a unit, View records, View and edit records.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `components/AppModelAccess.tsx:103`

### Field: Organizational unit

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select (options: Choose a unit, View records, View and edit records)
- **Purpose:** A unit of the organization's structure (branch, department...).
- **What user enters:** Choose one option: Choose a unit, View records, View and edit records.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `components/AppModelAccess.tsx:107`

### Field: Access level

- **Application:** IntraForge
- **Page:** Model records
- **Type:** select (options: View records, View and edit records)
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option: View records, View and edit records.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `components/AppModelAccess.tsx:111`

### Field: Expires at (optional, local time)

- **Application:** IntraForge
- **Page:** Model records
- **Type:** datetime-local
- **Purpose:** When a credential stops working; empty = no expiry.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New field name, Key, Type, Default, Required, New workflow name, State field, New state name
- **Source evidence:** `components/AppModelAccess.tsx:114`

### Field: Share with

- **Application:** IntraForge
- **Page:** Model records -> dialog "Share"
- **Type:** select (options: A specific member, A team, Everyone in this organization)
- **Purpose:** Member or team to share with.
- **What user enters:** Choose one option: A specific member, A team, Everyone in this organization.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Member, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:259`

### Field: Member

- **Application:** IntraForge
- **Page:** Model records -> dialog "Share"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:272`

### Field: Team

- **Application:** IntraForge
- **Page:** Model records -> dialog "Share"
- **Type:** select
- **Purpose:** A team of members.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Access level
- **Source evidence:** `components/ShareSection.tsx:288`

### Field: Access level

- **Application:** IntraForge
- **Page:** Model records -> dialog "Share"
- **Type:** select
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Team
- **Source evidence:** `components/ShareSection.tsx:303`

## Page: Record (`/app-models/[modelId]/records/[recordId]`)

### Field: Bucket

- **Application:** IntraForge
- **Page:** Record -> dialog "Attach a file"
- **Type:** select (options: Select a bucket…)
- **Purpose:** A file storage area.
- **What user enters:** Choose one option: Select a bucket….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** the "Attach a file" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** File
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:536`

### Field: File

- **Application:** IntraForge
- **Page:** Record -> dialog "Attach a file"
- **Type:** select (options: Select a file…)
- **Purpose:** The file to upload or choose.
- **What user enters:** Choose one option: Select a file….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** the "Attach a file" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Bucket
- **Source evidence:** `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx:555`

## Page: Template builder (`/app-templates/[templateId]`)

### Field: Required

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** checkbox
- **Purpose:** The field must be filled in.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:462`

### Field: New model name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new model (table) in a template.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:815`

### Field: Key

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a variable / secret.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:827`

### Field: New field name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new field.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, Type, Default, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:872`

### Field: Type

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Default, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:894`

### Field: Default

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** checkbox
- **Purpose:** Default value for new records.
- **What user enters:** Tick to switch on.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Unique constraint name, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:911`

### Field: Unique constraint name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a rule that combinations of values are unique.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Fields and relationships (select 2 or more), New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:965`

### Field: Fields and relationships (select 2 or more)

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** checkbox
- **Purpose:** Members of a combined uniqueness rule.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, New workflow name
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:987`

### Field: New workflow name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new workflow.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1060`

### Field: State field

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select
- **Purpose:** The field that holds a record's workflow state.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1082`

### Field: New state name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new workflow state.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1127`

### Field: New transition name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new workflow step.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1195`

### Field: From

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select (options: (any state))
- **Purpose:** Start (period) / origin.
- **What user enters:** Choose one option: (any state).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1217`

### Field: To

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select
- **Purpose:** End (period) / destination.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1232`

### Field: Requires approval

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** checkbox
- **Purpose:** The workflow step needs an approver (app_instance.workflow.approve).
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1245`

### Field: Notify URL (optional)

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Address notified about an operation.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1250`

### Field: New relationship name

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** text
- **Purpose:** Name of a new relationship.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1304`

### Field: References

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select (options: Many-to-one (reference), Many-to-many)
- **Purpose:** The model a relationship points to.
- **What user enters:** Choose one option: Many-to-one (reference), Many-to-many.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1336`

### Field: On delete

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** select (options: Restrict, Set null)
- **Purpose:** What happens to linked records when the target is deleted.
- **What user enters:** Choose one option: Restrict, Set null.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1358`

### Field: Default to current time

- **Application:** IntraForge
- **Page:** Template builder
- **Type:** checkbox
- **Purpose:** New records get the current date/time.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Required, New model name, Key, New field name, Type, Default, Unique constraint name, Fields and relationships (select 2 or more)
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1436`

### Field: Label

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Rename"
- **Type:** text
- **Purpose:** Display name of a field or item.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Rename" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1510`

### Field: Label

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Edit field"
- **Type:** text
- **Purpose:** Display name of a field or item.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Edit field" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Default value
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1557`

### Field: Default value

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Edit field"
- **Type:** text
- **Purpose:** Default value for new records.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Edit field" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Label
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1567`

### Field: Name

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Edit template details"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Edit template details" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Description, Archived
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1640`

### Field: Description

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Edit template details"
- **Type:** textarea
- **Purpose:** Longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Edit template details" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Archived
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1644`

### Field: Archived

- **Application:** IntraForge
- **Page:** Template builder -> dialog "Edit template details"
- **Type:** checkbox
- **Purpose:** Hide the item from normal use without deleting it.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "Edit template details" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Description
- **Source evidence:** `app/(app)/app-templates/[templateId]/_client.tsx:1652`

## Page: Application (API client) (`/applications/[applicationId]`)

### Field: Permission code

- **Application:** IntraForge
- **Page:** Application (API client) -> dialog "Grant permission"
- **Type:** text
- **Purpose:** The permission (capability) to grant, for example database.read.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Grant permission" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Resource type, Resource ID
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:498`

### Field: Resource type

- **Application:** IntraForge
- **Page:** Application (API client) -> dialog "Grant permission"
- **Type:** text
- **Purpose:** Kind of resource a permission or audit filter refers to.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Grant permission" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Permission code, Resource ID
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:509`

### Field: Resource ID

- **Application:** IntraForge
- **Page:** Application (API client) -> dialog "Grant permission"
- **Type:** text
- **Purpose:** Identifier of the resource.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Grant permission" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Permission code, Resource type
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:519`

### Field: Name

- **Application:** IntraForge
- **Page:** Application (API client) -> dialog "New environment"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New environment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:583`

### Field: Type

- **Application:** IntraForge
- **Page:** Application (API client) -> dialog "New environment"
- **Type:** select
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New environment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:594`

## Page: Apps (`/apps`)

### Field: Organization

- **Application:** IntraForge
- **Page:** Apps -> dialog "Install …"
- **Type:** select
- **Purpose:** The organization (company).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `permissions.manage`, `spareparts.settings.manage`, `spareparts.view`, `users.manage`
- **What happens after Save:** the "Install …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Shop name, Currency
- **Source evidence:** `app/(app)/apps/_client.tsx:240`

### Field: Shop name

- **Application:** IntraForge
- **Page:** Apps -> dialog "Install …"
- **Type:** text
- **Purpose:** Spare Parts: the shop's name shown in the app and on documents (saved in IntraForge).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `permissions.manage`, `spareparts.settings.manage`, `spareparts.view`, `users.manage`
- **What happens after Save:** the "Install …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Organization, Currency
- **Source evidence:** `app/(app)/apps/_client.tsx:251`

### Field: Currency

- **Application:** IntraForge
- **Page:** Apps -> dialog "Install …"
- **Type:** text
- **Purpose:** 3-letter currency code for the app's prices.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `permissions.manage`, `spareparts.settings.manage`, `spareparts.view`, `users.manage`
- **What happens after Save:** the "Install …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Organization, Shop name
- **Source evidence:** `app/(app)/apps/_client.tsx:262`

## Page: Built-in Spare Parts business app: overview (`/apps/[instanceId]`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in Spare Parts business app: overview
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `components/business/BusinessApp.tsx:142`

## Page: Built-in app: Customers (`/apps/[instanceId]/customers`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Customers
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Customers
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Customers
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Stock (`/apps/[instanceId]/inventory`)

### Field: Warehouse

- **Application:** IntraForge
- **Page:** Built-in app: Stock
- **Type:** select (options: All warehouses)
- **Purpose:** Built-in business app: the warehouse.
- **What user enters:** Choose one option: All warehouses.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search, *
- **Source evidence:** `components/business/Inventory.tsx:52`

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Stock
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Stock
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Stock
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Part numbers (`/apps/[instanceId]/part-numbers`)

### Field: Search part numbers

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers
- **Type:** search
- **Purpose:** Search box for part numbers.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 044650K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search, *
- **Source evidence:** `components/business/PartNumbers.tsx:102`

### Field: Part number *

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers -> dialog "Add part number"
- **Type:** text
- **Purpose:** Built-in business app: the part number to add (required).
- **What user enters:** Text. Placeholder: "e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Source
- **Source evidence:** `components/business/PartNumbers.tsx:247`

### Field: Source

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers -> dialog "Add part number"
- **Type:** text
- **Purpose:** Where data comes from.
- **What user enters:** Text. Placeholder: "e.g. OEM, aftermarket, supplier".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Part number *
- **Source evidence:** `components/business/PartNumbers.tsx:251`

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search part numbers, Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search part numbers, Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Part numbers
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search part numbers, Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Products (`/apps/[instanceId]/products`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Products
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Products
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Products
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Product (`/apps/[instanceId]/products/[partId]`)

### Field: Add an image or document

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** file
- **Purpose:** Attach a file to the product.
- **What user enters:** Choose a file.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Warehouse, Search part numbers, Search, *
- **Source evidence:** `components/business/ProductDetail.tsx:245`

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Add an image or document, Warehouse, Search part numbers, Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Warehouse

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** select (options: All warehouses)
- **Purpose:** Built-in business app: the warehouse.
- **What user enters:** Choose one option: All warehouses.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Add an image or document, Find a part number, Search part numbers, Search, *
- **Source evidence:** `components/business/Inventory.tsx:52`

### Field: Search part numbers

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** search
- **Purpose:** Search box for part numbers.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 044650K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Add an image or document, Find a part number, Warehouse, Search, *
- **Source evidence:** `components/business/PartNumbers.tsx:102`

### Field: Part number *

- **Application:** IntraForge
- **Page:** Built-in app: Product -> dialog "Add part number"
- **Type:** text
- **Purpose:** Built-in business app: the part number to add (required).
- **What user enters:** Text. Placeholder: "e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Source
- **Source evidence:** `components/business/PartNumbers.tsx:247`

### Field: Source

- **Application:** IntraForge
- **Page:** Built-in app: Product -> dialog "Add part number"
- **Type:** text
- **Purpose:** Where data comes from.
- **What user enters:** Text. Placeholder: "e.g. OEM, aftermarket, supplier".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Part number *
- **Source evidence:** `components/business/PartNumbers.tsx:251`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Add an image or document, Find a part number, Warehouse, Search part numbers, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Product
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Add an image or document, Find a part number, Warehouse, Search part numbers, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Receive stock (`/apps/[instanceId]/receive`)

### Field: Warehouse

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** select (options: Choose a warehouse…)
- **Purpose:** Built-in business app: the warehouse.
- **What user enters:** Choose one option: Choose a warehouse….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Quantity, Supplier, Unit cost, Reference, Find a part number
- **Source evidence:** `components/business/ReceiveStock.tsx:173`

### Field: Quantity

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** text
- **Purpose:** Number of units.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Supplier, Unit cost, Reference, Find a part number
- **Source evidence:** `components/business/ReceiveStock.tsx:185`

### Field: Supplier

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** select (options: No supplier)
- **Purpose:** Built-in business app: the supplier.
- **What user enters:** Choose one option: No supplier.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Quantity, Unit cost, Reference, Find a part number
- **Source evidence:** `components/business/ReceiveStock.tsx:198`

### Field: Unit cost

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** text
- **Purpose:** Cost per unit.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Quantity, Supplier, Reference, Find a part number
- **Source evidence:** `components/business/ReceiveStock.tsx:211`

### Field: Reference

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** text
- **Purpose:** Your reference for the document.
- **What user enters:** Text. Placeholder: "Delivery note or invoice number".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Quantity, Supplier, Unit cost, Find a part number
- **Source evidence:** `components/business/ReceiveStock.tsx:222`

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Receive stock
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Quantity, Supplier, Unit cost, Reference
- **Source evidence:** `components/business/BusinessApp.tsx:142`

## Page: Built-in app: Sales (`/apps/[instanceId]/sales`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Sales
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Sales
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Sales
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Sale (`/apps/[instanceId]/sales/[orderId]`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Sale
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `components/business/BusinessApp.tsx:142`

## Page: Built-in app: New sale (`/apps/[instanceId]/sales/new`)

### Field: Customer

- **Application:** IntraForge
- **Page:** Built-in app: New sale
- **Type:** select (options: Choose a customer…)
- **Purpose:** Built-in business app: the customer.
- **What user enters:** Choose one option: Choose a customer….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Warehouse, Quantity, Unit price, Find a part number
- **Source evidence:** `components/business/SellStock.tsx:215`

### Field: Warehouse

- **Application:** IntraForge
- **Page:** Built-in app: New sale
- **Type:** select (options: Choose…)
- **Purpose:** Built-in business app: the warehouse.
- **What user enters:** Choose one option: Choose….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Customer, Quantity, Unit price, Find a part number
- **Source evidence:** `components/business/SellStock.tsx:300`

### Field: Quantity

- **Application:** IntraForge
- **Page:** Built-in app: New sale
- **Type:** text
- **Purpose:** Number of units.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Customer, Warehouse, Unit price, Find a part number
- **Source evidence:** `components/business/SellStock.tsx:311`

### Field: Unit price

- **Application:** IntraForge
- **Page:** Built-in app: New sale
- **Type:** text
- **Purpose:** Price per unit.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Customer, Warehouse, Quantity, Find a part number
- **Source evidence:** `components/business/SellStock.tsx:315`

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: New sale
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Customer, Warehouse, Quantity, Unit price
- **Source evidence:** `components/business/BusinessApp.tsx:142`

## Page: Built-in app: Suppliers (`/apps/[instanceId]/suppliers`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Suppliers
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Suppliers
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Suppliers
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Built-in app: Warehouses (`/apps/[instanceId]/warehouses`)

### Field: Find a part number

- **Application:** IntraForge
- **Page:** Built-in app: Warehouses
- **Type:** search
- **Purpose:** Search for a part number.
- **What user enters:** Text. Placeholder: "Search a part number, e.g. 04465-0K290".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Search, *
- **Source evidence:** `components/business/BusinessApp.tsx:142`

### Field: Search

- **Application:** IntraForge
- **Page:** Built-in app: Warehouses
- **Type:** search
- **Purpose:** Search box.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, *
- **Source evidence:** `components/business/RecordSection.tsx:187`

### Field: *

- **Application:** IntraForge
- **Page:** Built-in app: Warehouses
- **Type:** text
- **Purpose:** NOT CONFIRMED
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Find a part number, Search
- **Source evidence:** `components/business/RecordSection.tsx:283`

## Page: Bucket (files) (`/buckets/[bucketId]`)

### Field: Share with

- **Application:** IntraForge
- **Page:** Bucket (files) -> dialog "Share"
- **Type:** select (options: A specific member, A team, Everyone in this organization)
- **Purpose:** Member or team to share with.
- **What user enters:** Choose one option: A specific member, A team, Everyone in this organization.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Member, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:259`

### Field: Member

- **Application:** IntraForge
- **Page:** Bucket (files) -> dialog "Share"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:272`

### Field: Team

- **Application:** IntraForge
- **Page:** Bucket (files) -> dialog "Share"
- **Type:** select
- **Purpose:** A team of members.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Access level
- **Source evidence:** `components/ShareSection.tsx:288`

### Field: Access level

- **Application:** IntraForge
- **Page:** Bucket (files) -> dialog "Share"
- **Type:** select
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Team
- **Source evidence:** `components/ShareSection.tsx:303`

## Page: Connected database (`/connected-databases/[connectedDatabaseId]`)

### Field: Share with

- **Application:** IntraForge
- **Page:** Connected database -> dialog "Share"
- **Type:** select (options: A specific member, A team, Everyone in this organization)
- **Purpose:** Member or team to share with.
- **What user enters:** Choose one option: A specific member, A team, Everyone in this organization.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Member, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:259`

### Field: Member

- **Application:** IntraForge
- **Page:** Connected database -> dialog "Share"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:272`

### Field: Team

- **Application:** IntraForge
- **Page:** Connected database -> dialog "Share"
- **Type:** select
- **Purpose:** A team of members.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Access level
- **Source evidence:** `components/ShareSection.tsx:288`

### Field: Access level

- **Application:** IntraForge
- **Page:** Connected database -> dialog "Share"
- **Type:** select
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Team
- **Source evidence:** `components/ShareSection.tsx:303`

## Page: Dashboard (analytics) (`/dashboards/[dashboardId]`)

### Field: Table

- **Application:** IntraForge
- **Page:** Dashboard (analytics) -> dialog "Add widget"
- **Type:** select
- **Purpose:** A table in a database.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`
- **What happens after Save:** the "Add widget" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Operation, Title (optional), Display as
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:335`

### Field: Operation

- **Application:** IntraForge
- **Page:** Dashboard (analytics) -> dialog "Add widget"
- **Type:** select
- **Purpose:** Analytics: the statistics operation to run.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`
- **What happens after Save:** the "Add widget" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Table, Title (optional), Display as
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:345`

### Field: Title (optional)

- **Application:** IntraForge
- **Page:** Dashboard (analytics) -> dialog "Add widget"
- **Type:** text
- **Purpose:** Optional title.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`
- **What happens after Save:** the "Add widget" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Table, Operation, Display as
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:397`

### Field: Display as

- **Application:** IntraForge
- **Page:** Dashboard (analytics) -> dialog "Add widget"
- **Type:** select
- **Purpose:** How a value is shown.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`
- **What happens after Save:** the "Add widget" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Table, Operation, Title (optional)
- **Source evidence:** `app/(app)/dashboards/[dashboardId]/_client.tsx:406`

## Page: Environment (`/environments/[environmentId]`)

### Field: Key

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** Name of a variable / secret.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Value, Base URL this environment's application should call, Tenant database, Bucket, Allowed origins (comma-separated), URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:350`

### Field: Value

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** Value of a variable / secret (secrets are shown only once).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Base URL this environment's application should call, Tenant database, Bucket, Allowed origins (comma-separated), URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:360`

### Field: Base URL this environment's application should call

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** Address the application in this environment uses to reach IntraForge.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Tenant database, Bucket, Allowed origins (comma-separated), URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:424`

### Field: Tenant database

- **Application:** IntraForge
- **Page:** Environment
- **Type:** select (options: Select a database…)
- **Purpose:** A database of this organization.
- **What user enters:** Choose one option: Select a database….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Bucket, Allowed origins (comma-separated), URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:837`

### Field: Bucket

- **Application:** IntraForge
- **Page:** Environment
- **Type:** select (options: Select a bucket…)
- **Purpose:** A file storage area.
- **What user enters:** Choose one option: Select a bucket….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Tenant database, Allowed origins (comma-separated), URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:928`

### Field: Allowed origins (comma-separated)

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** Web addresses allowed to call the API from a browser (CORS).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Tenant database, Bucket, URL, Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:997`

### Field: URL

- **Application:** IntraForge
- **Page:** Environment
- **Type:** url
- **Purpose:** Address a webhook delivers events to.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Tenant database, Bucket, Allowed origins (comma-separated), Event types (comma-separated), Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1162`

### Field: Event types (comma-separated)

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** Which events a webhook sends.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Tenant database, Bucket, Allowed origins (comma-separated), URL, Name
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1174`

### Field: Name

- **Application:** IntraForge
- **Page:** Environment
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Key, Value, Base URL this environment's application should call, Tenant database, Bucket, Allowed origins (comma-separated), URL, Event types (comma-separated)
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1392`

### Field: Type … to confirm

- **Application:** IntraForge
- **Page:** Environment -> dialog "Delete "…"?"
- **Type:** text
- **Purpose:** Type the shown name to confirm a destructive action.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Delete "…"?" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** I understand this is a production environment and I want to permanently delete it.
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1480`

### Field: I understand this is a production environment and I want to permanently delete it.

- **Application:** IntraForge
- **Page:** Environment -> dialog "Delete "…"?"
- **Type:** checkbox
- **Purpose:** Required second confirmation to delete a production environment.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Delete "…"?" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type … to confirm
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1486`

## Page: Sign in (`/login`)

### Field: Email

- **Application:** IntraForge
- **Page:** Sign in
- **Type:** email
- **Purpose:** Email address (sign-in name for accounts).
- **What user enters:** An email address.
- **Required:** Yes
- **Validation:** required by the form; must be an email address; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Password, Authenticator code
- **Source evidence:** `app/login/page.tsx:80`

### Field: Password

- **Application:** IntraForge
- **Page:** Sign in
- **Type:** password
- **Purpose:** The account password.
- **What user enters:** A password.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Email, Authenticator code
- **Source evidence:** `app/login/page.tsx:92`

### Field: Authenticator code

- **Application:** IntraForge
- **Page:** Sign in
- **Type:** text
- **Purpose:** The 6-digit code from your authenticator app, when two-step sign-in is switched on.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Email, Password
- **Source evidence:** `app/login/page.tsx:106`

## Page: Organizations (`/orgs`)

### Field: Name

- **Application:** IntraForge
- **Page:** Organizations -> dialog "New organization"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** the "New organization" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/page.tsx:151`

## Page: Organization (`/orgs/[orgId]`)

### Field: Name

- **Application:** IntraForge
- **Page:** Organization -> dialog "New workspace"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New workspace" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:236`

### Field: Email of an existing user

- **Application:** IntraForge
- **Page:** Organization -> dialog "Add member"
- **Type:** email
- **Purpose:** Add an existing IntraForge user (by email) to the organization or team.
- **What user enters:** An email address.
- **Required:** Yes
- **Validation:** required by the form; must be an email address; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Add member" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:296`

## Page: Business app templates (`/orgs/[orgId]/app-templates`)

### Field: Name

- **Application:** IntraForge
- **Page:** Business app templates -> dialog "New app template"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "New app template" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Description
- **Source evidence:** `app/(app)/orgs/[orgId]/app-templates/_client.tsx:159`

### Field: Description

- **Application:** IntraForge
- **Page:** Business app templates -> dialog "New app template"
- **Type:** textarea
- **Purpose:** Longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`
- **What happens after Save:** the "New app template" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/orgs/[orgId]/app-templates/_client.tsx:170`

## Page: Audit log (organization) (`/orgs/[orgId]/audit`)

### Field: Resource type

- **Application:** IntraForge
- **Page:** Audit log (organization)
- **Type:** text
- **Purpose:** Kind of resource a permission or audit filter refers to.
- **What user enters:** Text. Placeholder: "e.g. bucket, file, organization".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Action, Result
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:132`

### Field: Action

- **Application:** IntraForge
- **Page:** Audit log (organization)
- **Type:** text
- **Purpose:** Audit filter: the action name.
- **What user enters:** Text. Placeholder: "e.g. file.upload".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Resource type, Result
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:143`

### Field: Result

- **Application:** IntraForge
- **Page:** Audit log (organization)
- **Type:** select (options: Any, Success, Denied, Error)
- **Purpose:** Audit filter: success, denied or error.
- **What user enters:** Choose one option: Any, Success, Denied, Error.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Resource type, Action
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:152`

## Page: Developer: Applications (`/orgs/[orgId]/developer/applications`)

### Field: Name

- **Application:** IntraForge
- **Page:** Developer: Applications -> dialog "New application"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "New application" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Description (optional)
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:168`

### Field: Description (optional)

- **Application:** IntraForge
- **Page:** Developer: Applications -> dialog "New application"
- **Type:** textarea
- **Purpose:** Optional longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "New application" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/_client.tsx:179`

## Page: Developer: Connect application (`/orgs/[orgId]/developer/applications/connect`)

### Field: Name

- **Application:** IntraForge
- **Page:** Developer: Connect application
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Description (optional), Read only, Read & write
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:273`

### Field: Description (optional)

- **Application:** IntraForge
- **Page:** Developer: Connect application
- **Type:** textarea
- **Purpose:** Optional longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name, Read only, Read & write
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:284`

### Field: Read only

- **Application:** IntraForge
- **Page:** Developer: Connect application
- **Type:** radio
- **Purpose:** Share option: the person may only look.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name, Description (optional), Read & write
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:328`

### Field: Read & write

- **Application:** IntraForge
- **Page:** Developer: Connect application
- **Type:** radio
- **Purpose:** Share option: the person may also change.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name, Description (optional), Read only
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx:337`

## Page: Developer: Environments (`/orgs/[orgId]/developer/environments`)

### Field: Application

- **Application:** IntraForge
- **Page:** Developer: Environments -> dialog "Create environment"
- **Type:** select
- **Purpose:** A registered application (program that connects to IntraForge).
- **What user enters:** Choose one option.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Create environment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:324`

### Field: Name

- **Application:** IntraForge
- **Page:** Developer: Environments -> dialog "Create environment"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Create environment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Application, Type
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:339`

### Field: Type

- **Application:** IntraForge
- **Page:** Developer: Environments -> dialog "Create environment"
- **Type:** select
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Create environment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Application, Name
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:350`

### Field: Type … to confirm

- **Application:** IntraForge
- **Page:** Developer: Environments -> dialog "Delete "…"?"
- **Type:** text
- **Purpose:** Type the shown name to confirm a destructive action.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Delete "…"?" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** I understand this is a production environment and I want to permanently delete it.
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:433`

### Field: I understand this is a production environment and I want to permanently delete it.

- **Application:** IntraForge
- **Page:** Developer: Environments -> dialog "Delete "…"?"
- **Type:** checkbox
- **Purpose:** Required second confirmation to delete a production environment.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Delete "…"?" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type … to confirm
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:444`

## Page: Teams (`/orgs/[orgId]/teams`)

### Field: Name

- **Application:** IntraForge
- **Page:** Teams -> dialog "New team"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** the "New team" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:217`

### Field: Member

- **Application:** IntraForge
- **Page:** Teams -> dialog "Add member to …"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`
- **What happens after Save:** the "Add member to …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/teams/_client.tsx:285`

## Page: Organizational units (`/orgs/[orgId]/units`)

### Field: Name

- **Application:** IntraForge
- **Page:** Organizational units
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Type
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:288`

### Field: Type

- **Application:** IntraForge
- **Page:** Organizational units
- **Type:** text
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:299`

### Field: Name

- **Application:** IntraForge
- **Page:** Organizational units -> dialog "Edit …"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Edit …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type, Parent
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:367`

### Field: Type

- **Application:** IntraForge
- **Page:** Organizational units -> dialog "Edit …"
- **Type:** text
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Edit …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Parent
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:371`

### Field: Parent

- **Application:** IntraForge
- **Page:** Organizational units -> dialog "Edit …"
- **Type:** select (options: None (root))
- **Purpose:** The unit this one sits under.
- **What user enters:** Choose one option: None (root).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Edit …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:375`

### Field: Add member

- **Application:** IntraForge
- **Page:** Organizational units -> dialog "Members of …"
- **Type:** select (options: Select a member...)
- **Purpose:** Add a member.
- **What user enters:** Choose one option: Select a member....
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`
- **What happens after Save:** the "Members of …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/units/_client.tsx:486`

## Page: Workspace (`/orgs/[orgId]/workspaces/[workspaceId]`)

### Field: Name

- **Application:** IntraForge
- **Page:** Workspace -> dialog "New project"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `permissions.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New project" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/_client.tsx:143`

## Page: Project (`/projects/[projectId]`)

### Field: Template

- **Application:** IntraForge
- **Page:** Project -> dialog "Install app"
- **Type:** select (options: Select a template…)
- **Purpose:** A business application template.
- **What user enters:** Choose one option: Select a template….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Install app" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Version, Name this installed app
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:393`

### Field: Version

- **Application:** IntraForge
- **Page:** Project -> dialog "Install app"
- **Type:** select
- **Purpose:** A template version.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Install app" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Template, Name this installed app
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:413`

### Field: Name this installed app

- **Application:** IntraForge
- **Page:** Project -> dialog "Install app"
- **Type:** text
- **Purpose:** A name for this copy of the built-in business app.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Install app" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Template, Version
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:431`

### Field: Name

- **Application:** IntraForge
- **Page:** Project -> dialog "New bucket"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New bucket" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:492`

### Field: Name

- **Application:** IntraForge
- **Page:** Project -> dialog "New database"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:552`

### Field: Name

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Host, Port, Database name, Username, Password, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:632`

### Field: Host

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** text
- **Purpose:** Connected database: server address of the external PostgreSQL.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Port, Database name, Username, Password, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:644`

### Field: Port

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** number
- **Purpose:** Connected database: port (usually 5432).
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Host, Database name, Username, Password, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:654`

### Field: Database name

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** text
- **Purpose:** Name of a new tenant database / connection's database.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Host, Port, Username, Password, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:665`

### Field: Username

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** text
- **Purpose:** Connected database: account name on the external server.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Host, Port, Database name, Password, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:676`

### Field: Password

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** password
- **Purpose:** The account password.
- **What user enters:** A password.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Host, Port, Database name, Username, SSL mode
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:686`

### Field: SSL mode

- **Application:** IntraForge
- **Page:** Project -> dialog "Connect a database"
- **Type:** select (options: Disable, Prefer, Require, Verify full)
- **Purpose:** Connected database: how the connection is encrypted.
- **What user enters:** Choose one option: Disable, Prefer, Require, Verify full.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Connect a database" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Host, Port, Database name, Username, Password
- **Source evidence:** `app/(app)/projects/[projectId]/_client.tsx:698`

## Page: Applications (built-in business apps) (`/projects/[projectId]/apps`)

### Field: Application name

- **Application:** IntraForge
- **Page:** Applications (built-in business apps) -> dialog "Install …"
- **Type:** text
- **Purpose:** Name of the application being registered.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`, `workspace.manage`
- **What happens after Save:** the "Install …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** I understand this is a … that has not completed production qualification, and I will keep my existing records alongside it.
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:340`

### Field: I understand this is a … that has not completed production qualification, and I will keep my existing records alongside it.

- **Application:** IntraForge
- **Page:** Applications (built-in business apps) -> dialog "Install …"
- **Type:** checkbox
- **Purpose:** Required acknowledgement before installing a built-in app that is not fully qualified.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`, `workspace.manage`
- **What happens after Save:** the "Install …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Application name
- **Source evidence:** `app/(app)/projects/[projectId]/apps/_client.tsx:349`

## Page: Create account (`/register`)

### Field: First name

- **Application:** IntraForge
- **Page:** Create account
- **Type:** text
- **Purpose:** The person's first name.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Email, Password
- **Source evidence:** `app/register/page.tsx:66`

### Field: Email

- **Application:** IntraForge
- **Page:** Create account
- **Type:** email
- **Purpose:** Email address (sign-in name for accounts).
- **What user enters:** An email address.
- **Required:** Yes
- **Validation:** required by the form; must be an email address; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** First name, Password
- **Source evidence:** `app/register/page.tsx:76`

### Field: Password

- **Application:** IntraForge
- **Page:** Create account
- **Type:** password
- **Purpose:** The account password.
- **What user enters:** A password.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: membership
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** First name, Email
- **Source evidence:** `app/register/page.tsx:88`

## Page: Application settings (`/service-apps/[appId]/settings`)

### Field: Name in Apps

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** text
- **Purpose:** The name the installed application shows in Apps.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Currency, Default tax rate (%), Quotations valid for (days), Invoices due after (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails., Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:125`

### Field: Currency

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** text
- **Purpose:** 3-letter currency code for the app's prices.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Default tax rate (%), Quotations valid for (days), Invoices due after (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails., Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:151`

### Field: Default tax rate (%)

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** number
- **Purpose:** Tax percentage for new documents.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Currency, Quotations valid for (days), Invoices due after (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails., Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:155`

### Field: Quotations valid for (days)

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** number
- **Purpose:** How long new quotations stay valid.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Currency, Default tax rate (%), Invoices due after (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails., Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:167`

### Field: Invoices due after (days)

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** number
- **Purpose:** After how many days invoices are due.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Currency, Default tax rate (%), Quotations valid for (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails., Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:171`

### Field: Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails.

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** checkbox
- **Purpose:** Remove an installed application AND delete its data -- a backup is taken first; nothing is deleted if the backup fails.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Currency, Default tax rate (%), Quotations valid for (days), Invoices due after (days), Type … to confirm
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:270`

### Field: Type … to confirm

- **Application:** IntraForge
- **Page:** Application settings
- **Type:** text
- **Purpose:** Type the shown name to confirm a destructive action.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Name in Apps, Currency, Default tax rate (%), Quotations valid for (days), Invoices due after (days), Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails.
- **Source evidence:** `app/(app)/service-apps/[appId]/settings/_client.tsx:290`

## Page: Table (`/tables/[tableId]`)

### Field: Name

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type, Max length, Precision, Scale, Nullable, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:377`

### Field: Type

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** select
- **Purpose:** The kind of item (field type, widget type...).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Max length, Precision, Scale, Nullable, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:389`

### Field: Max length

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** number
- **Purpose:** Maximum number of characters.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type, Precision, Scale, Nullable, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:404`

### Field: Precision

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** number
- **Purpose:** Total number of digits of a decimal number.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type, Max length, Scale, Nullable, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:417`

### Field: Scale

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** number
- **Purpose:** Digits after the decimal point.
- **What user enters:** A whole number.
- **Required:** No (form does not require it)
- **Validation:** number; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type, Max length, Precision, Nullable, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:427`

### Field: Nullable

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** checkbox
- **Purpose:** The value may be empty.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type, Max length, Precision, Scale, Unique
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:439`

### Field: Unique

- **Application:** IntraForge
- **Page:** Table -> dialog "Add column"
- **Type:** checkbox
- **Purpose:** No two records may have the same value.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`
- **What happens after Save:** the "Add column" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Type, Max length, Precision, Scale, Nullable
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:443`

## Page: Table analytics (`/tables/[tableId]/analytics`)

### Field: Operation

- **Application:** IntraForge
- **Page:** Table analytics
- **Type:** select
- **Purpose:** Analytics: the statistics operation to run.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/tables/[tableId]/analytics/_client.tsx:157`

## Page: CSV import (`/tables/[tableId]/import`)

### Field: Storage bucket

- **Application:** IntraForge
- **Page:** CSV import
- **Type:** select
- **Purpose:** The bucket an environment is bound to.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `dataset.import`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** New bucket name, Upload a CSV, or pick one already in this bucket
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:240`

### Field: New bucket name

- **Application:** IntraForge
- **Page:** CSV import
- **Type:** text
- **Purpose:** Name of a new file bucket.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `dataset.import`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Storage bucket, Upload a CSV, or pick one already in this bucket
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:268`

### Field: Upload a CSV, or pick one already in this bucket

- **Application:** IntraForge
- **Page:** CSV import
- **Type:** file
- **Purpose:** Choose the CSV file for the import.
- **What user enters:** Choose a file.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `dataset.import`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Storage bucket, New bucket name
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:285`

## Page: Database (`/tenant-databases/[dbId]`)

### Field: Name

- **Application:** IntraForge
- **Page:** Database -> dialog "New table"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New table" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:264`

### Field: Name

- **Application:** IntraForge
- **Page:** Database -> dialog "New dashboard"
- **Type:** text
- **Purpose:** The name of the item being created (organization, team, project, bucket, database, table...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "New dashboard" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/tenant-databases/[dbId]/_client.tsx:335`

### Field: Share with

- **Application:** IntraForge
- **Page:** Database -> dialog "Share"
- **Type:** select (options: A specific member, A team, Everyone in this organization)
- **Purpose:** Member or team to share with.
- **What user enters:** Choose one option: A specific member, A team, Everyone in this organization.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Member, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:259`

### Field: Member

- **Application:** IntraForge
- **Page:** Database -> dialog "Share"
- **Type:** select
- **Purpose:** The member to add or select.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Team, Access level
- **Source evidence:** `components/ShareSection.tsx:272`

### Field: Team

- **Application:** IntraForge
- **Page:** Database -> dialog "Share"
- **Type:** select
- **Purpose:** A team of members.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Access level
- **Source evidence:** `components/ShareSection.tsx:288`

### Field: Access level

- **Application:** IntraForge
- **Page:** Database -> dialog "Share"
- **Type:** select
- **Purpose:** Read only, or read & write, for a share.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: NOT CONFIRMED per field (server validates every request)
- **Permission:** server-checked; page area codes: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`
- **What happens after Save:** the "Share" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Share with, Member, Team
- **Source evidence:** `components/ShareSection.tsx:303`
