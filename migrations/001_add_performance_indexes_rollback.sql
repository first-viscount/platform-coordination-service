-- Performance Indexes Rollback Migration for Platform Coordination Service
-- Rollback Migration: 001_add_performance_indexes_rollback
-- Purpose: Remove performance indexes added in 001_add_performance_indexes.sql
-- PostgreSQL 17.5

-- ==============================================================================
-- ROLLBACK: DROP PERFORMANCE INDEXES
-- ==============================================================================

-- Note: Using CONCURRENTLY to avoid blocking operations during index removal
-- This ensures zero downtime when rolling back the migration

-- Drop additional optimization indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_services_stale_cleanup;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_discovery_cover;

-- Drop service_events table indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_service_events_data;
DROP INDEX CONCURRENTLY IF EXISTS idx_service_events_recent;
DROP INDEX CONCURRENTLY IF EXISTS idx_service_events_type_time;
DROP INDEX CONCURRENTLY IF EXISTS idx_service_events_service_time;

-- Drop services table indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_services_id_version;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_active_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_health_monitoring;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_metadata_tags;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_type_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_services_name_host_port;

-- ==============================================================================
-- UPDATE STATISTICS
-- ==============================================================================

-- Update table statistics after index removal
ANALYZE services;
ANALYZE service_events;

-- ==============================================================================
-- ROLLBACK VERIFICATION
-- ==============================================================================

/*
ROLLBACK VERIFICATION QUERIES:

To verify that all indexes have been successfully removed, run:

-- Check remaining indexes on services table
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'services' 
    AND schemaname = 'public'
    AND indexname LIKE 'idx_services_%'
ORDER BY indexname;

-- Check remaining indexes on service_events table  
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'service_events' 
    AND schemaname = 'public'
    AND indexname LIKE 'idx_service_events_%'
ORDER BY indexname;

Expected remaining indexes after rollback:
- services table: idx_services_name, idx_services_type, idx_services_status, 
  idx_services_metadata, idx_services_last_seen (from original schema)
- service_events table: idx_service_events_service_id, idx_service_events_created_at 
  (from original schema)
*/

-- ==============================================================================
-- PERFORMANCE IMPACT OF ROLLBACK
-- ==============================================================================

/*
ROLLBACK IMPACT ANALYSIS:

1. QUERY PERFORMANCE DEGRADATION:
   - Service endpoint lookups: May become 10-100x slower
   - Type/status filtering: May become 5-50x slower
   - Metadata tag queries: May become 10-1000x slower
   - Event queries by service: May become 5-100x slower

2. STORAGE SAVINGS:
   - Will reclaim ~20-40% of table storage used by indexes
   - Immediate disk space recovery after VACUUM operation

3. WRITE PERFORMANCE IMPROVEMENT:
   - INSERT/UPDATE operations will be 5-15% faster per removed index
   - Reduced lock contention during high-concurrency operations

4. MONITORING AFTER ROLLBACK:
   - Monitor query performance degradation with pg_stat_statements
   - Watch for increased query execution times
   - Check for increased CPU usage during database operations

5. ROLLBACK TIMING CONSIDERATIONS:
   - Best performed during low-traffic periods
   - CONCURRENTLY option minimizes impact but rollback takes longer
   - Consider impact on application performance immediately after rollback

RECOMMENDATION:
Only rollback if performance indexes are causing issues (storage constraints, 
excessive write overhead, or maintenance problems). Monitor application 
performance closely after rollback and be prepared to re-apply if needed.
*/