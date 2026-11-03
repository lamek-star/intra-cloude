# IntraForge -- table reference (Level 1)

Every table found in the code with every column. Formulas are stated only where the code implements them.

## Page: Installed business app (definition) (`/app-instances/[instanceId]`)

### Table 1 on Installed business app (definition)

- **Columns:** From | To | When
- **Search / filter:** Item; item; Group; group; status filter: danger, info, success, warning
- **Source evidence:** `app/(app)/app-instances/[instanceId]/_client.tsx:781`

  - **From:** From.
  - **To:** To.
  - **When:** When it happened.

### Table 2 on Installed business app (definition)

- **Columns:** Shared with | Level | Expires | Actions
- **Search / filter:** Item; item; Group; group; status filter: danger, info, success, warning
- **Source evidence:** `components/ShareSection.tsx:148`

  - **Shared with:** Member or team it is shared with.
  - **Level:** Access level (read / write).
  - **Expires:** When it stops working.
  - **Actions:** Row actions.

## Page: Model records (`/app-models/[modelId]`)

### Table 1 on Model records

- **Columns:** Actions
- **Search / filter:** Search text fields…; Name; name; Lifecycle; lifecycle; Draft; draft; Submit; submit; https://...; Unique combination; unique_combination; status filter: default, info, warning
- **Source evidence:** `app/(app)/app-models/[modelId]/_client.tsx:492`

  - **Actions:** Row actions.

### Table 2 on Model records

- **Columns:** Shared with | Level | Expires | Actions
- **Search / filter:** Search text fields…; Name; name; Lifecycle; lifecycle; Draft; draft; Submit; submit; https://...; Unique combination; unique_combination; status filter: default, info, warning
- **Source evidence:** `components/ShareSection.tsx:148`

  - **Shared with:** Member or team it is shared with.
  - **Level:** Access level (read / write).
  - **Expires:** When it stops working.
  - **Actions:** Row actions.

## Page: Application (API client) (`/applications/[applicationId]`)

### Table 1 on Application (API client)

- **Columns:** Credential | Status | Created | Last used | Actions
- **Search / filter:** storage.files.read; bucket; the bucket's UUID; Production; status filter: danger
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:310`

  - **Credential:** Credential (token) identifier.
  - **Status:** Current status.
  - **Created:** When it was created.
  - **Last used:** When it was last used.
  - **Actions:** Row actions.

### Table 2 on Application (API client)

- **Columns:** Permission | Resource | Expires | Granted
- **Search / filter:** storage.files.read; bucket; the bucket's UUID; Production; status filter: danger
- **Source evidence:** `app/(app)/applications/[applicationId]/_client.tsx:395`

  - **Permission:** Permission (capability) code.
  - **Resource:** The item the event or grant refers to.
  - **Expires:** When it stops working.
  - **Granted:** When it was granted.

## Page: Built-in app: Stock (`/apps/[instanceId]/inventory`)

### Table 1 on Built-in app: Stock

- **Columns:** Product | Warehouse | On hand
- **Search / filter:** Search a part number, e.g. 04465-0K290
- **Source evidence:** `components/business/Inventory.tsx:87`

  - **Product:** Product.
  - **Warehouse:** Warehouse.
  - **On hand:** Units in stock.

### Table 2 on Built-in app: Stock

- **Columns:** When | Product | Warehouse | Change | Type | Reference
- **Search / filter:** Search a part number, e.g. 04465-0K290
- **Source evidence:** `components/business/Inventory.tsx:158`

  - **When:** When it happened.
  - **Product:** Product.
  - **Warehouse:** Warehouse.
  - **Change:** What changed.
  - **Type:** Kind of item.
  - **Reference:** Reference.

## Page: Built-in app: Part numbers (`/apps/[instanceId]/part-numbers`)

### Table 1 on Built-in app: Part numbers

- **Columns:** Part number | Source | Product
- **Search / filter:** Search a part number, e.g. 044650K290; e.g. 04465-0K290; e.g. OEM, aftermarket, supplier; Search a part number, e.g. 04465-0K290; Type a product name or part number; status filter: success
- **Source evidence:** `components/business/PartNumbers.tsx:141`

  - **Part number:** Part number.
  - **Source:** Source.
  - **Product:** Product.

## Page: Built-in app: Product (`/apps/[instanceId]/products/[partId]`)

### Table 1 on Built-in app: Product

- **Columns:** Part number | Source
- **Search / filter:** Search a part number, e.g. 04465-0K290; Search a part number, e.g. 044650K290; e.g. 04465-0K290; e.g. OEM, aftermarket, supplier; Type a product name or part number; status filter: success
- **Source evidence:** `components/business/ProductDetail.tsx:157`

  - **Part number:** Part number.
  - **Source:** Source.

### Table 2 on Built-in app: Product

- **Columns:** Product | Warehouse | On hand
- **Search / filter:** Search a part number, e.g. 04465-0K290; Search a part number, e.g. 044650K290; e.g. 04465-0K290; e.g. OEM, aftermarket, supplier; Type a product name or part number; status filter: success
- **Source evidence:** `components/business/Inventory.tsx:87`

  - **Product:** Product.
  - **Warehouse:** Warehouse.
  - **On hand:** Units in stock.

### Table 3 on Built-in app: Product

- **Columns:** When | Product | Warehouse | Change | Type | Reference
- **Search / filter:** Search a part number, e.g. 04465-0K290; Search a part number, e.g. 044650K290; e.g. 04465-0K290; e.g. OEM, aftermarket, supplier; Type a product name or part number; status filter: success
- **Source evidence:** `components/business/Inventory.tsx:158`

  - **When:** When it happened.
  - **Product:** Product.
  - **Warehouse:** Warehouse.
  - **Change:** What changed.
  - **Type:** Kind of item.
  - **Reference:** Reference.

### Table 4 on Built-in app: Product

- **Columns:** Part number | Source | Product
- **Search / filter:** Search a part number, e.g. 04465-0K290; Search a part number, e.g. 044650K290; e.g. 04465-0K290; e.g. OEM, aftermarket, supplier; Type a product name or part number; status filter: success
- **Source evidence:** `components/business/PartNumbers.tsx:141`

  - **Part number:** Part number.
  - **Source:** Source.
  - **Product:** Product.

## Page: Built-in app: Sales (`/apps/[instanceId]/sales`)

### Table 1 on Built-in app: Sales

- **Columns:** Date | Customer | Total | Status | Open
- **Search / filter:** Search a part number, e.g. 04465-0K290; status filter: success
- **Source evidence:** `components/business/Sales.tsx:64`

  - **Date:** Date.
  - **Customer:** Customer.
  - **Total:** Total.
  - **Status:** Current status.
  - **Open:** Open link.

## Page: Built-in app: Sale (`/apps/[instanceId]/sales/[orderId]`)

### Table 1 on Built-in app: Sale

- **Columns:** Product | Quantity | Unit price | Line total | When | Warehouse | Change | Type
- **Search / filter:** Search a part number, e.g. 04465-0K290; status filter: success, warning
- **Source evidence:** `components/business/SalesDocument.tsx:131`

  - **Product:** Product.
  - **Quantity:** Quantity.
  - **Unit price:** Price per unit.
  - **Line total:** Quantity x unit price.
  - **When:** When it happened.
  - **Warehouse:** Warehouse.
  - **Change:** What changed.
  - **Type:** Kind of item.

## Page: Bucket (files) (`/buckets/[bucketId]`)

### Table 1 on Bucket (files)

- **Columns:** Name | Size | Type | Uploaded | Actions
- **Search / filter:** Search files…
- **Source evidence:** `app/(app)/buckets/[bucketId]/_client.tsx:188`

  - **Name:** Name.
  - **Size:** File size.
  - **Type:** Kind of item.
  - **Uploaded:** When the file was uploaded.
  - **Actions:** Row actions.

### Table 2 on Bucket (files)

- **Columns:** Shared with | Level | Expires | Actions
- **Search / filter:** Search files…
- **Source evidence:** `components/ShareSection.tsx:148`

  - **Shared with:** Member or team it is shared with.
  - **Level:** Access level (read / write).
  - **Expires:** When it stops working.
  - **Actions:** Row actions.

## Page: Connected database (`/connected-databases/[connectedDatabaseId]`)

### Table 1 on Connected database

- **Columns:** Shared with | Level | Expires | Actions
- **Search / filter:** none on this page
- **Source evidence:** `components/ShareSection.tsx:148`

  - **Shared with:** Member or team it is shared with.
  - **Level:** Access level (read / write).
  - **Expires:** When it stops working.
  - **Actions:** Row actions.

## Page: Dashboard (analytics) (`/dashboards/[dashboardId]`)

### Table 1 on Dashboard (analytics)

- **Columns:** Field | Value
- **Search / filter:** none on this page; status filter: info
- **Source evidence:** `components/AnalyticsResult.tsx:81`

  - **Field:** Field.
  - **Value:** Variable value (secrets are never shown again).

## Page: Environment (`/environments/[environmentId]`)

### Table 1 on Environment

- **Columns:** Key | Value | Actions
- **Search / filter:** LOG_LEVEL; debug; https://staging.example.com; STRIPE_API_KEY; https://staging.example.com, https://staging-preview.example.com; https://hooks.example.com/staging; file.uploaded, database.row.created; status filter: danger
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:324`

  - **Key:** Variable / secret name.
  - **Value:** Variable value (secrets are never shown again).
  - **Actions:** Row actions.

### Table 2 on Environment

- **Columns:** Key | Created | Rotated | Actions
- **Search / filter:** LOG_LEVEL; debug; https://staging.example.com; STRIPE_API_KEY; https://staging.example.com, https://staging-preview.example.com; https://hooks.example.com/staging; file.uploaded, database.row.created; status filter: danger
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:515`

  - **Key:** Variable / secret name.
  - **Created:** When it was created.
  - **Rotated:** When it was last rotated.
  - **Actions:** Row actions.

### Table 3 on Environment

- **Columns:** Credential | Status | Created | Last used | Actions
- **Search / filter:** LOG_LEVEL; debug; https://staging.example.com; STRIPE_API_KEY; https://staging.example.com, https://staging-preview.example.com; https://hooks.example.com/staging; file.uploaded, database.row.created; status filter: danger
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:722`

  - **Credential:** Credential (token) identifier.
  - **Status:** Current status.
  - **Created:** When it was created.
  - **Last used:** When it was last used.
  - **Actions:** Row actions.

### Table 4 on Environment

- **Columns:** URL | Events | Status | Actions
- **Search / filter:** LOG_LEVEL; debug; https://staging.example.com; STRIPE_API_KEY; https://staging.example.com, https://staging-preview.example.com; https://hooks.example.com/staging; file.uploaded, database.row.created; status filter: danger
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1078`

  - **URL:** Delivery address.
  - **Events:** Event types delivered.
  - **Status:** Current status.
  - **Actions:** Row actions.

### Table 5 on Environment

- **Columns:** Time | Action | Result
- **Search / filter:** LOG_LEVEL; debug; https://staging.example.com; STRIPE_API_KEY; https://staging.example.com, https://staging-preview.example.com; https://hooks.example.com/staging; file.uploaded, database.row.created; status filter: danger
- **Source evidence:** `app/(app)/environments/[environmentId]/_client.tsx:1240`

  - **Time:** When it happened.
  - **Action:** The audited action (for example storage.file.upload).
  - **Result:** success, denied or error.

## Page: Organization (`/orgs/[orgId]`)

### Table 1 on Organization

- **Columns:** Email | Name | Status | Team
- **Search / filter:** Engineering; teammate@example.com
- **Source evidence:** `app/(app)/orgs/[orgId]/_client.tsx:147`

  - **Email:** Email.
  - **Name:** Name.
  - **Status:** Current status.
  - **Team:** Team.

## Page: Audit log (organization) (`/orgs/[orgId]/audit`)

### Table 1 on Audit log (organization)

- **Columns:** Time | Action | Resource | Result | Request ID
- **Search / filter:** e.g. bucket, file, organization; e.g. file.upload
- **Source evidence:** `app/(app)/orgs/[orgId]/audit/_client.tsx:201`

  - **Time:** When it happened.
  - **Action:** The audited action (for example storage.file.upload).
  - **Resource:** The item the event or grant refers to.
  - **Result:** success, denied or error.
  - **Request ID:** Identifier of the request.

## Page: Developer: Environments (`/orgs/[orgId]/developer/environments`)

### Table 1 on Developer: Environments

- **Columns:** Name | Application | Type | Status | Database | Storage | API credentials | Created | Last activity | Actions
- **Search / filter:** Production; status filter: default, success
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/environments/_client.tsx:174`

  - **Name:** Name.
  - **Application:** Registered application.
  - **Type:** Kind of item.
  - **Status:** Current status.
  - **Database:** Database.
  - **Storage:** Bucket bound to the environment.
  - **API credentials:** Number of credentials.
  - **Created:** When it was created.
  - **Last activity:** Latest activity.
  - **Actions:** Row actions.

## Page: Developer: Webhooks (`/orgs/[orgId]/developer/webhooks`)

### Table 1 on Developer: Webhooks

- **Columns:** Environment | Application | Database bound | Webhooks | Manage | Event type | Fires when
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/orgs/[orgId]/developer/webhooks/_client.tsx:125`

  - **Environment:** Development / Staging / Production.
  - **Application:** Registered application.
  - **Database bound:** Tenant database bound to the environment.
  - **Webhooks:** Number of webhooks.
  - **Manage:** Management actions.
  - **Event type:** Event type.
  - **Fires when:** What triggers the webhook.

## Page: Table (`/tables/[tableId]`)

### Table 1 on Table

- **Columns:** Actions
- **Search / filter:** Search text columns…; email; {}
- **Source evidence:** `app/(app)/tables/[tableId]/_client.tsx:206`

  - **Actions:** Row actions.

## Page: Table analytics (`/tables/[tableId]/analytics`)

### Table 1 on Table analytics

- **Columns:** Field | Value
- **Search / filter:** none on this page; status filter: info
- **Source evidence:** `components/AnalyticsResult.tsx:81`

  - **Field:** Field.
  - **Value:** Variable value (secrets are never shown again).

## Page: CSV import (`/tables/[tableId]/import`)

### Table 1 on CSV import

- **Columns:** File | Size | Action
- **Search / filter:** imports
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:303`

  - **File:** File.
  - **Size:** File size.
  - **Action:** The audited action (for example storage.file.upload).

### Table 2 on CSV import

- **Columns:** CSV column | Inferred type | Sample values | Import into
- **Search / filter:** imports
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:348`

  - **CSV column:** Column in the CSV file.
  - **Inferred type:** Data type detected from the CSV values.
  - **Sample values:** Example values from the file.
  - **Import into:** Table column the CSV column is imported into.

### Table 3 on CSV import

- **Columns:** Row | Reason
- **Search / filter:** imports
- **Source evidence:** `app/(app)/tables/[tableId]/import/_client.tsx:444`

  - **Row:** Row number.
  - **Reason:** Why the row was rejected.

## Page: Database (`/tenant-databases/[dbId]`)

### Table 1 on Database

- **Columns:** Shared with | Level | Expires | Actions
- **Search / filter:** contacts; Orders overview
- **Source evidence:** `components/ShareSection.tsx:148`

  - **Shared with:** Member or team it is shared with.
  - **Level:** Access level (read / write).
  - **Expires:** When it stops working.
  - **Actions:** Row actions.
