"""Phase 8 -- School (education management) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "School -- Enrollment & Records" AppTemplate draft: 11 generic models
covering academic structure, enrollment, attendance, grading, and billing,
built entirely from Phases 1-3/6's existing primitives. No industry-
specific concept is added to `app_platform` itself.

Deliberately excluded (same discipline as the Phase 4 Spare Parts
template, documented in APP_PLATFORM_PHASE8.md):
- No calculated GPA/attendance-percentage fields -- the platform has no
  formula/computed-column concept.
- No enum/status type -- `status` fields stay free text.
- No cross-request atomicity -- e.g. posting a grade and updating a
  report card stays separate record-CRUD calls.
"""

import uuid

from ._helpers import _field, _model, _relationship


def school_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "student", "guardian", "teacher", "department", "course", "term",
            "class_section", "enrollment", "attendance_record", "grade", "invoice",
        )
    }

    student = _model(
        ids["student"], "student", "Student",
        [
            _field("name", "Name", "text", required=True),
            _field("email", "Email", "text"),
            _field("date_of_birth", "Date of Birth", "date"),
            _field("enrollment_date", "Enrollment Date", "date"),
            _field("is_active", "Is Active", "boolean", default_value=True),
        ],
    )
    guardian = _model(
        ids["guardian"], "guardian", "Guardian",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
            _field("contact_phone", "Contact Phone", "text"),
        ],
    )
    teacher = _model(
        ids["teacher"], "teacher", "Teacher",
        [
            _field("name", "Name", "text", required=True),
            _field("email", "Email", "text"),
            _field("hire_date", "Hire Date", "date"),
        ],
    )
    department = _model(
        ids["department"], "department", "Department",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    course = _model(
        ids["course"], "course", "Course",
        [
            _field("title", "Title", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
            _field("credits", "Credits", "integer"),
            _field("description", "Description", "text"),
        ],
    )
    term = _model(
        ids["term"], "term", "Term",
        [
            _field("name", "Name", "text", required=True),
            _field("start_date", "Start Date", "date"),
            _field("end_date", "End Date", "date"),
        ],
    )
    class_section = _model(
        ids["class_section"], "class_section", "Class Section",
        [
            _field("section_code", "Section Code", "text", required=True),
            _field("capacity", "Capacity", "integer"),
        ],
    )
    enrollment = _model(
        ids["enrollment"], "enrollment", "Enrollment",
        [
            _field("enrolled_at", "Enrolled At", "datetime"),
            _field("status", "Status", "text", required=True, default_value="enrolled"),
        ],
    )
    attendance_record = _model(
        ids["attendance_record"], "attendance_record", "Attendance Record",
        [
            _field("date", "Date", "date", required=True),
            _field("present", "Present", "boolean", default_value=True),
        ],
    )
    grade = _model(
        ids["grade"], "grade", "Grade",
        [
            _field("score", "Score", "decimal"),
            _field("grade_letter", "Grade Letter", "text"),
        ],
    )
    invoice = _model(
        ids["invoice"], "invoice", "Invoice",
        [
            _field("invoice_number", "Invoice Number", "text", required=True, unique=True),
            _field("amount_due", "Amount Due", "decimal", default_value="0"),
            _field("due_date", "Due Date", "date"),
            _field("status", "Status", "text", required=True, default_value="unpaid"),
        ],
    )

    enrollment_student_rel = _relationship("enrollment_student", "Student", ids["enrollment"], ids["student"])
    enrollment_class_section_rel = _relationship(
        "enrollment_class_section", "Class Section", ids["enrollment"], ids["class_section"]
    )
    # One enrollment per (student, class_section) -- a composite constraint
    # over two relationships, the exact capability Phase 4 closed generically.
    enrollment["constraints"] = [
        {
            "key": "student_class_section_unique",
            "label": "One enrollment per Student and Class Section",
            "field_ids": [],
            "relationship_ids": [enrollment_student_rel["id"], enrollment_class_section_rel["id"]],
        }
    ]

    relationships = [
        _relationship("course_department", "Department", ids["course"], ids["department"]),
        _relationship("class_section_course", "Course", ids["class_section"], ids["course"]),
        _relationship("class_section_term", "Term", ids["class_section"], ids["term"]),
        _relationship("class_section_teacher", "Teacher", ids["class_section"], ids["teacher"]),
        enrollment_student_rel,
        enrollment_class_section_rel,
        _relationship("attendance_enrollment", "Enrollment", ids["attendance_record"], ids["enrollment"]),
        _relationship("grade_enrollment", "Enrollment", ids["grade"], ids["enrollment"]),
        _relationship("invoice_student", "Student", ids["invoice"], ids["student"]),
        # Native many-to-many: a student can have several guardians.
        _relationship("guardians", "Guardians", ids["student"], ids["guardian"], kind="many_to_many"),
    ]

    return {
        "schema_version": 1,
        "models": [
            student, guardian, teacher, department, course, term,
            class_section, enrollment, attendance_record, grade, invoice,
        ],
        "relationships": relationships,
    }
