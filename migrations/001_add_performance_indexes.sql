-- Performance Indexes Migration for Platform Coordination Service
-- Migration: 001_add_performance_indexes
-- Purpose: Add optimized indexes for common query patterns in service registry
-- PostgreSQL 17.5

-- ==============================================================================
-- PERFORMANCE INDEXES FOR SERVICES TABLE
-- ==============================================================================

-- 1. Composite index for frequent lookup patterns (name, host, port)
-- Optimizes queries that look up services by their network endpoint
-- Usage: SELECT * FROM services WHERE name = ? AND host = ? AND port = ?
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_name_host_port 
ON services(name, host, port);

-- 2. Composite index for type and status filtering
-- Optimizes queries that filter services by type and status together
-- Usage: SELECT * FROM services WHERE type = 'api' AND status = 'healthy'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_type_status 
ON services(type, status);

-- 3. Enhanced GIN index for metadata JSON queries with specific tags extraction
-- Optimizes queries on service metadata, particularly for tags
-- Usage: SELECT * FROM services WHERE service_metadata->'tags' ? 'production'
-- Note: Changed from 'metadata' to 'service_metadata' to match actual schema
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_metadata_tags 
ON services USING GIN((service_metadata->'tags'));

-- 4. Composite index for health check operations
-- Optimizes queries for health checking and service monitoring
-- Usage: SELECT * FROM services WHERE status != 'stopped' AND last_health_check_at < ?
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_health_monitoring 
ON services(status, last_health_check_at) 
WHERE status NOT IN ('stopped', 'unknown');

-- 5. Partial index for active services (optimization for common filter)
-- Optimizes queries that frequently filter out stopped/unknown services
-- Usage: SELECT * FROM services WHERE status NOT IN ('stopped', 'unknown')
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_active_status 
ON services(last_seen_at DESC, type, status) 
WHERE status NOT IN ('stopped', 'unknown');

-- 6. Index for version-based optimistic locking queries
-- Optimizes concurrent update operations with version checking
-- Usage: UPDATE services SET ... WHERE id = ? AND version = ?
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_id_version 
ON services(id, version);

-- ==============================================================================
-- PERFORMANCE INDEXES FOR SERVICE_EVENTS TABLE
-- ==============================================================================

-- 7. Enhanced composite index for service events with time-based queries
-- Optimizes event queries by service with time ordering (most common pattern)
-- Usage: SELECT * FROM service_events WHERE service_id = ? ORDER BY created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_service_events_service_time 
ON service_events(service_id, created_at DESC);

-- 8. Index for event type filtering with time ordering
-- Optimizes queries that filter events by type across all services
-- Usage: SELECT * FROM service_events WHERE event_type = 'status_change' ORDER BY created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_service_events_type_time 
ON service_events(event_type, created_at DESC);

-- 9. Partial index for recent events (last 7 days)
-- Optimizes queries on recent events, which are accessed most frequently
-- Usage: SELECT * FROM service_events WHERE created_at > NOW() - INTERVAL '7 days'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_service_events_recent 
ON service_events(created_at DESC, service_id, event_type) 
WHERE created_at > (CURRENT_TIMESTAMP - INTERVAL '7 days');

-- 10. GIN index for event data JSON queries
-- Optimizes queries on event data for analytics and debugging
-- Usage: SELECT * FROM service_events WHERE event_data @> '{"status": "healthy"}'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_service_events_data 
ON service_events USING GIN(event_data);

-- ==============================================================================
-- ADDITIONAL OPTIMIZATIONS
-- ==============================================================================

-- 11. Cover index for service discovery queries (includes commonly selected columns)
-- Optimizes service discovery without needing to access the main table
-- Usage: SELECT id, name, type, host, port, status FROM services WHERE type = ?
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_discovery_cover 
ON services(type) INCLUDE (id, name, host, port, status, last_seen_at);

-- 12. Index for service cleanup operations (finding stale services)
-- Optimizes queries that find services not seen for a certain period
-- Usage: SELECT * FROM services WHERE last_seen_at < NOW() - INTERVAL '5 minutes'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_stale_cleanup 
ON services(last_seen_at) 
WHERE status NOT IN ('stopped');

-- ==============================================================================
-- STATISTICS UPDATE
-- ==============================================================================

-- Update table statistics to help the query planner make better decisions
ANALYZE services;
ANALYZE service_events;

-- ==============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ==============================================================================

COMMENT ON INDEX idx_services_name_host_port IS 'Composite index for service endpoint lookups';
COMMENT ON INDEX idx_services_type_status IS 'Composite index for type and status filtering';
COMMENT ON INDEX idx_services_metadata_tags IS 'GIN index for metadata tag queries';
COMMENT ON INDEX idx_services_health_monitoring IS 'Index for health check operations';
COMMENT ON INDEX idx_services_active_status IS 'Partial index for active services only';
COMMENT ON INDEX idx_services_id_version IS 'Index for optimistic locking operations';
COMMENT ON INDEX idx_service_events_service_time IS 'Composite index for service events with time ordering';
COMMENT ON INDEX idx_service_events_type_time IS 'Index for event type filtering with time';
COMMENT ON INDEX idx_service_events_recent IS 'Partial index for recent events (7 days)';
COMMENT ON INDEX idx_service_events_data IS 'GIN index for event data JSON queries';
COMMENT ON INDEX idx_services_discovery_cover IS 'Covering index for service discovery queries';
COMMENT ON INDEX idx_services_stale_cleanup IS 'Index for finding stale services';

-- ==============================================================================
-- PERFORMANCE NOTES
-- ==============================================================================

/*
PERFORMANCE IMPACT ANALYSIS:

1. QUERY OPTIMIZATIONS:
   - Service endpoint lookups: 10-100x faster with composite index
   - Type/status filtering: 5-50x faster depending on selectivity
   - Metadata tag queries: 10-1000x faster with GIN index
   - Event queries by service: 5-100x faster with proper ordering

2. INDEX MAINTENANCE OVERHEAD:
   - Each index adds ~5-15% overhead to INSERT/UPDATE operations
   - GIN indexes have higher maintenance cost but provide significant query benefits
   - Partial indexes reduce maintenance overhead by only indexing relevant rows

3. STORAGE IMPACT:
   - Estimated additional storage: 20-40% of table size for all indexes
   - GIN indexes are larger but provide better query performance for JSON operations

4. CONCURRENCY:
   - CONCURRENTLY option ensures zero downtime during index creation
   - May take longer to build but doesn't block table operations

5. MONITORING RECOMMENDATIONS:
   - Monitor index usage with pg_stat_user_indexes
   - Check for unused indexes after deployment
   - Monitor query performance improvements with pg_stat_statements
*/