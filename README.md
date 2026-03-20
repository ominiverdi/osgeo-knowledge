# OSGeo Knowledge Base

A PostgreSQL knowledge base of the OSGeo ecosystem, with an MCP server for AI assistant integration. Aggregates content from the OSGeo wiki, Planet OSGeo blog feeds, and the osgeo.org website.

## What it does

This project crawls OSGeo content sources, processes text into searchable chunks, extracts entities and relationships, generates LLM-enhanced summaries, and exposes everything through a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server.

**Data sources:**

| Source | Content | Pages |
|--------|---------|-------|
| OSGeo Wiki | Projects, governance, board meetings, local chapters, community guidelines | 5300+ |
| Planet OSGeo | Aggregated blog posts from GeoServer, QGIS, Mappery, gvSIG, etc. | 50+ |
| osgeo.org | Official website pages, sponsorship info, project descriptions | 89 |

**Use cases:**

- Power chatbots that answer questions about OSGeo ("What is QGIS?", "Who is the president of OSGeo?")
- Search across wiki content, blog posts, and website pages with source and date filtering
- Query a knowledge graph of 20,000+ entities and 17,000+ relationships

## MCP Server

The primary interface is an MCP server with 6 tools:

| Tool | Description |
|------|-------------|
| `search_wiki` | Search LLM-generated summaries and keywords (primary search) |
| `search_content` | Full-text search over raw page content with highlights |
| `search_entities` | Fuzzy entity search (people, projects, orgs, conferences) |
| `get_entity_relationships` | Knowledge graph queries (subject-predicate-object triples) |
| `get_page` | Retrieve full wiki page content by title |
| `get_wiki_stats` | Database statistics and sync status |

Both search tools support filtering by `source` (`wiki`, `planet`, `wordpress`) and date range (`date_from`, `date_to` in YYYY-MM-DD format).

### Running the MCP server

```bash
# Install with MCP dependencies
pip install -e ".[mcp]"

# Run via module
python -m osgeo_knowledge.servers.mcp

# Or via CLI
osgeo-knowledge mcp
```

### MCP client configuration

Add to your `opencode.json`, Claude Desktop config, or any MCP-compatible client:

```json
{
  "osgeo-knowledge": {
    "type": "local",
    "command": [
      "/path/to/venv/bin/python",
      "-m",
      "osgeo_knowledge.servers.mcp"
    ]
  }
}
```

## Skills

The `skills/` directory contains bot integration skills -- structured instructions that tell AI models how and when to use each tool:

| Skill | Purpose |
|-------|---------|
| `skills/wiki/` | OSGeo wiki search with `source="wiki"` |
| `skills/planet/` | Planet OSGeo blog posts with `source="planet"` |
| `skills/entities/` | People, projects, orgs, and relationships |
| `skills/wordpress/` | osgeo.org website pages with `source="wordpress"` |

The `AGENTS.md` file at the project root indexes all skills for bot deployment. See [docs/integration.md](docs/integration.md) for details.

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ with `pg_trgm` extension

### Quick Start

```bash
# Clone and install
git clone https://github.com/ominiverdi/osgeo-knowledge.git
cd osgeo-knowledge
python -m venv venv
source venv/bin/activate
pip install -e ".[mcp,crawl]"

# Configure database connection
cp .env.template .env
# Edit .env with your PostgreSQL credentials

# Initialize database schema
psql -d your_db -f schema/tables.sql
psql -d your_db -f schema/triggers.sql
psql -d your_db -f schema/extension.sql
psql -d your_db -f schema/sync_tracking.sql

# Sync content from all sources
python crawler/wiki_sync.py --days 30
python crawler/planet_sync.py --all
python crawler/wordpress_sync.py --days 30

# Process content
python db/process_chunks.py --limit 500
python db/process_extensions.py --limit 100
```

For production deployment and cron setup, see [docs/operations.md](docs/operations.md).

## Architecture

### Data Flow

1. **Crawling** -- Three crawlers fetch content from wiki, Planet OSGeo, and osgeo.org
2. **Queue** -- New/updated pages enter the processing queue
3. **Chunking** -- Content split into searchable chunks with tsvector indexes
4. **Extensions** -- LLM generates summaries and keywords for each page
5. **Entities** -- Named entity extraction and relationship linking
6. **MCP Server** -- Tools expose search, entity lookup, and page retrieval

### Components

```
osgeo-knowledge/
  osgeo_knowledge/       Python package
    servers/mcp.py       MCP server (6 tools)
    db.py                Database connection helpers
    cli.py               CLI entry point
  crawler/               Content crawlers (wiki, planet, wordpress)
  db/                    Processing scripts (chunks, extensions, entities)
  schema/                PostgreSQL schema definitions
  skills/                Bot integration skills (wiki, planet, entities, wordpress)
  docs/                  Documentation
  analysis/              Search quality evaluation scripts
  tests/                 Query and search tests
  AGENTS.md              Bot deployment config (skill index)
  pyproject.toml         Package definition with mcp, dev, crawl extras
```

## Database Schema

### Core Tables

- `pages` -- Page content and metadata
- `page_chunks` -- Searchable content chunks with tsvector indexes
- `page_categories` -- Category assignments
- `page_extensions` -- LLM-generated summaries and keywords

### Entity Tables

- `entities` -- Named entities (person, project, organization, conference, location, etc.)
- `entity_relationships` -- Subject-predicate-object triples

### Sync Tables

- `source_pages` -- Tracks synced content per source type (wiki, planet_post, wordpress_page)
- `processing_queue` -- Task queue for chunk/extension/entity processing
- `sync_log` -- Sync run history

See [docs/schema.md](docs/schema.md) for full schema documentation.

## Documentation

- [docs/operations.md](docs/operations.md) -- Production deployment, cron setup, maintenance
- [docs/integration.md](docs/integration.md) -- MCP server integration and bot deployment
- [docs/search.md](docs/search.md) -- Search capabilities and query patterns
- [docs/crawlers.md](docs/crawlers.md) -- Content crawlers (wiki, planet, wordpress)
- [docs/schema.md](docs/schema.md) -- Database schema reference
- [docs/data_pipeline.md](docs/data_pipeline.md) -- Data processing pipeline
- [docs/entities.md](docs/entities.md) -- Entity extraction and knowledge graph
- [docs/wordpress_integration.md](docs/wordpress_integration.md) -- WordPress source details

## License

GNU General Public License v3.0 -- see [LICENSE](LICENSE).
