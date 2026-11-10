-- Ejecutar: mysql -u root -p < schema.sql
CREATE DATABASE IF NOT EXISTS nap_plaza CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nap_plaza;

CREATE TABLE IF NOT EXISTS naps (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(30) NOT NULL UNIQUE,
  sector VARCHAR(100) NOT NULL,
  address VARCHAR(200) DEFAULT '',
  splitter VARCHAR(5) NOT NULL DEFAULT '1:8',
  ports_total TINYINT UNSIGNED NOT NULL DEFAULT 8,
  ports_used TINYINT UNSIGNED NOT NULL DEFAULT 0,
  olt_tx_dbm DECIMAL(4,1) NOT NULL DEFAULT 3.0,
  distance_km DECIMAL(5,2) NOT NULL DEFAULT 1.00,
  state ENUM('Activa','Mantenimiento','Inactiva') NOT NULL DEFAULT 'Activa',
  notes VARCHAR(255) DEFAULT '',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CHECK (ports_used <= ports_total)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nap_id INT NOT NULL,
  technician VARCHAR(80) NOT NULL,
  rx_dbm DECIMAL(5,2) NOT NULL,
  connectors TINYINT UNSIGNED NOT NULL DEFAULT 2,
  splices TINYINT UNSIGNED NOT NULL DEFAULT 2,
  expected_dbm DECIMAL(5,2) NOT NULL,
  loss_db DECIMAL(5,2) NOT NULL,
  status ENUM('OK','ALERTA','CRITICO') NOT NULL,
  diagnosis VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (nap_id) REFERENCES naps(id) ON DELETE CASCADE,
  INDEX idx_audits_nap (nap_id, id)
) ENGINE=InnoDB;

INSERT IGNORE INTO naps (code,sector,address,splitter,ports_total,ports_used,olt_tx_dbm,distance_km,state) VALUES
('NAP-GUA-001','Guarenas Centro','Av. Intercomunal, sector centro','1:8',8,5,3.0,1.20,'Activa'),
('NAP-GUA-002','Ciudad Casarapa','Calle principal, Ciudad Casarapa','1:16',16,11,3.0,2.80,'Activa'),
('NAP-GUA-003','Mampote','Vía Mampote','1:8',8,2,2.5,4.10,'Mantenimiento');
