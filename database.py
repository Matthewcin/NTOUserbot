import asyncpg
from config import DB_URL

class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # Fix Neon SSL
                url_clean = self.db_url.split('?')[0]
                self.pool = await asyncpg.create_pool(url_clean, ssl='require')
                await self.init_tables()
                print("✅ Database Connected")
            except Exception as e:
                print(f"❌ DATABASE ERROR: {e}")

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            # Tabla Productos
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    key_name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    price_usd NUMERIC(10, 2) NOT NULL,
                    description TEXT,
                    file_url TEXT
                );
            """)
            # Tabla Ordenes
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    oxapay_track_id BIGINT, 
                    user_id BIGINT,
                    product_key TEXT,
                    amount_usd NUMERIC(10, 2),
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # [NUEVO] Tabla Settings (Para guardar URLs de status)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key_name TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            
            # Insertar URLs por defecto si no existen
            await conn.execute("""
                INSERT INTO settings (key_name, value) VALUES 
                ('url_svb', 'https://cloudfig6-001-site1.qtempurl.com/top/api/Configs'),
                ('url_ob2', 'https://cloudfigob-001-site1.anytempurl.com')
                ON CONFLICT DO NOTHING;
            """)

    # --- MÉTODOS DE PRODUCTOS ---
    async def get_product(self, key):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE key_name = $1", key)

    async def get_all_products(self):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products")
            
    async def create_order(self, order_id, track_id, user_id, product_key, amount):
        if not self.pool: return
        try: track_id_int = int(track_id)
        except: track_id_int = 0
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO orders (order_id, oxapay_track_id, user_id, product_key, amount_usd) 
                   VALUES ($1, $2, $3, $4, $5)""",
                order_id, track_id_int, user_id, product_key, amount
            )

    async def update_product(self, key, field, value):
        if not self.pool: return False
        valid_fields = {'price': 'price_usd', 'name': 'display_name', 'desc': 'description', 'link': 'file_url'}
        if field not in valid_fields: return False
        column = valid_fields[field]
        if field == 'price':
            try: value = float(value)
            except: return False
        async with self.pool.acquire() as conn:
            query = f"UPDATE products SET {column} = $1 WHERE key_name = $2"
            res = await conn.execute(query, value, key)
            return res != "UPDATE 0"

    async def delete_product(self, key):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM products WHERE key_name = $1", key)
            return res != "DELETE 0"

    # --- [NUEVOS] MÉTODOS PARA SETTINGS (URLs) ---
    async def get_setting(self, key):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM settings WHERE key_name = $1", key)
            return row['value'] if row else None

    async def set_setting(self, key, value):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO settings (key_name, value) VALUES ($1, $2)
                ON CONFLICT (key_name) DO UPDATE SET value = $2
            """, key, value)
            return True

db = Database(DB_URL)
