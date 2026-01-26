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
            # Tablas Base (Productos, Ordenes, Settings, Licencias, Wallets, Requests)
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
            try: await conn.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS last_ip_change TIMESTAMP;")
            except: pass
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    symbol TEXT PRIMARY KEY,
                    address TEXT NOT NULL,
                    network TEXT NOT NULL
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    service_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 🆕 NUEVA TABLA: CONFIGS
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT '🟢',
                    price TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, name)
                );
            """)
            
            # 🆕 POBLAR LISTA INICIAL SI ESTÁ VACÍA
            count = await conn.fetchval("SELECT COUNT(*) FROM configs")
            if count == 0:
                print("⚙️ Insertando lista inicial de Configs...")
                initial_data = [
                    # STREAMING
                    ('STREAMING', 'AMCTheatres', ''), ('STREAMING', 'Allente', ''), ('STREAMING', 'Bally Sports', ''),
                    ('STREAMING', 'Britbox', ''), ('STREAMING', 'Crunchyroll', ''), ('STREAMING', 'Curiosity Stream', ''),
                    ('STREAMING', 'Dazn (Ask me for TLS!)', ''), ('STREAMING', 'DirecTV Stream + DirecTV AT&T', ''),
                    ('STREAMING', 'Disney+', ''), ('STREAMING', 'FloSports', ''), ('STREAMING', 'Fox', ''),
                    ('STREAMING', 'FuboTV + FuboTV TLS', ''), ('STREAMING', 'Hulu VM', ''), ('STREAMING', 'ITVX', ''),
                    ('STREAMING', 'MLB', ''), ('STREAMING', 'Marcus Theatres', ''), ('STREAMING', 'NBA League Pass', ''),
                    ('STREAMING', 'NFL + NFL Gamepass', ''), ('STREAMING', 'NHL TV', ''), ('STREAMING', 'Peacock', ''),
                    ('STREAMING', 'PlexTV', ''), ('STREAMING', 'PluralSight', ''), ('STREAMING', 'Pureflix', ''),
                    ('STREAMING', 'Rakuten TV', ''), ('STREAMING', 'Season4U', ''), ('STREAMING', 'Shudder', ''),
                    ('STREAMING', 'SportTV', ''), ('STREAMING', 'Starz', ''), ('STREAMING', 'Tennis TV', ''),
                    ('STREAMING', 'UFC', ''), ('STREAMING', 'VSiN Sports', ''), ('STREAMING', 'Viki Rakuten', ''),
                    ('STREAMING', 'WWE-Network', ''),

                    # GAMING
                    ('GAMING', 'ABYA (GeForceNOW)', ''), ('GAMING', 'GeoGuessr', ''), ('GAMING', 'Steam', ''),
                    ('GAMING', 'Ubisoft Connect', ''), ('GAMING', 'XBOX+Outlook', ''),

                    # EDUCATION
                    ('EDUCATION', 'BentBox', ''), ('EDUCATION', 'Codecademy', ''), ('EDUCATION', 'Chegg', ''),
                    ('EDUCATION', 'Chordify', ''), ('EDUCATION', 'Crehana', ''), ('EDUCATION', 'Domestika', ''),
                    ('EDUCATION', 'Front-End Masters', ''), ('EDUCATION', 'GetAbstract', ''), ('EDUCATION', 'Magoosh', ''),
                    ('EDUCATION', 'Masterclass', ''), ('EDUCATION', 'Mimo', ''), ('EDUCATION', 'Mindvalley', ''),
                    ('EDUCATION', 'Mubi', ''), ('EDUCATION', 'Quizlet', ''), ('EDUCATION', 'RealVision', ''),
                    ('EDUCATION', 'Storytel', ''), ('EDUCATION', 'Studocu', ''), ('EDUCATION', 'Study Mode', ''),
                    ('EDUCATION', 'Symbolab', ''), ('EDUCATION', 'Transtutors', ''), ('EDUCATION', 'Ultimate Guitar', ''),
                    ('EDUCATION', 'Yousician', ''),

                    # ADULT
                    ('ADULT', 'Flingster', ''), ('ADULT', 'Nubiles Porn', ''), ('ADULT', 'Pornhub', ''),
                    ('ADULT', 'VR Porn', ''), ('ADULT', 'XVideos', ''),

                    # FOOD
                    ('FOOD', '&Pizza', ''), ('FOOD', 'Chopt', ''), ('FOOD', 'Dasher Direct', ''),
                    ('FOOD', 'Del Taco', ''), ('FOOD', 'Dominos CA', ''), ('FOOD', 'FoodHub', ''),
                    ('FOOD', 'MakeItCount', ''), ('FOOD', 'Maverik Rewards', ''), ('FOOD', 'PedidosYa', ''),
                    ('FOOD', 'PizzaHut USA', ''), ('FOOD', 'Safeway', ''), ('FOOD', 'ShakeShack', ''),
                    ('FOOD', 'Shipt', ''), ('FOOD', 'Wingstop', ''),

                    # VPN
                    ('VPN', 'CactusVPN', ''), ('VPN', 'DotVPN', ''), ('VPN', 'IPVanish', ''),
                    ('VPN', 'Malwarebytes', ''), ('VPN', 'Mullvad VPN', ''), ('VPN', 'TunnelBear', ''),
                    ('VPN', 'VyprVPN', ''), ('VPN', 'Windscribe (App Version Error)', ''),

                    # SHOP
                    ('SHOP', "Arc'teryx", ''), ('SHOP', 'Engelhorn.de', ''), ('SHOP', 'Farfetch', ''),
                    ('SHOP', 'Fashion Nova', ''), ('SHOP', 'FashionDays', ''), ('SHOP', 'Fitbit', ''),
                    ('SHOP', 'Guitar Center', ''), ('SHOP', 'PlayOn', ''), ('SHOP', 'RackRoom Shoes', ''),
                    ('SHOP', 'SSense', ''), ('SHOP', 'Tanguay', ''),

                    # UNSORTED
                    ('UNSORTED', 'AhRefs', ''), ('UNSORTED', 'BetterMe', ''), ('UNSORTED', 'Calm', ''),
                    ('UNSORTED', 'Codefinity', ''), ('UNSORTED', 'Coohom', ''), ('UNSORTED', 'Evernote', ''),
                    ('UNSORTED', 'FakeYou', ''), ('UNSORTED', 'Figma', ''), ('UNSORTED', 'Headspace', ''),
                    ('UNSORTED', 'InVideo', ''), ('UNSORTED', 'Kismia Dating', ''), ('UNSORTED', 'Lenme', ''),
                    ('UNSORTED', 'Let\'s Enhance', ''), ('UNSORTED', 'Mail VM', ''), ('UNSORTED', 'Meditopia', ''),
                    ('UNSORTED', 'MLB Ballpark', ''), ('UNSORTED', 'Napster', ''), ('UNSORTED', 'Onedrive + File Filter', ''),
                    ('UNSORTED', 'Outlook (Hotmail)', ''), ('UNSORTED', 'Outlook (Hotmail) Inbox Searcher', ''),
                    ('UNSORTED', 'Palia', ''), ('UNSORTED', 'Quillbot', ''), ('UNSORTED', 'RealTrends', ''),
                    ('UNSORTED', 'Soundtrap', ''), ('UNSORTED', 'Speechify', ''), ('UNSORTED', 'TradingView', ''),
                    ('UNSORTED', 'Viki K-Drama', ''), ('UNSORTED', 'Windstream', ''), ('UNSORTED', 'YCharts', ''),
                    ('UNSORTED', 'eHarmony Dating', ''),

                    # PRIVATE
                    ('PRIVATE', 'Roblox (TLS)', '$200 USD'), ('PRIVATE', 'American Airlines', '$250 USD'),
                    ('PRIVATE', 'Hollister & Co', '$60 USD'), ('PRIVATE', 'StripChat (CapSolver)', '$100 USD'),
                    ('PRIVATE', 'REWE (Only Login / Capsolver)', '$25 USD'), ('PRIVATE', 'Degoo Storage Cloud', '$250 USD'),
                    ('PRIVATE', 'ShopLC', '$100 USD'), ('PRIVATE', 'E-Bank Patagonia', '$300 USD'),
                    ('PRIVATE', 'Wall Street Journal', '$75 USD'), ('PRIVATE', 'NYTimes', '$75 USD')
                ]
                await conn.executemany(
                    "INSERT INTO configs (category, name, price) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    initial_data
                )

    # --- MÉTODOS PRODUCTOS ---
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

    # --- MÉTODOS SETTINGS ---
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

    # --- MÉTODOS LICENCIAS ---
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

    async def search_license_by_partial(self, partial_text):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            pattern = f"%{partial_text}%"
            rows = await conn.fetch("SELECT api_key FROM licenses WHERE api_key ILIKE $1", pattern)
            if len(rows) == 0: return None
            elif len(rows) == 1: return rows[0]['api_key']
            else: return "AMBIGUOUS"

    # --- MÉTODOS WALLETS (CRYPTO) ---
    async def set_wallet(self, symbol, address, network):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO wallets (symbol, address, network) VALUES ($1, $2, $3)
                ON CONFLICT (symbol) DO UPDATE SET address = $2, network = $3
            """, symbol.upper(), address, network)
            return True

    async def get_wallet(self, symbol):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM wallets WHERE symbol = $1", symbol.upper())

    async def get_all_wallets(self):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM wallets ORDER BY symbol ASC")

    async def delete_wallet(self, symbol):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM wallets WHERE symbol = $1", symbol.upper())
            return res != "DELETE 0"

    # --- MÉTODOS REQUEST/QUEUE (SISTEMA DE TICKETS) ---
    async def add_request(self, user_id, username, service):
        if not self.pool: return False, 0
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM requests WHERE user_id = $1 AND status IN ('pending', 'processing')", 
                user_id
            )
            if count >= 5:
                return False, count
            await conn.execute(
                "INSERT INTO requests (user_id, username, service_name) VALUES ($1, $2, $3)",
                user_id, username, service
            )
            return True, count + 1

    async def get_user_position(self, user_id):
        if not self.pool: return 0
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM requests WHERE status = 'pending' ORDER BY created_at ASC")
            for index, row in enumerate(rows):
                if row['user_id'] == user_id:
                    return index + 1
            return 0

    async def get_queue_list(self):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM requests WHERE status = 'pending' ORDER BY created_at ASC")

    async def pop_next_request(self):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")
            if row:
                await conn.execute("UPDATE requests SET status = 'processing' WHERE id = $1", row['id'])
                return row
            return None

    async def get_processing_request(self):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM requests WHERE status = 'processing' LIMIT 1")

    async def finish_request(self, request_id, status):
        if not self.pool: return
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE requests SET status = $1 WHERE id = $2", status, request_id)

    async def delete_request(self, request_id):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM requests WHERE id = $1", request_id)
            return res != "DELETE 0"

    # 🆕 MÉTODOS CONFIGS MANAGEMENT
    async def get_all_configs(self):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM configs ORDER BY category, name ASC")

    async def add_config(self, category, name, price=""):
        if not self.pool: return False
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO configs (category, name, price) VALUES ($1, $2, $3)",
                    category.upper(), name, price
                )
            return True
        except: return False

    async def del_config(self, category, name):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM configs WHERE category = $1 AND name ILIKE $2",
                category.upper(), name
            )
            return res != "DELETE 0"

    async def update_config_status(self, category, name, new_status):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE configs SET status = $1 WHERE category = $2 AND name ILIKE $3",
                new_status, category.upper(), name
            )
            return res != "UPDATE 0"

    async def update_config_price(self, category, name, new_price):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE configs SET price = $1 WHERE category = $2 AND name ILIKE $3",
                new_price, category.upper(), name
            )
            return res != "UPDATE 0"

db = Database()
