# Crawlers

This document describes the content crawlers for fetching data from OSGeo sources.

## Wiki Crawler

**Status**: Implemented

**Location**: `crawler/crawler.py`

### How it works

1. Fetches page list from MediaWiki API
2. Retrieves full content for each page
3. Extracts clean text, removing wiki markup
4. Saves to local dump files for processing

### Usage

```bash
python crawler/crawler.py
```

### Configuration

- Base URL: `https://wiki.osgeo.org`
- Output: `wiki_dump/` directory

### API Endpoints Used

- `api.php?action=query&list=allpages` - List all pages
- `api.php?action=parse&page=X` - Get parsed page content

## WordPress Crawler

**Status**: Implemented (`crawler/wordpress_sync.py`)

### Target Sites

- `https://www.osgeo.org` - Main website
- `https://blog.osgeo.org` - Blog

### Approach

Use WordPress REST API:
- `/wp-json/wp/v2/posts` - Blog posts
- `/wp-json/wp/v2/pages` - Static pages

### Planned Features

- Pagination handling
- Author extraction
- Category/tag mapping
- Featured image references

## Planet OSGeo Crawler

**Status: Implemented** (`crawler/planet_sync.py`)

Syncs blog posts from Planet OSGeo (planet.osgeo.org) RSS feeds into the knowledge base.

### Features
- Fetches posts from multiple blog feeds aggregated by Planet OSGeo
- Creates source_pages entries with source_type='planet_post'
- Prunes old posts (configurable retention)
- Queues new posts for chunk processing and LLM extension generation

### Usage
```bash
# Sync all feeds
python crawler/planet_sync.py --all

# Via cron (every 4 hours)
30 */4 * * * cd $WIKI_BOT && $PYTHON crawler/planet_sync.py --all >> logs/planet_sync.log 2>&1
```

### Sources
Posts come from blogs including: geoserver.org, blog.qgis.org, mappery.org, camptocamp.com, blog.gvsig.org, anitagraser.com, merginmaps.com, and others.

## Common Features

### Implemented

- Direct DB writes to `source_pages` table (all crawlers)
- Processing queue integration via `processing_queue` table
- Rate limiting with configurable delay between requests
- Crawl progress logging and error tracking

### Planned

- Respect robots.txt
- Back-off on errors
- Skip unchanged content (ETag/Last-Modified)
- Generate crawl reports

## Output Format

Crawlers write directly to the database:

- **`source_pages`** -- one row per crawled page/post, with columns for title, URL, content, source_type, and metadata.
- **`processing_queue`** -- new or updated pages are queued here for chunk processing and LLM extension generation.

Source types used:
| Crawler | `source_type` |
|---------|---------------|
| Wiki | `wiki_page` |
| WordPress | `wp_post`, `wp_page` |
| Planet OSGeo | `planet_post` |
