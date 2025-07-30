
CREATE TABLE IF NOT EXISTS network_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    collapsed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS subnets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER,
    name TEXT NOT NULL,
    vlan_id INTEGER,
    cidr TEXT NOT NULL,
    FOREIGN KEY(block_id) REFERENCES network_blocks(id)
);
CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    action TEXT,
    block TEXT,
    details TEXT,
    content TEXT
);
