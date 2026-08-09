from .models import AuditEvent


def record(
    *,
    actor,
    organization_id,
    action: str,
    resource_type: str = "",
    resource_id="",
    request_id: str = "",
    result: str = AuditEvent.Result.SUCCESS,
    context: dict | None = None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor if actor is not None and getattr(actor, "is_authenticated", False) else None,
        organization_id=organization_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        request_id=request_id,
        result=result,
        context=context or {},
    )
