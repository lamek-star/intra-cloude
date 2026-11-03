param([Parameter(Mandatory)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputPath) { throw 'Refusing to overwrite an existing environment file.' }
function New-Secret { [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) }
$databaseSecret = New-Secret
$storageSecret = New-Secret
$config = @{
    DJANGO_SETTINGS_MODULE = 'config.settings.prod'
    SECRET_KEY = New-Secret
    CREDENTIAL_ENCRYPTION_KEY = New-Secret
    POSTGRES_DB = 'qualification'
    POSTGRES_USER = 'qualification'
    POSTGRES_PASSWORD = $databaseSecret
    CONTROL_DB_NAME = 'qualification'
    CONTROL_DB_USER = 'qualification'
    CONTROL_DB_PASSWORD = $databaseSecret
    CONTROL_DB_HOST = 'postgres-control'
    TENANT_DB_NAME = 'qualification'
    TENANT_DB_USER = 'qualification'
    TENANT_DB_PASSWORD = $databaseSecret
    TENANT_DB_HOST = 'postgres-tenant'
    REDIS_URL = 'redis://valkey:6379/0'
    CACHE_URL = 'redis://valkey:6379/1'
    OBJECT_STORAGE_ENDPOINT = 'http://object-storage:9000'
    OBJECT_STORAGE_ROOT_USER = 'qualification'
    OBJECT_STORAGE_ROOT_PASSWORD = $storageSecret
    OBJECT_STORAGE_BUCKET_PREFIX = 'qualification'
    MINIO_ROOT_USER = 'qualification'
    MINIO_ROOT_PASSWORD = $storageSecret
    ALLOWED_HOSTS = 'localhost,127.0.0.1,backend,testserver'
    CSRF_TRUSTED_ORIGINS = 'https://localhost:8444'
    OIDC_ISSUER = 'https://localhost:8444'
    BACKUP_DIR = '/backups'
    BACKUP_ENCRYPTION_KEY = New-Secret
}
$config.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Key)=$($_.Value)" } |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
Write-Output 'Created disposable qualification configuration; keep this file private.'
