# Integration Guide

How to integrate external clients with the osgeo-knowledge database.

## MCP Server (Primary Interface)

The MCP server is the recommended way to access the knowledge base. It runs
over STDIO transport and exposes 6 tools.

### Running the server

```bash
python -m osgeo_knowledge.servers.mcp
```

### Available tools

| Tool | Description |
|------|-------------|
| `search_wiki` | Semantic search over LLM-generated summaries and keywords |
| `search_content` | Full-text search over raw page content chunks |
| `search_entities` | Find people, projects, organizations, events (fuzzy matching) |
| `get_entity_relationships` | Query relationships between entities |
| `get_page` | Get full content of a specific page by title |
| `get_wiki_stats` | Database statistics and sync status |

### Tool parameters

**search_wiki** and **search_content**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Natural language or keywords |
| `source` | string | all | `'wiki'`, `'planet'`, or `'wordpress'` |
| `date_from` | string | none | Start date, YYYY-MM-DD |
| `date_to` | string | none | End date, YYYY-MM-DD |
| `limit` | int | 5 | Max results (1-20) |

**search_entities**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Entity name (partial/fuzzy OK) |
| `entity_type` | string | all | `'person'`, `'project'`, `'organization'`, `'event'`, `'year'` |
| `limit` | int | 10 | Max results (1-30) |

**get_entity_relationships**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_name` | string | required | Entity name (fuzzy matched) |
| `predicate` | string | all | Relationship type, e.g. `'member_of'`, `'contributes_to'`, `'president_of'` |
| `limit` | int | 20 | Max results (1-50) |


## Client Configuration

### opencode (opencode-chat-bridge)

In `opencode.json`:

```json
{
  "mcpServers": {
    "osgeo-knowledge": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "osgeo_knowledge.servers.mcp"],
      "env": {
        "OSGEO_DB_URL": "postgresql://user:pass@localhost:5432/osgeo_knowledge"
      }
    }
  }
}
```

### Claude Desktop

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "osgeo-knowledge": {
      "command": "python",
      "args": ["-m", "osgeo_knowledge.servers.mcp"],
      "env": {
        "OSGEO_DB_URL": "postgresql://user:pass@localhost:5432/osgeo_knowledge"
      }
    }
  }
}
```

### Generic MCP client

Any MCP client that supports STDIO transport can connect:

```json
{
  "command": "python",
  "args": ["-m", "osgeo_knowledge.servers.mcp"],
  "transport": "stdio",
  "env": {
    "OSGEO_DB_URL": "postgresql://user:pass@localhost:5432/osgeo_knowledge"
  }
}
```


## Bot Deployment with Skills

Skills provide domain-specific instructions that tell a bot how and when
to use the MCP tools. They live in the `skills/` directory:

```
skills/
  wiki/SKILL.md
  planet/SKILL.md
  entities/SKILL.md
  wordpress/SKILL.md
```

`AGENTS.md` at the repository root indexes all skills and defines the
bot persona (response format, skill-loading rules, cross-domain query
strategies).

### Deploying skills to a bot

Symlink the skill directories and AGENTS.md into the bot's workspace:

```bash
# Skills
ln -s /path/to/osgeo-knowledge/skills/wiki    /path/to/bot/.opencode/skills/wiki
ln -s /path/to/osgeo-knowledge/skills/planet   /path/to/bot/.opencode/skills/planet
ln -s /path/to/osgeo-knowledge/skills/entities /path/to/bot/.opencode/skills/entities
ln -s /path/to/osgeo-knowledge/skills/wordpress /path/to/bot/.opencode/skills/wordpress

# Agent instructions
ln -s /path/to/osgeo-knowledge/AGENTS.md /path/to/bot/.opencode/AGENTS.md
```

The bot loads a skill before answering domain-specific questions. For
cross-domain queries it loads multiple skills and combines results.


## Direct SQL (Advanced)

For advanced use cases you can query the database directly. Use read-only
credentials. See [docs/search.md](search.md) for full details.

### Schema overview

| Table | Key columns | Purpose |
|-------|-------------|---------|
| `pages` | `id`, `title`, `url`, `last_crawled` | Crawled pages |
| `page_chunks` | `page_id`, `chunk_text`, `tsv`, `chunk_index` | Content split into searchable chunks |
| `page_extensions` | `url`, `resume`, `keywords`, `resume_tsv`, `keywords_tsv` | LLM-generated summaries |
| `entities` | `id`, `entity_name`, `entity_type`, `url`, `confidence` | Extracted entities |
| `entity_relationships` | `subject_id`, `object_id`, `predicate`, `confidence` | Triples between entities |

### Quick examples

Full-text search over content chunks:

```sql
SELECT p.title, p.url,
       ts_rank(pc.tsv, websearch_to_tsquery('english', 'QGIS sketcher')) AS rank
FROM page_chunks pc
JOIN pages p ON pc.page_id = p.id
WHERE pc.tsv @@ websearch_to_tsquery('english', 'QGIS sketcher')
ORDER BY rank DESC
LIMIT 10;
```

Find an entity by name:

```sql
SELECT entity_name, entity_type, url, confidence
FROM entities
WHERE entity_name ILIKE '%warmerdam%';
```

Get relationships for an entity:

```sql
SELECT e1.entity_name AS subject, er.predicate, e2.entity_name AS object
FROM entity_relationships er
JOIN entities e1 ON er.subject_id = e1.id
JOIN entities e2 ON er.object_id = e2.id
WHERE e1.entity_name ILIKE '%OSGeo%'
ORDER BY er.confidence DESC
LIMIT 20;
```
