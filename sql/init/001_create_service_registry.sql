-- Service Registry Schema for Platform Coordination Service
-- PostgreSQL 17.5

-- Create custom types
CREATE TYPE service_status AS ENUM (
    'healthy',
    'degraded',
    'unhealthy',
    'unknown',
    'starting',
    'stopping',
    'stopped'
);

CREATE TYPE service_type AS ENUM (
    'api',
    'worker',
    'scheduler',
    'gateway',
    'cache',
    'database',
    'message_broker',
    'monitoring'
);

-- Create services table
CREATE TABLE IF NOT EXISTS services (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type service_type NOT NULL,
    
    -- Network information
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL CHECK (port > 0 AND port < 65536),
    
    -- Status and health
    status service_status NOT NULL DEFAULT 'unknown',
    health_check_endpoint VARCHAR(500),
    health_check_interval INTEGER DEFAULT 30, -- seconds
    health_check_timeout INTEGER DEFAULT 10, -- seconds
    health_check_failures INTEGER DEFAULT 0,
    last_health_check_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata stored as JSONB for flexibility
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Version for optimistic locking
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Constraints
    CONSTRAINT unique_service_endpoint UNIQUE (name, host, port)
);

-- Create indexes for common queries
CREATE INDEX idx_services_name ON services(name);
CREATE INDEX idx_services_type ON services(type);
CREATE INDEX idx_services_status ON services(status);
CREATE INDEX idx_services_metadata ON services USING GIN(metadata);
CREATE INDEX idx_services_last_seen ON services(last_seen_at);

-- Create service_events table for audit trail
CREATE TABLE IF NOT EXISTS service_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for querying events by service
    CONSTRAINT fk_service_event FOREIGN KEY (service_id) REFERENCES services(id)
);

CREATE INDEX idx_service_events_service_id ON service_events(service_id);
CREATE INDEX idx_service_events_created_at ON service_events(created_at);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_services_updated_at BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to log service events
CREATE OR REPLACE FUNCTION log_service_event()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO service_events (service_id, event_type, event_data)
    VALUES (
        NEW.id,
        TG_ARGV[0],
        jsonb_build_object(
            'old_status', OLD.status,
            'new_status', NEW.status,
            'old_metadata', OLD.metadata,
            'new_metadata', NEW.metadata
        )
    );
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to log status changes
CREATE TRIGGER log_service_status_change
    AFTER UPDATE OF status ON services
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION log_service_event('status_change');

-- View for active services (easier querying)
CREATE VIEW active_services AS
SELECT 
    id,
    name,
    type,
    host,
    port,
    status,
    metadata,
    last_seen_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen_at)) as seconds_since_seen
FROM services
WHERE status NOT IN ('stopped', 'unknown')
  AND last_seen_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes';

-- Comments for documentation
COMMENT ON TABLE services IS 'Registry of all services in the platform';
COMMENT ON COLUMN services.metadata IS 'JSONB field for flexible service metadata including tags, version, dependencies';
COMMENT ON COLUMN services.version IS 'Optimistic locking version, incremented on each update';
COMMENT ON TABLE service_events IS 'Audit trail of service lifecycle events';
COMMENT ON VIEW active_services IS 'Convenient view of currently active services';