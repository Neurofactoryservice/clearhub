import sqlite3, os
DB_PATH=os.getenv("DB_PATH","neurofactory.db")
def get_db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c
def init_db():
    db=get_db()
    db.executescript("""
        -- Table utilisateurs (SaaS + Marketplace)
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            -- Identité
            name TEXT DEFAULT "",
            first_name TEXT DEFAULT "",
            last_name TEXT DEFAULT "",
            display_name TEXT DEFAULT "",
            -- Profil public marketplace
            bio TEXT DEFAULT "",
            profile_photo TEXT DEFAULT "",
            is_professional INTEGER DEFAULT 0,
            company_name TEXT DEFAULT "",
            siret TEXT DEFAULT "",
            -- Services proposés
            service_title TEXT DEFAULT "",
            service_description TEXT DEFAULT "",
            service_categories TEXT DEFAULT "",
            price_from REAL DEFAULT 0,
            price_to REAL DEFAULT 0,
            price_unit TEXT DEFAULT "heure",
            -- Localisation
            departement TEXT DEFAULT "",
            city TEXT DEFAULT "",
            zip_code TEXT DEFAULT "",
            address TEXT DEFAULT "",
            intervention_radius INTEGER DEFAULT 20,
            -- Contact & Disponibilité
            phone TEXT DEFAULT "",
            website TEXT DEFAULT "",
            availability TEXT DEFAULT "{}",
            response_time TEXT DEFAULT "< 24h",
            languages TEXT DEFAULT "Français",
            -- Expertise & Certifications
            years_experience INTEGER DEFAULT 0,
            certifications TEXT DEFAULT "",
            -- Stats publiques (calculées)
            rating_avg REAL DEFAULT 0.0,
            review_count INTEGER DEFAULT 0,
            completed_jobs INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            profile_complete INTEGER DEFAULT 0,
            -- Abonnement SaaS
            avatar TEXT DEFAULT "",
            subscription_status TEXT DEFAULT "inactive",
            stripe_customer_id TEXT DEFAULT "",
            stripe_sub_id TEXT DEFAULT "",
            stripe_account_id TEXT DEFAULT "",
            trial_ends_at TEXT DEFAULT "",
            -- Système
            created_at TEXT NOT NULL,
            last_login TEXT DEFAULT "",
            usage_count INTEGER DEFAULT 0,
            role TEXT DEFAULT "user"
        );
        -- Portfolio (photos / réalisations du prestataire)
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT "",
            image_url TEXT DEFAULT "",
            category TEXT DEFAULT "",
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        -- Annonces marketplace (P2P / Location)
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT "",
            price REAL NOT NULL,
            commission REAL NOT NULL DEFAULT 0,
            net_amount REAL NOT NULL DEFAULT 0,
            departement TEXT NOT NULL,
            category TEXT DEFAULT "",
            status TEXT DEFAULT "active",
            rating REAL DEFAULT 0.0,
            review_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE CASCADE
        );
        -- Réservations avec commission 10%
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            commission REAL NOT NULL DEFAULT 0,
            net_amount REAL NOT NULL DEFAULT 0,
            date_service TEXT NOT NULL,
            message TEXT DEFAULT "",
            status TEXT DEFAULT "pending",
            stripe_pi_id TEXT DEFAULT "",
            created_at TEXT NOT NULL,
            validated_at   TEXT DEFAULT NULL,
            disputed_at    TEXT DEFAULT NULL,
            dispute_reason TEXT DEFAULT NULL,
            FOREIGN KEY(client_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE CASCADE
        );
        -- Avis / Reviews
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER UNIQUE NOT NULL,
            listing_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            rating REAL NOT NULL,
            comment TEXT DEFAULT "",
            created_at TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE
        );
        -- Stats plateforme globales
        CREATE TABLE IF NOT EXISTS platform_stats (
            key TEXT PRIMARY KEY,
            value REAL DEFAULT 0
        );
        -- Données communes
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            data TEXT DEFAULT "{}",
            ip TEXT DEFAULT "",
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL DEFAULT 0, currency TEXT DEFAULT "eur",
            status TEXT DEFAULT "paid",
            stripe_id TEXT DEFAULT "", created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL,
            subject TEXT DEFAULT "", message TEXT NOT NULL,
            status TEXT DEFAULT "new", created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS newsletter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
        );
        -- Index pour perf
        CREATE INDEX IF NOT EXISTS idx_listings_dep ON listings(departement);
        CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
        CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(client_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_provider ON bookings(provider_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
        CREATE INDEX IF NOT EXISTS idx_users_dep ON users(departement);
        CREATE INDEX IF NOT EXISTS idx_users_verified ON users(verified);
        CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio(user_id);
        -- Stats initiales
        INSERT OR IGNORE INTO platform_stats (key,value) VALUES ("total_commission",0);
        INSERT OR IGNORE INTO platform_stats (key,value) VALUES ("total_transactions",0);
        INSERT OR IGNORE INTO platform_stats (key,value) VALUES ("total_gmv",0);
    """)
    # Migrations : ajouter colonnes manquantes si ancienne DB
    _cols=[r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    _profile_cols=[
        ("trial_ends_at","''","TEXT"),("last_login","''","TEXT"),
        ("usage_count","0","INTEGER"),("avatar","''","TEXT"),("role","'user'","TEXT"),
        ("departement","''","TEXT"),("bio","''","TEXT"),("phone","''","TEXT"),
        ("stripe_account_id","''","TEXT"),
        # Nouveaux champs profil marketplace
        ("first_name","''","TEXT"),("last_name","''","TEXT"),
        ("display_name","''","TEXT"),("profile_photo","''","TEXT"),
        ("is_professional","0","INTEGER"),("company_name","''","TEXT"),
        ("siret","''","TEXT"),("service_title","''","TEXT"),
        ("service_description","''","TEXT"),("service_categories","''","TEXT"),
        ("price_from","0","REAL"),("price_to","0","REAL"),
        ("price_unit","'heure'","TEXT"),
        ("city","''","TEXT"),("zip_code","''","TEXT"),
        ("address","''","TEXT"),("intervention_radius","20","INTEGER"),
        ("website","''","TEXT"),("availability","'{}'","TEXT"),
        ("response_time","'< 24h'","TEXT"),("languages","'Français'","TEXT"),
        ("years_experience","0","INTEGER"),("certifications","''","TEXT"),
        ("rating_avg","0","REAL"),("review_count","0","INTEGER"),
        ("completed_jobs","0","INTEGER"),("verified","0","INTEGER"),
        ("profile_complete","0","INTEGER"),
    ]
    for col,dflt,typ in _profile_cols:
        if col not in _cols:
            db.execute(f"ALTER TABLE users ADD COLUMN {col} {typ} DEFAULT {dflt}")
    _act=[r[1] for r in db.execute("PRAGMA table_info(activity)").fetchall()]
    if "data" not in _act: db.execute("ALTER TABLE activity ADD COLUMN data TEXT DEFAULT '{}'")
    db.commit()
