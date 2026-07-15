CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Per-account settings. The legacy config table is retained only so existing
-- deployments can upgrade without destructive migration.
CREATE TABLE IF NOT EXISTS user_config (
  owner_email TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (owner_email, key)
);

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  track TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  cover_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '未发',
  qc_score INTEGER,
  qc_level TEXT,
  qc_problems TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);

-- Per-account content library. The legacy articles table remains read-only
-- after upgrading; new cloud data is stored here and isolated by email.
CREATE TABLE IF NOT EXISTS user_articles (
  owner_email TEXT NOT NULL,
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  track TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  cover_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '未发',
  qc_score INTEGER,
  qc_level TEXT,
  qc_problems TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (owner_email, id)
);

CREATE INDEX IF NOT EXISTS idx_user_articles_created_at ON user_articles(owner_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_articles_status ON user_articles(owner_email, status);

-- Per-account delivery receipts. Platform login cookies remain in the user's
-- browser; only the non-sensitive sync result is stored in D1.
CREATE TABLE IF NOT EXISTS user_publications (
  owner_email TEXT NOT NULL,
  article_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT NOT NULL DEFAULT '',
  draft_link TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (owner_email, article_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_user_publications_article
  ON user_publications(owner_email, article_id, updated_at DESC);
