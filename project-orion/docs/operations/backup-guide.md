# ORION Backup Guide

## Overview

ORION implements automated backup for PostgreSQL and Redis with encryption, compression, remote storage, and retention rotation.

## Backup Strategy

| Component | Type | Schedule | Retention | Storage |
|-----------|------|----------|-----------|---------|
| PostgreSQL Full | Custom format dump | Daily 02:00 UTC | 7 daily / 4 weekly / 3 monthly | Local + S3 |
| PostgreSQL WAL | WAL archiving | Continuous | 14 days | Local + S3 |
| Redis RDB | RDB snapshot | Hourly | 7 daily / 4 weekly | Local + S3 |

## Scripts (backup/)

| Script | Purpose |
|--------|---------|
| `database-backup.sh` | PostgreSQL full/incremental dump |
| `redis-backup.sh` | Redis RDB snapshot |
| `restore-database.sh` | PostgreSQL restore with verification |
| `restore-redis.sh` | Redis restore with RDB placement |
| `retention-policy.sh` | Retention rotation and cleanup |
| `backup-config.yml` | Central configuration |

## Usage

```bash
# Full database backup
./backup/database-backup.sh full

# Redis backup
./backup/redis-backup.sh

# Apply retention policy
./backup/retention-policy.sh

# Restore database
./backup/restore-database.sh /var/backups/orion/database/2024-01-01/orion-db-full-*.dump.gz
```

## Encryption

AES-256-CBC via BACKUP_ENCRYPTION_KEY:
```bash
export BACKUP_ENCRYPTION_KEY="$(openssl rand -hex 32)"
```

## Remote Storage

S3-compatible via BACKUP_S3_BUCKET, BACKUP_S3_ENDPOINT, BACKUP_S3_REGION.

## Monitoring

Backup metrics exposed on port 9121:
- orion_backup_database_last_success_timestamp
- orion_backup_database_duration_seconds
- orion_backup_redis_last_success_timestamp
- orion_backup_errors_total
