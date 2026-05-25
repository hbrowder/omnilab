import aiosqlite

from core.config import settings

DB_PATH = str(settings.DB_PATH)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS labs (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            description TEXT, category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'stopped', topology TEXT DEFAULT '{}',
            created_at TEXT, updated_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            name TEXT NOT NULL, type TEXT NOT NULL, image TEXT,
            status TEXT DEFAULT 'stopped', config TEXT DEFAULT '{}',
            x REAL DEFAULT 0, y REAL DEFAULT 0, console_port INTEGER,
            created_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        # Schema additions that landed via ALTER TABLE on the production install.
        # Replayed here so a fresh DB (tests, new install) matches the live shape.
        # Each statement is its own try/except — sqlite errors with "duplicate
        # column name" if the column already exists, which is the upgrade path.
        for ddl in (
            "ALTER TABLE nodes ADD COLUMN console_type TEXT NOT NULL DEFAULT 'pty'",
            "ALTER TABLE nodes ADD COLUMN vnc_port INTEGER",
            "ALTER TABLE nodes ADD COLUMN rdp_host TEXT",
            "ALTER TABLE nodes ADD COLUMN rdp_port INTEGER",
        ):
            try:
                await db.execute(ddl)
            except Exception:
                # Column already exists from a prior install — that's fine.
                pass
        await db.execute("""CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            src_node_id TEXT NOT NULL, dst_node_id TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        # CRE-66: Link styling (colors, labels, interface names)
        for ddl in (
            "ALTER TABLE links ADD COLUMN src_interface TEXT",
            "ALTER TABLE links ADD COLUMN dst_interface TEXT",
            "ALTER TABLE links ADD COLUMN color TEXT",
            "ALTER TABLE links ADD COLUMN style TEXT DEFAULT 'Solid'",
            "ALTER TABLE links ADD COLUMN linkstyle TEXT DEFAULT 'Straight'",
            "ALTER TABLE links ADD COLUMN label TEXT",
            "ALTER TABLE links ADD COLUMN labelpos REAL DEFAULT 0.5",
            "ALTER TABLE links ADD COLUMN width REAL DEFAULT 1.5",
        ):
            try:
                await db.execute(ddl)
            except Exception:
                # Column already exists
                pass
        # CRE-56: NAT networks for internet access
        await db.execute("""CREATE TABLE IF NOT EXISTS networks (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            name TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'bridge',
            subnet TEXT, gateway TEXT, dhcp_start TEXT, dhcp_end TEXT,
            dns_servers TEXT, bridge_name TEXT, status TEXT DEFAULT 'inactive',
            created_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        # CRE-55: Template/Image Management System
        await db.execute("""CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            vendor TEXT, category TEXT, description TEXT,
            type TEXT NOT NULL DEFAULT 'docker',
            image TEXT NOT NULL,
            cpu INTEGER DEFAULT 1, ram INTEGER DEFAULT 512, disk INTEGER DEFAULT 10,
            console_type TEXT DEFAULT 'telnet',
            icon TEXT, visible INTEGER DEFAULT 1,
            is_builtin INTEGER DEFAULT 0,
            config TEXT DEFAULT '{}',
            created_at TEXT, updated_at TEXT)""")
        # CRE-53: Multi-User RBAC
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'readonly',
            full_name TEXT, is_active INTEGER DEFAULT 1,
            last_login TEXT, created_at TEXT, updated_at TEXT)""")
        await db.execute("""CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)""")
        await db.execute("""CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)""")
        # Lab ownership and sharing (CRE-53)
        for ddl in (
            "ALTER TABLE labs ADD COLUMN owner_id TEXT",
            "ALTER TABLE labs ADD COLUMN shared_with TEXT DEFAULT '[]'",
            "ALTER TABLE labs ADD COLUMN visibility TEXT DEFAULT 'private'",
        ):
            try:
                await db.execute(ddl)
            except Exception:
                pass
        await db.execute("""CREATE TABLE IF NOT EXISTS license (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            key TEXT, tier TEXT DEFAULT 'free')""")
        await db.execute("INSERT OR IGNORE INTO license (id,tier) VALUES (1,'free')")
        
        # CRE-68: Traffic Filters (Phase 1: Foundation)
        await db.execute("""CREATE TABLE IF NOT EXISTS traffic_filters (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            title TEXT NOT NULL, expr TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#00ff00', timeout INTEGER DEFAULT 5000,
            enabled INTEGER DEFAULT 1, priority INTEGER DEFAULT 0,
            created_at TEXT, updated_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        await db.execute("""CREATE INDEX IF NOT EXISTS idx_filters_lab ON traffic_filters(lab_id)""")
        await db.execute("""CREATE INDEX IF NOT EXISTS idx_filters_enabled ON traffic_filters(lab_id,enabled)""")
        
        # CRE-64: Drawing Tools - Text Objects (rectangles, circles, text annotations)
        await db.execute("""CREATE TABLE IF NOT EXISTS textobjects (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            type TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL,
            width REAL, height REAL,
            fill TEXT DEFAULT 'rgba(88,166,255,0.3)', stroke TEXT DEFAULT 'rgba(88,166,255,1)',
            text TEXT DEFAULT '', z_index INTEGER DEFAULT 0,
            created_at TEXT, updated_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        await db.execute("""CREATE INDEX IF NOT EXISTS idx_textobjects_lab ON textobjects(lab_id)""")
        
        # CRE-15: first-run wizard + admin auth state. Single-row settings
        # row, k/v columns. New fields are added as plain ALTER TABLEs below
        # so existing installs don't lose state on upgrade.
        await db.execute("""CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            first_run_complete INTEGER DEFAULT 0,
            admin_password_hash TEXT,
            telemetry_enabled INTEGER DEFAULT 0,
            updated_at TEXT)""")
        await db.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
        await db.commit()

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
