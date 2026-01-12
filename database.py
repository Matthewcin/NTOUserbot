import asyncpg
import config
import time

class Database:
    def __init__(self):
        self.db_url = config.DB_URL
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                url_clean = self.db_url.split('?')[0]
                self.pool = await asyncpg.create_pool(url_clean, ssl='require')
                await self.init_tables()
                print("✅ Database Connected")
            except Exception as e:
                print(f"❌ DATABASE ERROR: {e}")

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            # Tablas (Products, Orders, Settings, Licenses)...
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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    oxapay_track_id TEXT, 
                    user_id BIGINT,
                    product_key TEXT,
                    amount_usd NUMERIC(10, 2),
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key_name TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    user_id BIGINT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_ip_change TIMESTAMP
                );
            """)
            # Migración por si acaso
            try: await conn.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS last_ip_change TIMESTAMP;")
            except: pass

    # --- MÉTODOS ESTÁNDAR (Get, Create, etc) ---
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
        track_id_str = str(track_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO orders (order_id, oxapay_track_id, user_id, product_key, amount_usd) 
                   VALUES ($1, $2, $3, $4, $5)""",
                order_id, track_id_str, user_id, product_key, amount
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

    # --- MÉTODOS DE LICENCIAS ---
    async def get_license(self, user_id):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT api_key FROM licenses WHERE user_id = $1", user_id)
            return row['api_key'] if row else None

    async def is_key_redeemed(self, api_key):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT user_id FROM licenses WHERE api_key = $1", api_key)
            return row is not None

    async def redeem_license(self, user_id, api_key):
        if not self.pool: return False
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO licenses (user_id, api_key) VALUES ($1, $2)", 
                    user_id, api_key
                )
            return True
        except:
            return False

    async def can_change_ip(self, user_id):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT last_ip_change FROM licenses WHERE user_id = $1", user_id)
            if not row or not row['last_ip_change']: return True
            
            last_ts = row['last_ip_change'].timestamp()
            diff = time.time() - last_ts
            seven_days = 7 * 24 * 60 * 60
            
            if diff >= seven_days: return True
            remaining = seven_days - diff
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            return f"{days}d {hours}h"

    async def update_ip_cooldown(self, user_id):
        if not self.pool: return
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE licenses SET last_ip_change = NOW() WHERE user_id = $1", user_id)

    # 🆕 NUEVO: BUSCADOR INTELIGENTE DE KEY
    async def search_license_by_partial(self, partial_text):
        """Busca una licencia que contenga el texto dado (case insensitive)"""
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            # ILIKE es case-insensitive en Postgres. %texto% busca en cualquier parte.
            pattern = f"%{partial_text}%"
            rows = await conn.fetch("SELECT api_key FROM licenses WHERE api_key ILIKE $1", pattern)
            
            if len(rows) == 0:
                return None # No se encontró nada
            elif len(rows) == 1:
                return rows[0]['api_key'] # Se encontró EXACTAMENTE una
            else:
                return "AMBIGUOUS" # Se encontraron muchas (ej: "VIRUS" coincide con VIRUS-1 y VIRUS-2)

db = Database()
