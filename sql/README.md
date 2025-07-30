# Platform Coordination Service Database

## Quick Start

1. Start the PostgreSQL container:
```bash
docker-compose -f docker-compose.dev.yml up -d postgres
```

2. Wait for PostgreSQL to be ready:
```bash
docker-compose -f docker-compose.dev.yml exec postgres pg_isready
```

3. The database schema will be automatically created from `sql/init/001_create_service_registry.sql`

4. (Optional) Start pgAdmin for database management:
```bash
docker-compose -f docker-compose.dev.yml --profile tools up -d pgadmin
```
Access pgAdmin at http://localhost:5050

## Database Schema

### Tables

#### `services`
Main table storing service registrations:
- `id`: UUID primary key
- `name`: Service name
- `type`: Service type (api, worker, scheduler, etc.)
- `host`: Service hostname/IP
- `port`: Service port
- `status`: Current service status
- `metadata`: JSONB field for flexible metadata
- `version`: Optimistic locking version

#### `service_events`
Audit trail for service lifecycle events:
- Tracks all status changes
- Stores event metadata
- Enables historical analysis

### Features

1. **Thread-Safe Operations**: All operations use PostgreSQL's ACID guarantees
2. **Optimistic Locking**: Version field prevents lost updates
3. **Audit Trail**: Automatic event logging for compliance
4. **Flexible Metadata**: JSONB field for extensibility
5. **Performance Indexes**: Optimized for common queries

## Connection Details

- **Host**: localhost
- **Port**: 5432
- **Database**: platform_coordination
- **User**: coordination_user
- **Password**: coordination_dev_password (dev only!)

## Migrations

Future migrations should be added as numbered SQL files:
- `002_add_service_dependencies.sql`
- `003_add_rate_limiting.sql`
- etc.

## Production Considerations

1. Use proper secrets management for passwords
2. Enable SSL/TLS connections
3. Configure connection pooling
4. Set up regular backups
5. Monitor query performance