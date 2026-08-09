import uuid

from django.conf import settings
from django.db import models


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="workspaces"
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="workspaces_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_workspace_name_per_org"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="projects_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "name"], name="unique_project_name_per_workspace"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.workspace} / {self.name}"

    @property
    def organization_id(self):
        return self.workspace.organization_id
