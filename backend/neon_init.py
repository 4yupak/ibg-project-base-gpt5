#!/usr/bin/env python3
"""
Initialize Neon PostgreSQL database with PropBase schema
"""
import psycopg2
from psycopg2.extras import execute_values
import os
import json
from datetime import datetime

# Neon connection parameters
NEON_HOST = 'ep-dark-fog-a1zovppt-pooler.ap-southeast-1.aws.neon.tech'
NEON_DB = 'neondb'
NEON_USER = 'neondb_owner'
NEON_PASSWORD = 'npg_DQac6znJ0oxN'

def get_connection():
    return psycopg2.connect(
        host=NEON_HOST,
        database=NEON_DB,
        user=NEON_USER,
        password=NEON_PASSWORD,
        sslmode='require'
    )

def init_schema():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Drop existing tables (for clean start)
    drop_tables = """
    DROP TABLE IF EXISTS price_history CASCADE;
    DROP TABLE IF EXISTS price_versions CASCADE;
    DROP TABLE IF EXISTS units CASCADE;
    DROP TABLE IF EXISTS project_phases CASCADE;
    DROP TABLE IF EXISTS projects CASCADE;
    DROP TABLE IF EXISTS developers CASCADE;
    DROP TABLE IF EXISTS infrastructure CASCADE;
    DROP TABLE IF EXISTS districts CASCADE;
    DROP TABLE IF EXISTS cities CASCADE;
    DROP TABLE IF EXISTS countries CASCADE;
    DROP TABLE IF EXISTS user_sessions CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS collections CASCADE;
    DROP TABLE IF EXISTS collection_items CASCADE;
    DROP TABLE IF EXISTS payment_plans CASCADE;
    DROP TABLE IF EXISTS exchange_rates CASCADE;
    """
    
    for stmt in drop_tables.strip().split(';'):
        if stmt.strip():
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"Warning: {e}")
    
    conn.commit()
    print("Dropped existing tables")
    
    # Create schema
    schema = """
    -- Users
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        is_superuser BOOLEAN DEFAULT FALSE,
        role VARCHAR(50) DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Countries
    CREATE TABLE IF NOT EXISTS countries (
        id SERIAL PRIMARY KEY,
        name_en VARCHAR(255) NOT NULL,
        name_ru VARCHAR(255),
        code VARCHAR(10) UNIQUE NOT NULL,
        center_lat DECIMAL(10, 7),
        center_lng DECIMAL(10, 7),
        default_currency VARCHAR(10) DEFAULT 'USD',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Cities
    CREATE TABLE IF NOT EXISTS cities (
        id SERIAL PRIMARY KEY,
        country_id INTEGER REFERENCES countries(id),
        name_en VARCHAR(255) NOT NULL,
        name_ru VARCHAR(255),
        slug VARCHAR(255) UNIQUE NOT NULL,
        center_lat DECIMAL(10, 7),
        center_lng DECIMAL(10, 7),
        default_zoom INTEGER DEFAULT 12,
        is_active BOOLEAN DEFAULT TRUE,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Districts
    CREATE TABLE IF NOT EXISTS districts (
        id SERIAL PRIMARY KEY,
        city_id INTEGER REFERENCES cities(id),
        name_en VARCHAR(255) NOT NULL,
        name_ru VARCHAR(255),
        slug VARCHAR(255) UNIQUE NOT NULL,
        description_en TEXT,
        description_ru TEXT,
        center_lat DECIMAL(10, 7),
        center_lng DECIMAL(10, 7),
        is_active BOOLEAN DEFAULT TRUE,
        sort_order INTEGER DEFAULT 0,
        projects_count INTEGER DEFAULT 0,
        min_price_usd DECIMAL(15, 2),
        max_price_usd DECIMAL(15, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Developers
    CREATE TABLE IF NOT EXISTS developers (
        id SERIAL PRIMARY KEY,
        name_en VARCHAR(255) NOT NULL,
        name_ru VARCHAR(255),
        slug VARCHAR(255) UNIQUE NOT NULL,
        website VARCHAR(500),
        logo_url VARCHAR(500),
        description_en TEXT,
        description_ru TEXT,
        contact_email VARCHAR(255),
        contact_phone VARCHAR(50),
        projects_count INTEGER DEFAULT 0,
        is_verified BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Projects
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        developer_id INTEGER REFERENCES developers(id),
        district_id INTEGER REFERENCES districts(id),
        slug VARCHAR(255) UNIQUE NOT NULL,
        internal_code VARCHAR(100),
        notion_page_id VARCHAR(100) UNIQUE,
        name_en VARCHAR(500) NOT NULL,
        name_ru VARCHAR(500),
        description_en TEXT,
        description_ru TEXT,
        property_types JSONB DEFAULT '[]',
        status VARCHAR(50) DEFAULT 'under_construction',
        construction_progress INTEGER DEFAULT 0,
        ownership_type VARCHAR(50) DEFAULT 'freehold',
        leasehold_years INTEGER,
        completion_date DATE,
        completion_quarter VARCHAR(10),
        completion_year INTEGER,
        lat DECIMAL(10, 7),
        lng DECIMAL(10, 7),
        address_en VARCHAR(500),
        address_ru VARCHAR(500),
        min_price DECIMAL(15, 2),
        max_price DECIMAL(15, 2),
        min_price_usd DECIMAL(15, 2),
        max_price_usd DECIMAL(15, 2),
        min_price_per_sqm DECIMAL(15, 2),
        max_price_per_sqm DECIMAL(15, 2),
        min_price_per_sqm_usd DECIMAL(15, 2),
        max_price_per_sqm_usd DECIMAL(15, 2),
        original_currency VARCHAR(10) DEFAULT 'THB',
        total_units INTEGER DEFAULT 0,
        available_units INTEGER DEFAULT 0,
        sold_units INTEGER DEFAULT 0,
        reserved_units INTEGER DEFAULT 0,
        min_bedrooms INTEGER,
        max_bedrooms INTEGER,
        min_area DECIMAL(10, 2),
        max_area DECIMAL(10, 2),
        cover_image_url VARCHAR(500),
        gallery JSONB DEFAULT '[]',
        master_plan_url VARCHAR(500),
        video_url VARCHAR(500),
        virtual_tour_url VARCHAR(500),
        website_url VARCHAR(500),
        amenities JSONB DEFAULT '[]',
        features JSONB DEFAULT '{}',
        roi DECIMAL(5, 2),
        has_payment_plan BOOLEAN DEFAULT FALSE,
        smart_home BOOLEAN DEFAULT FALSE,
        price_files JSONB DEFAULT '[]',
        is_featured BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        visibility VARCHAR(50) DEFAULT 'public',
        sort_order INTEGER DEFAULT 0,
        last_price_update TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_projects_district ON projects(district_id);
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
    CREATE INDEX IF NOT EXISTS idx_projects_lat_lng ON projects(lat, lng);
    CREATE INDEX IF NOT EXISTS idx_projects_notion_page_id ON projects(notion_page_id);
    CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);
    
    -- Units
    CREATE TABLE IF NOT EXISTS units (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        phase_id INTEGER,
        unit_number VARCHAR(50) NOT NULL,
        building VARCHAR(100),
        floor INTEGER,
        unit_type VARCHAR(50),
        bedrooms INTEGER DEFAULT 0,
        bathrooms INTEGER DEFAULT 0,
        area DECIMAL(10, 2),
        view_type VARCHAR(100),
        status VARCHAR(50) DEFAULT 'available',
        price DECIMAL(15, 2),
        price_usd DECIMAL(15, 2),
        price_per_sqm DECIMAL(15, 2),
        price_per_sqm_usd DECIMAL(15, 2),
        original_currency VARCHAR(10) DEFAULT 'THB',
        floor_plan_url VARCHAR(500),
        gallery JSONB DEFAULT '[]',
        features JSONB DEFAULT '{}',
        is_featured BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, unit_number)
    );
    
    CREATE INDEX IF NOT EXISTS idx_units_project ON units(project_id);
    CREATE INDEX IF NOT EXISTS idx_units_status ON units(status);
    
    -- Price Versions (for tracking price list imports)
    CREATE TABLE IF NOT EXISTS price_versions (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL,
        source_type VARCHAR(50) NOT NULL,
        source_url VARCHAR(1000),
        source_file_name VARCHAR(255),
        source_file_hash VARCHAR(64),
        status VARCHAR(50) DEFAULT 'pending',
        processing_started_at TIMESTAMP,
        processing_completed_at TIMESTAMP,
        units_created INTEGER DEFAULT 0,
        units_updated INTEGER DEFAULT 0,
        units_unchanged INTEGER DEFAULT 0,
        units_errors INTEGER DEFAULT 0,
        original_currency VARCHAR(10) DEFAULT 'THB',
        exchange_rate_usd DECIMAL(15, 6),
        errors JSONB DEFAULT '[]',
        warnings JSONB DEFAULT '[]',
        raw_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Price History (for tracking unit price changes)
    CREATE TABLE IF NOT EXISTS price_history (
        id SERIAL PRIMARY KEY,
        unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE,
        price_version_id INTEGER REFERENCES price_versions(id),
        old_price DECIMAL(15, 2),
        old_price_usd DECIMAL(15, 2),
        new_price DECIMAL(15, 2),
        new_price_usd DECIMAL(15, 2),
        price_change DECIMAL(15, 2),
        price_change_percent DECIMAL(10, 2),
        change_type VARCHAR(20) NOT NULL,
        currency VARCHAR(10) DEFAULT 'THB',
        exchange_rate DECIMAL(15, 6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Payment Plans
    CREATE TABLE IF NOT EXISTS payment_plans (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        name_ru VARCHAR(255),
        description TEXT,
        description_ru TEXT,
        schedule JSONB DEFAULT '[]',
        installment_months INTEGER,
        is_default BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Exchange Rates
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id SERIAL PRIMARY KEY,
        base_currency VARCHAR(10) NOT NULL,
        target_currency VARCHAR(10) NOT NULL,
        rate DECIMAL(15, 6) NOT NULL,
        source VARCHAR(50) DEFAULT 'api',
        rate_date TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair ON exchange_rates(base_currency, target_currency, rate_date);
    
    -- Insert default exchange rate
    INSERT INTO exchange_rates (base_currency, target_currency, rate, rate_date)
    VALUES ('THB', 'USD', 0.028, CURRENT_TIMESTAMP)
    ON CONFLICT DO NOTHING;
    """
    
    cursor.execute(schema)
    conn.commit()
    print("Schema created successfully")
    
    cursor.close()
    conn.close()

def seed_locations():
    """Seed initial location data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Insert Thailand
    cursor.execute("""
        INSERT INTO countries (name_en, name_ru, code, center_lat, center_lng, default_currency)
        VALUES ('Thailand', 'Таиланд', 'THA', 7.8804, 98.3923, 'THB')
        ON CONFLICT (code) DO UPDATE SET name_en = EXCLUDED.name_en
        RETURNING id
    """)
    thailand_id = cursor.fetchone()[0]
    
    # Insert Phuket city
    cursor.execute("""
        INSERT INTO cities (country_id, name_en, name_ru, slug, center_lat, center_lng, default_zoom)
        VALUES (%s, 'Phuket', 'Пхукет', 'phuket', 7.8804, 98.3923, 11)
        ON CONFLICT (slug) DO UPDATE SET name_en = EXCLUDED.name_en
        RETURNING id
    """, (thailand_id,))
    phuket_id = cursor.fetchone()[0]
    
    # Phuket districts
    districts = [
        ('rawai', 'Rawai', 'Равай', 7.7707, 98.3281),
        ('kata', 'Kata', 'Ката', 7.8206, 98.298),
        ('karon', 'Karon', 'Карон', 7.8447, 98.2958),
        ('patong', 'Patong', 'Патонг', 7.8926, 98.2963),
        ('kamala', 'Kamala', 'Камала', 7.9532, 98.2815),
        ('surin', 'Surin', 'Сурин', 7.9744, 98.2778),
        ('bangtao', 'Bang Tao', 'Банг Тао', 7.9947, 98.2897),
        ('laguna', 'Laguna', 'Лагуна', 8.0075, 98.3028),
        ('naiharn', 'Nai Harn', 'Най Харн', 7.7615, 98.3067),
        ('chalong', 'Chalong', 'Чалонг', 7.8368, 98.3425),
        ('phuket-town', 'Phuket Town', 'Пхукет Таун', 7.8825, 98.3881),
        ('mai-khao', 'Mai Khao', 'Май Као', 8.1652, 98.3017),
        ('nai-yang', 'Nai Yang', 'Най Янг', 8.0969, 98.2936),
        ('cherngtalay', 'Cherng Talay', 'Чернг Талай', 8.0178, 98.3089),
    ]
    
    for slug, name_en, name_ru, lat, lng in districts:
        cursor.execute("""
            INSERT INTO districts (city_id, name_en, name_ru, slug, center_lat, center_lng)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET center_lat = EXCLUDED.center_lat, center_lng = EXCLUDED.center_lng
        """, (phuket_id, name_en, name_ru, slug, lat, lng))
    
    conn.commit()
    print(f"Seeded locations: 1 country, 1 city, {len(districts)} districts")
    
    cursor.close()
    conn.close()

def seed_demo_user():
    """Create demo user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Hash for 'demo123' - using bcrypt compatible hash
    demo_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.OQX.V7RDJKYwpy"
    
    cursor.execute("""
        INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, role)
        VALUES ('demo@propbase.io', %s, 'Demo User', TRUE, TRUE, 'admin')
        ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
    """, (demo_hash,))
    
    conn.commit()
    print("Created demo user: demo@propbase.io / demo123")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("=== Initializing Neon PostgreSQL Database ===")
    init_schema()
    seed_locations()
    seed_demo_user()
    print("=== Database initialization complete ===")
