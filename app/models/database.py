from sqlalchemy import create_engine, Column, String, Boolean, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.config import settings

# ══════════════════════════════════════════════
# DATABASE CONNECTION
# ──────────────────────────────────────────────
# pool_pre_ping + pool_recycle were added to fix:
#   psycopg2.OperationalError: SSL connection has been closed unexpectedly
#
# This happened at the very end of long-running requests (e.g. the
# crawl-and-bio pipeline, which does 10+ sequential page loads --
# some via Playwright with multi-second scroll/wait delays -- before
# ever touching the database). While that request is busy crawling,
# the checked-out DB connection sits idle, and the DB server / a
# network proxy in between (common on managed Postgres like Render's)
# silently closes it. When the code finally tries db.commit() at the
# end, SQLAlchemy hands it that now-dead connection and the write fails
# even though nothing was wrong with the query itself.
#
#   pool_pre_ping=True  -- runs a lightweight "is this connection still
#                          alive?" check before handing it to your code.
#                          If it's dead, SQLAlchemy transparently opens
#                          a fresh one instead of failing.
#   pool_recycle=1800    -- proactively recycles connections older than
#                          30 minutes, before the DB/proxy has a chance
#                          to kill them from its side.
# ══════════════════════════════════════════════

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ══════════════════════════════════════════════
# TABLE 1 — CLIENTS
# ══════════════════════════════════════════════

class Client(Base):
    __tablename__ = "clients"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    brands = relationship("Brand", back_populates="client")

# ══════════════════════════════════════════════
# TABLE 2 — BRANDS
# ══════════════════════════════════════════════

class Brand(Base):
    __tablename__ = "brands"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id      = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    name           = Column(String, nullable=False)
    domain         = Column(String, nullable=False)
    bio            = Column(JSON, nullable=True)
    bio_version    = Column(String, default="1.0")
    bio_updated_at = Column(DateTime, nullable=True)
    active_geos    = Column(JSON, default=["IN", "AE", "GB"])
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Auto-run scheduling
    auto_run_enabled = Column(Boolean, default=False)
    auto_run_day     = Column(String, default="monday")  # monday..sunday
    last_auto_run    = Column(DateTime, nullable=True)

    client  = relationship("Client", back_populates="brands")
    prompts = relationship("Prompt", back_populates="brand")
    runs    = relationship("Run", back_populates="brand")

# ══════════════════════════════════════════════
# TABLE 3 — PROMPTS
# ══════════════════════════════════════════════

class Prompt(Base):
    __tablename__ = "prompts"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id       = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    prompt_text    = Column(Text, nullable=False)
    intent_cluster = Column(String, nullable=False)
    prompt_type    = Column(String, nullable=False)
    source_signals = Column(JSON, default=[])
    corpus_version = Column(Integer, default=1)
    status         = Column(String, default="active")
    date_added     = Column(DateTime, default=datetime.utcnow)

    brand     = relationship("Brand", back_populates="prompts")
    responses = relationship("Response", back_populates="prompt")

# ══════════════════════════════════════════════
# TABLE 4 — RUNS
# ══════════════════════════════════════════════

class Run(Base):
    __tablename__ = "runs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id      = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    triggered_by  = Column(String, default="manual")
    status        = Column(String, default="queued")
    started_at    = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)
    total_calls   = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count  = Column(Integer, default=0)

    brand     = relationship("Brand", back_populates="runs")
    responses = relationship("Response", back_populates="run")

# ══════════════════════════════════════════════
# TABLE 5 — RESPONSES
# ──────────────────────────────────────────────
# brand_source_urls is NEW: citation URLs specifically matched to the
# tracked brand (vs citation_urls, which is ALL sources the grounded
# response used, brand-related or not).
# ══════════════════════════════════════════════

class Response(Base):
    __tablename__ = "responses"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id            = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    brand_id          = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    prompt_id         = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=False)
    prompt_text       = Column(Text, nullable=False)
    intent_cluster    = Column(String, nullable=False)
    prompt_type       = Column(String, nullable=False)
    engine            = Column(String, nullable=False)
    geo               = Column(String, nullable=False)
    run_date          = Column(DateTime, default=datetime.utcnow)
    raw_response      = Column(Text, nullable=True)
    brand_mentioned   = Column(Boolean, default=False)
    brand_cited       = Column(Boolean, default=False)
    mention_form      = Column(String, nullable=True)
    mention_position  = Column(Integer, nullable=True)
    sentiment         = Column(String, nullable=True)
    citation_urls     = Column(JSON, default=[])
    brand_source_urls = Column(JSON, default=[])   # NEW
    competing_brands  = Column(JSON, default=[])
    corpus_version    = Column(Integer, default=1)
    parsing_status    = Column(String, default="pending")

    run    = relationship("Run", back_populates="responses")
    brand  = relationship("Brand")
    prompt = relationship("Prompt", back_populates="responses")