"""Phase 8 -- Documents (document management) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "Documents -- Library & Review" AppTemplate draft: 6 generic models
covering folders, categorization, versioning, tagging, and review,
built entirely from Phases 1-3's existing primitives, including a
self-referencing folder hierarchy (the same pattern HR's Employee.manager
and Spare Parts' PartNumber.supersedes already proved). No
industry-specific concept is added to `app_platform` itself.

Deliberately excluded, same discipline as the other Phase 8 templates:
- No new "file" field type. Actually storing a document's bytes reuses
  the existing generic per-record attachment capability (Phase 2's
  record-attachment API, backed by the same object-storage pipeline
  every other model already uses) rather than inventing a second file
  concept scoped to this one template.
- No enum/status type -- `status`/`decision` stay free text.
- No calculated `version` auto-increment -- the caller writes both the
  Document's own `version` field and a corresponding `DocumentVersion`
  row; the platform has no trigger/computed-column concept.
"""

import uuid

from ._helpers import _field, _model, _relationship


def documents_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in ("document_category", "document_folder", "document", "document_version", "tag", "document_review")
    }

    document_category = _model(
        ids["document_category"], "document_category", "Document Category",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    document_folder = _model(
        ids["document_folder"], "document_folder", "Folder",
        [_field("name", "Name", "text", required=True)],
    )
    document = _model(
        ids["document"], "document", "Document",
        [
            _field("title", "Title", "text", required=True),
            _field("description", "Description", "text"),
            _field("status", "Status", "text", required=True, default_value="draft"),
            _field("version", "Version", "integer", default_value=1),
            _field("is_public", "Is Public", "boolean", default_value=False),
        ],
    )
    version_number_id, version_number_field = _field("version_number", "Version Number", "integer", required=True)
    document_version = _model(
        ids["document_version"], "document_version", "Document Version",
        [
            (version_number_id, version_number_field),
            _field("notes", "Notes", "text"),
            _field("created_at", "Created At", "datetime"),
        ],
    )
    tag = _model(ids["tag"], "tag", "Tag", [_field("name", "Name", "text", required=True, unique=True)])
    document_review = _model(
        ids["document_review"], "document_review", "Document Review",
        [
            _field("reviewer_name", "Reviewer Name", "text"),
            _field("decision", "Decision", "text", required=True, default_value="pending"),
            _field("reviewed_at", "Reviewed At", "datetime"),
            _field("comments", "Comments", "text"),
        ],
    )

    document_version_document_rel = _relationship(
        "document_version_document", "Document", ids["document_version"], ids["document"]
    )
    # One version row per (Document, Version Number).
    document_version["constraints"] = [
        {
            "key": "document_version_number_unique",
            "label": "One Document Version per Document and Version Number",
            "field_ids": [version_number_id],
            "relationship_ids": [document_version_document_rel["id"]],
        }
    ]

    relationships = [
        # Self-referencing, nullable on delete -- removing a parent folder
        # should not be blocked by its children, just orphan them to the
        # library root.
        _relationship(
            "parent_folder", "Parent Folder", ids["document_folder"], ids["document_folder"],
            deletion_policy="set_null",
        ),
        _relationship("document_category", "Category", ids["document"], ids["document_category"]),
        _relationship(
            "document_folder", "Folder", ids["document"], ids["document_folder"], deletion_policy="set_null"
        ),
        document_version_document_rel,
        _relationship("document_review_document", "Document", ids["document_review"], ids["document"]),
        # Native many-to-many: a document can carry several tags.
        _relationship("tags", "Tags", ids["document"], ids["tag"], kind="many_to_many"),
    ]

    return {
        "schema_version": 1,
        "models": [document_category, document_folder, document, document_version, tag, document_review],
        "relationships": relationships,
    }
