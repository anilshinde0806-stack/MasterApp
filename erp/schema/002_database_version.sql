CREATE TABLE IF NOT EXISTS erp.database_version
(
    id SERIAL PRIMARY KEY,

    version VARCHAR(20),

    installed_on TIMESTAMP DEFAULT NOW(),

    installed_by VARCHAR(100),

    remarks TEXT
);