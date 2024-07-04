try:
    import asyncpg
except ImportError:
    asyncpg = None

import sqlite3


class Connection:
    def __init__(self, db_url: str):
        self.db_url = db_url
        if db_url.startswith('sqlite://'):
            self.conn = sqlite3.connect(db_url.removeprefix('sqlite://'), check_same_thread=False)
            self.dbtype = 'sqlite'
        elif db_url.startswith('postgresql://'):
            self.conn = None
            self.dbtype = 'postgresql'
        else:
            raise ValueError('Unknown database URL')

    async def connect(self):
        if self.dbtype == 'sqlite':
            return self.conn
        if self.conn == None or self.conn.is_closed():
            self.conn = await asyncpg.connect(self.db_url)
        return self.conn

    async def select(self, query: str, *args):
        conn = await self.connect()
        if self.dbtype == 'sqlite':
            return conn.execute(query, *args).fetchall()
        return await conn.fetch(replace_qmarks(query), *args)

    async def select_one(self, query: str, *args):
        conn = await self.connect()
        if self.dbtype == 'sqlite':
            return conn.execute(query, *args).fetchone()
        return await conn.fetchrow(replace_qmarks(query), *args)

    async def update_or_insert(self, table, key_data, update_data):
        conn = await self.connect()
        if self.dbtype == 'sqlite':
            conn.execute(f'DELETE FROM {table} WHERE {" AND ".join([f"{k} = ?" for k in key_data])}', [*key_data.values()])
            conn.execute(f'INSERT INTO {table} ({",".join([*key_data.keys(), *update_data.keys()])}) VALUES ({",".join([f"?" for _ in range(1, len(key_data) + len(update_data) + 1)])})', [*key_data.values(), *update_data.values()])
        else:
            await conn.execute(f'INSERT INTO {table} ({",".join([*key_data.keys(), *update_data.keys()])}) VALUES ({",".join([f"${n}" for n in range(1, len(key_data) + len(update_data) + 1)])}) ON CONFLICT ({",".join(key_data.keys())}) DO UPDATE SET {",".join([f"{k} = EXCLUDED.{k}" for k in update_data])}', *key_data.values(), *update_data.values())

    async def execute(self, query: str, *args):
        conn = await self.connect()
        if self.dbtype == 'sqlite':
            conn.execute(query, *args)
        else:
            await conn.execute(replace_qmarks(query), *args)

def replace_qmarks(query: str) -> str:
    qmark_count = query.count('?')
    for i in range(qmark_count):
        query = query.replace('?', f'${i + 1}', 1)
    return query

LAST_MIGRATION = 1

async def do_migrations(conn: Connection):
    if conn.dbtype == 'sqlite':
        has_migrations_table = await conn.select_one('SELECT 1 FROM sqlite_master WHERE type="table" AND name="migrations"')
    else:
        has_migrations_table = await conn.select_one('SELECT 1 FROM information_schema.tables WHERE table_name = \'migrations\'')
    if has_migrations_table is None:
        await conn.execute('CREATE TABLE migrations (num INTEGER PRIMARY KEY)')
    max_migration = await conn.select_one('SELECT MAX(num) FROM migrations')
    if max_migration[0] is None:
        max_migration = 0
    else:
        max_migration = max_migration[0]

    for i in range(max_migration + 1, LAST_MIGRATION + 1):
        await globals()[f'do_migration_{i}'](conn)
        await conn.execute('INSERT INTO migrations (num) VALUES (?)', 1)

async def do_migration_1(conn: Connection):
    await conn.execute('CREATE TABLE IF NOT EXISTS defines (name TEXT, chat TEXT, message TEXT)')
    await conn.execute('CREATE TABLE IF NOT EXISTS bonks (user_id TEXT, chat_id TEXT)')
