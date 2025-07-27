-- Radio Station Database Schema
CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sign TEXT NOT NULL UNIQUE,
    facility_id INTEGER UNIQUE,
    service_type TEXT NOT NULL CHECK (service_type IN ('FM', 'AM')),
    frequency REAL NOT NULL,
    
    -- Station info
    station_name TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    
    -- Location
    latitude REAL,
    longitude REAL,
    
    -- Power and coverage
    power_watts REAL,
    coverage_radius_km REAL,
    
    -- Content
    genre TEXT,
    
    -- Metadata
    status TEXT DEFAULT 'ACTIVE',
    data_source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stations_call_sign ON stations (call_sign);
CREATE INDEX IF NOT EXISTS idx_stations_frequency ON stations (frequency);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations (latitude, longitude);