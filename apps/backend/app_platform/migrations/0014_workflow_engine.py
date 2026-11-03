"""Phase 5 -- Workflow engine (docs/implementation/APP_PLATFORM_PHASE5.md):
declarative WorkflowDefinition/WorkflowState/WorkflowTransition metadata
(never read by runtime_plan.py/runtime_build.py -- no tenant-schema
impact), plus the operational WorkflowTransitionAttempt/
WorkflowNotificationDelivery receipt rows that make "concurrent/replayed
transitions cannot duplicate effects" durable."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_platform', '0013_constraint_relationships'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowDefinition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('key', models.CharField(max_length=63)),
                ('source_definition_id', models.UUIDField(editable=False, null=True)),
                ('position', models.PositiveIntegerField(default=0)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflows', to='app_platform.modeldefinition')),
                ('state_field', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='workflows', to='app_platform.fielddefinition')),
            ],
            options={
                'ordering': ['position', 'created_at', 'id'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowState',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('key', models.CharField(max_length=63)),
                ('source_definition_id', models.UUIDField(editable=False, null=True)),
                ('position', models.PositiveIntegerField(default=0)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='states', to='app_platform.workflowdefinition')),
            ],
            options={
                'ordering': ['position', 'created_at', 'id'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowTransition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('key', models.CharField(max_length=63)),
                ('source_definition_id', models.UUIDField(editable=False, null=True)),
                ('position', models.PositiveIntegerField(default=0)),
                ('conditions', models.JSONField(blank=True, default=list)),
                ('field_actions', models.JSONField(blank=True, default=list)),
                ('requires_approval', models.BooleanField(default=False)),
                ('notify_url', models.TextField(blank=True)),
                ('from_state', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transitions_from', to='app_platform.workflowstate')),
                ('to_state', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transitions_to', to='app_platform.workflowstate')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transitions', to='app_platform.workflowdefinition')),
            ],
            options={
                'ordering': ['position', 'created_at', 'id'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowTransitionAttempt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('record_id', models.UUIDField()),
                ('idempotency_key', models.UUIDField(null=True)),
                ('request_fingerprint', models.CharField(max_length=64)),
                ('state_before', models.CharField(blank=True, max_length=63)),
                ('state_after', models.CharField(blank=True, max_length=63)),
                ('completed_at', models.DateTimeField(null=True)),
                ('last_error', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('transition', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attempts', to='app_platform.workflowtransition')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowNotificationDelivery',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.TextField()),
                ('delivered_at', models.DateTimeField(null=True)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('last_error', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attempt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='app_platform.workflowtransitionattempt')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='workflowdefinition',
            constraint=models.UniqueConstraint(fields=('model', 'key'), name='app_workflow_key_unique'),
        ),
        migrations.AddConstraint(
            model_name='workflowdefinition',
            constraint=models.UniqueConstraint(fields=('model', 'source_definition_id'), name='app_workflow_source_unique'),
        ),
        migrations.AddConstraint(
            model_name='workflowstate',
            constraint=models.UniqueConstraint(fields=('workflow', 'key'), name='app_workflow_state_key_unique'),
        ),
        migrations.AddConstraint(
            model_name='workflowstate',
            constraint=models.UniqueConstraint(fields=('workflow', 'source_definition_id'), name='app_workflow_state_source_unique'),
        ),
        migrations.AddConstraint(
            model_name='workflowtransition',
            constraint=models.UniqueConstraint(fields=('workflow', 'key'), name='app_workflow_transition_key_unique'),
        ),
        migrations.AddConstraint(
            model_name='workflowtransition',
            constraint=models.UniqueConstraint(fields=('workflow', 'source_definition_id'), name='app_workflow_transition_source_unique'),
        ),
        migrations.AddIndex(
            model_name='workflowtransitionattempt',
            index=models.Index(fields=['transition', 'record_id'], name='app_platfor_transit_e30756_idx'),
        ),
        migrations.AddConstraint(
            model_name='workflowtransitionattempt',
            constraint=models.UniqueConstraint(condition=models.Q(('idempotency_key__isnull', False)), fields=('record_id', 'idempotency_key'), name='app_workflow_attempt_idempotency_unique'),
        ),
    ]
