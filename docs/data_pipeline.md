# Data Pipeline

This document describes the data import and update strategies for the OSGeo Knowledge Base.

## Content Sources

### 1. OSGeo Wiki (wiki.osgeo.org)
- MediaWiki instance
- Primary source for project documentation, governance, events
- Implemented via `crawler/wiki_sync.py`

### 2. Planet OSGeo (planet.osgeo.org)
- Aggregates blog posts from 100+ OSGeo community members and projects
- Community updates, event reports, project highlights
- Implemented via `crawler/planet_sync.py`

### 3. OSGeo Website (osgeo.org)
- Main website content (WordPress)
- News, announcements, organizational info
- Implemented via `crawler/wordpress_sync.py`

## Initial Import

### Phase 1: Wiki Content
1. **Crawl** - Fetch all wiki pages using MediaWiki API
2. **Parse** - Extract clean text content, metadata, categories
3. **Chunk** - Split content into searchable chunks (optimized size)
4. **Index** - Generate tsvector for full-text search
5. **Store** - Insert into PostgreSQL

### Phase 2: Entity Extraction
1. **Identify** - Extract named entities (people, projects, organizations, events)
2. **Classify** - Assign entity types
3. **Link** - Create relationships between entities
4. **Store** - Populate entity and relationship tables

### Phase 3: Planet OSGeo Content
1. **Crawl** - Fetch posts from Planet OSGeo RSS/Atom feed
2. **Parse** - Extract content, author, source blog, date
3. **Chunk** - Split into searchable chunks
4. **Merge** - Integrate with existing wiki entities where applicable
5. **Store** - Insert into PostgreSQL

### Phase 4: WordPress Content
1. **Crawl** - Fetch pages and posts via WordPress REST API (osgeo.org)
2. **Parse** - Extract content, author, date, categories
3. **Chunk** - Split into searchable chunks
4. **Merge** - Integrate with existing entities where applicable
5. **Store** - Insert into PostgreSQL

## Continuous Update Strategy

### MediaWiki Recent Changes API

We use the MediaWiki `recentchanges` API for efficient change detection:

```
https://wiki.osgeo.org/w/api.php?action=query&list=recentchanges&rcprop=title|timestamp|ids|user|comment&rclimit=50&format=json
```

**Response fields:**
| Field | Description |
|-------|-------------|
| `pageid` | Unique page ID (stable across renames) |
| `title` | Page title |
| `revid` | New revision ID |
| `old_revid` | Previous revision ID |
| `timestamp` | When the change occurred |
| `user` | Who made the edit |
| `comment` | Edit summary |

**Filtering by date:**
```
&rcend=2025-12-10T00:00:00Z  # Only changes after this timestamp
```

### Avoiding Duplicate Updates

**Problem scenarios:**
1. Multiple edits to same page in one sync (e.g., 4 edits to "Osgeo8")
2. Page updated again after we already synced it today

**Solution: Track revision ID per page**

We store the last processed `revid` for each page. On sync:
1. Deduplicate changes by `pageid`, keeping only the latest `revid`
2. Compare against stored `revid` - skip if already processed
3. Optionally hash content to detect identical content across revisions

### Sync Algorithm

```python
def sync_changes(since_timestamp):
    # 1. Get recent changes from API
    changes = fetch_recentchanges(since=since_timestamp)
    
    # 2. Deduplicate - keep only latest revid per pageid
    latest_by_page = {}
    for change in changes:
        pageid = change['pageid']
        if pageid not in latest_by_page or change['revid'] > latest_by_page[pageid]['revid']:
            latest_by_page[pageid] = change
    
    # 3. Filter out already-processed revisions
    to_update = []
    for pageid, change in latest_by_page.items():
        stored_revid = db.get_last_revid(pageid)
        if stored_revid is None or change['revid'] > stored_revid:
            to_update.append(change)
    
    # 4. Process only what's actually new
    for change in to_update:
        content = fetch_page_content(change['title'])
        update_chunks(change['pageid'], content)
        db.set_last_revid(change['pageid'], change['revid'])
    
    return len(to_update)
```

### Update Scenarios

| Scenario | What happens |
|----------|--------------|
| First sync | All pages processed, revids stored |
| Same page edited 4 times | Only latest revid processed |
| Sync twice, no changes | Second sync skips (revid unchanged) |
| Sync, edit, sync again | Second sync processes new revid |
| Page deleted | Detected via `rctype=log` or periodic full scan |

### Update Pipeline

```
[Poll recentchanges API]
        |
        v
[Deduplicate by pageid]
        |
        v
[Filter: revid > stored_revid?]
        |
        v
[Fetch full page content]
        |
        v
[Compare content hash (optional)]
        |
        v
[Update Chunks] --> [Regenerate Search Vectors]
        |
        v
[Update Entities] --> [Update Knowledge Graph]
        |
        v
[Store new revid + Log Change]
```

### Processing Queue

After crawling, updated pages are enqueued for asynchronous processing via
the `queue_task()` database function. Each source page can generate multiple
task types:

| Task Type | Processor | Description |
|-----------|-----------|-------------|
| `chunks` | `db/process_chunks.py` | Split content into searchable chunks, generate tsvectors |
| `extensions` | `db/process_extensions.py` | Extract structured metadata and extensions |
| `entities` | `db/process_entities.py` | Extract named entities and relationships |

Processors call `claim_task('<type>')` to atomically claim the next pending
task, preventing duplicate processing in concurrent environments. Each
processor runs independently and can be scheduled or triggered separately.

### Chunk Update Strategy

When a page is modified:
1. **Soft delete** - Mark existing chunks as `outdated`
2. **Re-chunk** - Process new content into chunks
3. **Compare** - Match new chunks to existing where possible (preserve IDs)
4. **Update** - Insert new/modified chunks, remove orphaned ones
5. **Reindex** - Regenerate tsvector for affected chunks

### Knowledge Graph Updates

When entities change:
1. **Re-extract** - Run entity extraction on modified content
2. **Diff** - Compare with existing entities
3. **Merge** - Update existing entities, add new ones
4. **Prune** - Remove relationships no longer supported by content
5. **Validate** - Check graph consistency

## Database Tables

### Tracking Tables

```sql
-- Track source page sync status
CREATE TABLE public.source_pages (
    id integer NOT NULL,
    source_type text NOT NULL,
      -- 'wiki', 'planet', 'wordpress_page', 'wordpress_post'
    source_id integer NOT NULL,
       -- pageid from MediaWiki, post ID from WordPress
    title text NOT NULL,
    url text,
    last_revid integer,      -- Last revision ID we processed
    content_hash text,
        -- SHA256 of content for change detection
    last_synced timestamp without time zone,
        -- When we last synced this page
    status text DEFAULT 'active'::text, -- 'active', 'outdated', 'deleted'
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    content_text text,
    content_html text,
    categories text[]
);

-- Track sync operations
CREATE TABLE public.sync_log (
    id integer NOT NULL,
    sync_type text NOT NULL,   -- 'incremental', 'full'
    source_type text NOT NULL, -- 'wiki', 'planet', 'wordpress'
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    since_timestamp timestamp without time zone,
    pages_checked integer DEFAULT 0,
    pages_updated integer DEFAULT 0,
    pages_created integer DEFAULT 0,
    pages_deleted integer DEFAULT 0,
    pages_skipped integer DEFAULT 0,
    errors text[],            -- Array of error messages
    status text DEFAULT 'running'::text -- 'running', 'completed', 'failed'
);


-- Track individual page updates


CREATE INDEX idx_source_pages_type_id ON source_pages(source_type, source_id);
CREATE INDEX idx_source_pages_status ON source_pages(status);
CREATE INDEX idx_sync_log_started ON sync_log(started_at);
```

## Scheduling

### Recommended Schedule

| Task | Frequency | Description |
|------|-----------|-------------|
| Wiki incremental sync | Daily | Check recentchanges API |
| Planet OSGeo sync | Every 4 hours | Fetch new posts from RSS/Atom feed |
| WordPress sync | Daily | Fetch new/updated pages and posts |
| Full wiki crawl | Monthly | Catch any missed changes, detect deletions |
| Entity re-extraction | Weekly | Refresh entity relationships |
| Database maintenance | Weekly | VACUUM, reindex |

### Cron Examples

```bash
# Daily wiki sync at 2 AM
0 2 * * * cd /path/to/project && python crawler/wiki_sync.py

# Planet OSGeo sync every 4 hours
0 */4 * * * cd /path/to/project && python crawler/planet_sync.py

# WordPress (osgeo.org) sync daily at 3 AM
0 3 * * * cd /path/to/project && python crawler/wordpress_sync.py

# Monthly full crawl on 1st at 4 AM
0 4 1 * * cd /path/to/project && python crawler/crawler.py --full

# Weekly maintenance on Sunday at 5 AM
0 5 * * 0 psql -d osgeo_wiki -c "VACUUM ANALYZE;"
```

## Error Handling

- Retry failed fetches with exponential backoff (max 3 retries)
- Log all failures to `sync_log.errors`
- Continue processing other pages on single-page failure
- Alert on repeated failures (configurable threshold)
- Mark pages as 'error' status after max retries

## WordPress Update Strategy

Similar approach using REST API:

```
https://www.osgeo.org/wp-json/wp/v2/posts?modified_after=2025-12-10T00:00:00Z
```

Track by post ID and `modified` timestamp instead of revid.

## Pipeline Consumer

The MCP server (`osgeo_knowledge.servers.mcp`) is the primary consumer of
this pipeline. It queries the processed chunks, entities, and metadata to
serve search results and knowledge graph lookups to connected clients
(e.g., Claude Desktop, IDE integrations). See `docs/integration.md` for
configuration details.

## Future Considerations

- Webhook integration for real-time updates (if sources support)
- Distributed crawling for large-scale content
- ML-based change significance scoring (skip trivial edits)
- Cross-source entity resolution improvements
