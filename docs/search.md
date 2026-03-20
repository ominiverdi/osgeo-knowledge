# Search Capabilities

This document describes the search features available in the OSGeo Knowledge Database.

## MCP Search Tools

The primary interface for searching is through two MCP tools exposed by the chat assistant.

### search_wiki

Searches the `page_extensions` table, which contains LLM-generated summaries and extracted keywords for each page. Results are ranked using weighted full-text search across three tsvector columns:

- `resume_tsv` -- summary text
- `keywords_tsv` -- extracted keywords
- `page_title_tsv` -- page title

**Parameters**:
- `query` (required) -- search terms, passed through `websearch_to_tsquery`
- `source` -- filter by origin: `'wiki'`, `'planet'`, or `'wordpress'`
- `date_from` / `date_to` -- date range filter in `YYYY-MM-DD` format
- `limit` -- max results (default 10)

Returns: page title, URL, summary, keywords, last updated date, and relevance rank.

### search_content

Searches the `page_chunks` table for raw crawled content. Returns matching text with `ts_headline` highlights around the query terms.

**Parameters**:
- `query` (required) -- search terms, passed through `websearch_to_tsquery`
- `source` -- filter by origin: `'wiki'`, `'planet'`, or `'wordpress'`
- `date_from` / `date_to` -- date range filter in `YYYY-MM-DD` format
- `limit` -- max results (default 10)

Returns: page title, URL, highlighted text snippet, chunk index, and relevance rank.

---

## Full-Text Search (SQL)

The underlying search uses PostgreSQL full-text search with `websearch_to_tsquery`, which supports natural query syntax including quoted phrases, `OR`, and `-` for exclusion.

### Tables

**page_extensions** -- LLM summaries and keywords per page:
- `resume_tsv`, `keywords_tsv`, `page_title_tsv` (tsvector columns for search)
- `resume`, `keywords`, `page_title` (plain text)
- `url`, `last_updated`

**page_chunks** -- raw crawled content split into chunks:
- `chunk_text` (plain text)
- `tsv` (tsvector for search)
- `page_id`, `chunk_index`

**pages** -- crawled pages:
- `id`, `title`, `url`, `last_crawled`

### Weighted Ranking on page_extensions

Title matches are weighted higher than content matches. The ranking combines all three tsvector columns with PostgreSQL weight labels:

```sql
SELECT page_title, url, resume, keywords, last_updated,
       ts_rank(
           setweight(page_title_tsv, 'A') ||
           setweight(keywords_tsv, 'B') ||
           setweight(resume_tsv, 'C'),
           query
       ) AS rank
FROM page_extensions,
     websearch_to_tsquery('english', 'FOSS4G conference') AS query
WHERE (page_title_tsv || keywords_tsv || resume_tsv) @@ query
ORDER BY rank DESC
LIMIT 10;
```

### Content Search on page_chunks

```sql
SELECT p.title, p.url,
       ts_headline('english', c.chunk_text, query,
                   'StartSel=**, StopSel=**, MaxWords=60, MinWords=20') AS snippet,
       ts_rank(c.tsv, query) AS rank
FROM page_chunks c
JOIN pages p ON p.id = c.page_id,
     websearch_to_tsquery('english', 'spatial database') AS query
WHERE c.tsv @@ query
ORDER BY rank DESC
LIMIT 10;
```

### Features

- Stemming (matches "configure", "configuration", "configured")
- Stop word removal
- Relevance ranking with `ts_rank`
- Phrase matching via quoted strings in `websearch_to_tsquery`
- Snippet generation with `ts_headline`

---

## Entity Search

### Table

**entities**:
- `id`, `entity_name`, `entity_type`
- `url`, `confidence`, `source_page_id`

### Entity Types

`person`, `project`, `organization`, `conference`, `meeting`, `location`, `topic`, `sprint`, `software`, `year`

### Trigram Similarity (pg_trgm)

Fuzzy matching for typo tolerance and partial name matches:

```sql
SELECT entity_name, entity_type, similarity(entity_name, 'QQGIS') AS sim
FROM entities
WHERE entity_name % 'QQGIS'
ORDER BY sim DESC
LIMIT 10;
```

### Exact Entity Lookup

```sql
SELECT entity_name, entity_type, url, confidence
FROM entities
WHERE entity_name ILIKE '%GDAL%'
ORDER BY confidence DESC;
```

---

## Relationship Queries

### Table

**entity_relationships**:
- `id`, `subject_id`, `predicate`, `object_id`
- `source_page_id`, `confidence`

### Common Predicates

`member_of`, `contributes_to`, `located_in`, `happened_in`, `president_of`, `created_by`, `founded_by`, `sponsors`

### Example: Find Contributors to a Project

```sql
SELECT e.entity_name
FROM entities e
JOIN entity_relationships r ON e.id = r.subject_id
WHERE r.object_id = (SELECT id FROM entities WHERE entity_name = 'GDAL')
  AND r.predicate = 'contributes_to';
```

### Example: Find All Relationships for a Person

```sql
SELECT
    subj.entity_name AS subject,
    r.predicate,
    obj.entity_name AS object,
    r.confidence
FROM entity_relationships r
JOIN entities subj ON subj.id = r.subject_id
JOIN entities obj ON obj.id = r.object_id
WHERE subj.entity_name = 'Frank Warmerdam'
   OR obj.entity_name = 'Frank Warmerdam'
ORDER BY r.confidence DESC;
```

---

## Source Filtering

Sources are determined by URL pattern matching on the `pages` table:

| Source    | URL Pattern                        |
|-----------|------------------------------------|
| wiki      | `https://wiki.osgeo.org/%`        |
| wordpress | `https://%osgeo.org/%`            |
| planet    | Everything else                    |

When filtering by source in queries that use `page_extensions` or `page_chunks`, join through `pages` and apply a `WHERE` clause on `pages.url`:

```sql
-- Wiki pages only
WHERE p.url LIKE 'https://wiki.osgeo.org/%'

-- WordPress pages only
WHERE p.url LIKE 'https://%osgeo.org/%'
  AND p.url NOT LIKE 'https://wiki.osgeo.org/%'

-- Planet pages (everything else)
WHERE p.url NOT LIKE 'https://%osgeo.org/%'
```

---

## Indexing

- GIN indexes on all tsvector columns (`resume_tsv`, `keywords_tsv`, `page_title_tsv`, `tsv`)
- GIN index for trigram operations on `entity_name`
- B-tree indexes on foreign keys (`page_id`, `source_page_id`, `subject_id`, `object_id`)

## Performance Notes

- Use `LIMIT` to cap result sets
- `ts_headline` is expensive; use it only for display, not filtering
- `websearch_to_tsquery` is preferred over `plainto_tsquery` for user-facing input
- Source filtering benefits from the B-tree index on `pages.url`
