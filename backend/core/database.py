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
        await db.execute("""CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY, lab_id TEXT NOT NULL,
            src_node_id TEXT NOT NULL, dst_node_id TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS license (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            key TEXT, tier TEXT DEFAULT 'free')""")
        await db.execute("INSERT OR IGNORE INTO license (id,tier) VALUES (1,'free')")
        await db.commit()

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
