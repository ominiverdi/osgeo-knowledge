#!/usr/bin/env python3
"""
MCP (Model Context Protocol) server for osgeo-knowledge.

Exposes OSGeo wiki knowledge base search as MCP tools for AI assistants.

Usage:
    # Run directly
    python -m osgeo_knowledge.servers.mcp

    # Or via installed entry point (if added)
    osgeo-knowledge mcp

Available Tools:
    - search_wiki: Semantic search over LLM-generated summaries and keywords
    - search_content: Full-text search over raw wiki page content chunks
    - search_entities: Find people, projects, organizations, events (fuzzy matching)
    - get_entity_relationships: Query relationships between entities
    - get_page: Get full content of a specific wiki page
    - get_wiki_stats: Database statistics and sync status
"""

import logging
import sys
from typing import Optional

# Configure logging to stderr (required for STDIO MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("osgeo_knowledge.mcp")

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("MCP SDK not installed. Install with: pip install 'mcp[cli]'")
    sys.exit(1)

from osgeo_knowledge.db import fetch_all, fetch_one

# Initialize FastMCP server
mcp = FastMCP("osgeo-knowledge")


# -- Tool: search_wiki --------------------------------------------------------


@mcp.tool()
async def search_wiki(query: str, limit: int = 5) -> str:
    """Search the OSGeo wiki knowledge base using LLM-enhanced summaries and keywords.

    This is the primary search tool. It searches over AI-generated page summaries
    and keywords for high-relevance results about OSGeo projects, people, events,
    and governance.

    Good for questions like:
    - "What is QGIS?"
    - "FOSS4G conference locations"
    - "OSGeo board governance"
    - "How to contribute to GDAL"

    Args:
        query: Search query text (natural language or keywords)
        limit: Maximum results to return (1-20, default 5)
    """
    limit = min(max(1, limit), 20)

    sql = """
        SELECT
            pe.page_title,
            pe.url,
            pe.resume,
            pe.keywords,
            (
                0.6 * ts_rank(pe.resume_tsv, websearch_to_tsquery('english', %s)) +
                0.4 * ts_rank(pe.keywords_tsv, websearch_to_tsquery('english', %s)) +
                CASE WHEN pe.page_title_tsv @@ websearch_to_tsquery('english', %s)
                     THEN 1.1 ELSE 0 END
            ) AS rank
        FROM page_extensions pe
        WHERE
            pe.resume_tsv @@ websearch_to_tsquery('english', %s)
            OR pe.keywords_tsv @@ websearch_to_tsquery('english', %s)
            OR pe.page_title_tsv @@ websearch_to_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT %s
    """

    try:
        results = fetch_all(sql, (query, query, query, query, query, query, limit), limit=limit)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return f"No results found for: {query}"

    lines = [f"Found {len(results)} results for: {query}\n"]
    for i, r in enumerate(results, 1):
        title = r["page_title"]
        url = r["url"]
        summary = (r["resume"] or "")[:400]
        keywords = (r["keywords"] or "")[:200]
        score = r["rank"]
        lines.append(
            f"[{i}] {title}\n"
            f"  URL: {url}\n"
            f"  Score: {score:.3f}\n"
            f"  Summary: {summary}\n"
            f"  Keywords: {keywords}"
        )

    return "\n\n".join(lines)


# -- Tool: search_content -----------------------------------------------------


@mcp.tool()
async def search_content(query: str, limit: int = 5) -> str:
    """Search the raw wiki page content for detailed information.

    Use this when search_wiki doesn't find enough detail, or when you need
    the actual wiki text rather than summaries. Searches over page content
    chunks with full-text matching and highlights.

    Args:
        query: Search query text
        limit: Maximum results to return (1-20, default 5)
    """
    limit = min(max(1, limit), 20)

    sql = """
        SELECT
            p.title,
            p.url,
            ts_headline(
                'english', pc.chunk_text,
                websearch_to_tsquery('english', %s),
                'MaxFragments=2, MaxWords=40, MinWords=10, StartSel=**, StopSel=**'
            ) AS highlight,
            ts_rank(
                setweight(to_tsvector('english', p.title), 'A') ||
                setweight(pc.tsv, 'C'),
                websearch_to_tsquery('english', %s)
            ) AS rank
        FROM page_chunks pc
        JOIN pages p ON pc.page_id = p.id
        WHERE
            pc.tsv @@ websearch_to_tsquery('english', %s)
            OR to_tsvector('english', p.title) @@ websearch_to_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT %s
    """

    try:
        results = fetch_all(sql, (query, query, query, query, limit), limit=limit)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return f"No content found for: {query}"

    lines = [f"Found {len(results)} content matches for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] {r['title']}\n"
            f"  URL: {r['url']}\n"
            f"  Score: {r['rank']:.4f}\n"
            f"  Content: {r['highlight']}"
        )

    return "\n\n".join(lines)


# -- Tool: search_entities ----------------------------------------------------


@mcp.tool()
async def search_entities(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search for entities (people, projects, organizations, events) in the OSGeo knowledge base.

    Uses fuzzy matching (trigram similarity) so typos and partial names work.

    Args:
        query: Entity name to search for (e.g., "strk", "QGIS", "FOSS4G 2023")
        entity_type: Optional filter: 'person', 'project', 'organization', 'event', 'year'
        limit: Maximum results (1-30, default 10)
    """
    limit = min(max(1, limit), 30)

    if entity_type:
        sql = """
            SELECT
                entity_name,
                entity_type,
                description,
                aliases,
                similarity(entity_name, %s) AS sim
            FROM entities
            WHERE entity_type = %s
              AND (entity_name %% %s OR entity_name ILIKE %s)
            ORDER BY sim DESC
            LIMIT %s
        """
        like_pattern = f"%{query}%"
        params = (query, entity_type, query, like_pattern, limit)
    else:
        sql = """
            SELECT
                entity_name,
                entity_type,
                description,
                aliases,
                similarity(entity_name, %s) AS sim
            FROM entities
            WHERE entity_name %% %s OR entity_name ILIKE %s
            ORDER BY sim DESC
            LIMIT %s
        """
        like_pattern = f"%{query}%"
        params = (query, query, like_pattern, limit)

    try:
        results = fetch_all(sql, params, limit=limit)
    except Exception as e:
        return f"Entity search error: {e}"

    if not results:
        type_filter = f" of type '{entity_type}'" if entity_type else ""
        return f"No entities{type_filter} found matching: {query}"

    lines = [f"Found {len(results)} entities matching: {query}\n"]
    for i, r in enumerate(results, 1):
        desc = r["description"] or "No description"
        aliases_list = r.get("aliases") or []
        aliases_str = f"  Aliases: {', '.join(aliases_list)}" if aliases_list else ""
        lines.append(
            f"[{i}] {r['entity_name']} ({r['entity_type']})\n"
            f"  Similarity: {r['sim']:.2f}\n"
            f"  Description: {desc[:300]}" + (f"\n{aliases_str}" if aliases_str else "")
        )

    return "\n\n".join(lines)


# -- Tool: get_entity_relationships -------------------------------------------


@mcp.tool()
async def get_entity_relationships(
    entity_name: str,
    predicate: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Get relationships for an entity in the OSGeo knowledge graph.

    Returns subject-predicate-object triples. Useful for questions like:
    - "Who is the president of OSGeo?" (predicate: president_of)
    - "Where was FOSS4G 2023 held?" (predicate: located_in)
    - "What projects did Frank Warmerdam create?" (predicate: created_by)

    Common predicates: member_of, contributes_to, part_of, located_in,
    happened_in, president_of, created_by, founded_by, sponsors.

    Args:
        entity_name: Entity name to look up (fuzzy matched)
        predicate: Optional filter by relationship type
        limit: Maximum results (1-50, default 20)
    """
    limit = min(max(1, limit), 50)

    if predicate:
        sql = """
            SELECT
                e1.entity_name AS subject,
                e1.entity_type AS subject_type,
                er.predicate,
                e2.entity_name AS object,
                e2.entity_type AS object_type,
                er.confidence
            FROM entity_relationships er
            JOIN entities e1 ON er.subject_id = e1.id
            JOIN entities e2 ON er.object_id = e2.id
            WHERE (e1.entity_name ILIKE %s OR e2.entity_name ILIKE %s)
              AND er.predicate = %s
            ORDER BY er.confidence DESC
            LIMIT %s
        """
        like_pattern = f"%{entity_name}%"
        params = (like_pattern, like_pattern, predicate, limit)
    else:
        sql = """
            SELECT
                e1.entity_name AS subject,
                e1.entity_type AS subject_type,
                er.predicate,
                e2.entity_name AS object,
                e2.entity_type AS object_type,
                er.confidence
            FROM entity_relationships er
            JOIN entities e1 ON er.subject_id = e1.id
            JOIN entities e2 ON er.object_id = e2.id
            WHERE e1.entity_name ILIKE %s OR e2.entity_name ILIKE %s
            ORDER BY er.confidence DESC
            LIMIT %s
        """
        like_pattern = f"%{entity_name}%"
        params = (like_pattern, like_pattern, limit)

    try:
        results = fetch_all(sql, params, limit=limit)
    except Exception as e:
        return f"Relationship query error: {e}"

    if not results:
        pred_str = f" with predicate '{predicate}'" if predicate else ""
        return f"No relationships found for '{entity_name}'{pred_str}"

    lines = [f"Found {len(results)} relationships for: {entity_name}\n"]
    for i, r in enumerate(results, 1):
        conf = f" (confidence: {r['confidence']:.2f})" if r["confidence"] < 1.0 else ""
        lines.append(
            f"[{i}] {r['subject']} ({r['subject_type']}) "
            f"--[{r['predicate']}]--> "
            f"{r['object']} ({r['object_type']}){conf}"
        )

    return "\n\n".join(lines)


# -- Tool: get_page -----------------------------------------------------------


@mcp.tool()
async def get_page(title: str) -> str:
    """Get the content of a specific OSGeo wiki page by title.

    Looks up a page by exact or fuzzy title match and returns the full
    content, categories, and any associated entities.

    Args:
        title: Page title to look up (e.g., "QGIS", "FOSS4G 2023", "Board Meeting 2024-02-27")
    """
    # Try exact match first
    page = fetch_one(
        "SELECT id, title, url FROM pages WHERE title ILIKE %s",
        (title,),
    )

    # Fall back to fuzzy search
    if not page:
        page = fetch_one(
            """SELECT id, title, url FROM pages
               WHERE title ILIKE %s
               ORDER BY length(title) ASC
               LIMIT 1""",
            (f"%{title}%",),
        )

    if not page:
        return f"No page found matching: {title}"

    page_id = page["id"]

    # Get content chunks
    chunks = fetch_all(
        """SELECT chunk_text FROM page_chunks
           WHERE page_id = %s ORDER BY chunk_index""",
        (page_id,),
        limit=100,
    )

    # Get categories
    categories = fetch_all(
        "SELECT category_name FROM page_categories WHERE page_id = %s",
        (page_id,),
        limit=50,
    )

    # Get summary if available
    extension = fetch_one(
        "SELECT resume, keywords FROM page_extensions WHERE url = %s",
        (page["url"],),
    )

    # Build output
    lines = [
        f"Page: {page['title']}",
        f"URL: {page['url']}",
    ]

    if categories:
        cat_names = [c["category_name"] for c in categories]
        lines.append(f"Categories: {', '.join(cat_names)}")

    if extension:
        lines.append(f"\nSummary: {extension['resume']}")
        lines.append(f"Keywords: {extension['keywords']}")

    if chunks:
        content = "\n".join(c["chunk_text"] for c in chunks)
        # Truncate if very long
        if len(content) > 4000:
            content = content[:4000] + "\n... [truncated, page has more content]"
        lines.append(f"\nContent:\n{content}")
    else:
        lines.append("\nNo content chunks available for this page.")

    return "\n".join(lines)


# -- Tool: get_wiki_stats -----------------------------------------------------


@mcp.tool()
async def get_wiki_stats() -> str:
    """Get statistics about the OSGeo wiki knowledge base.

    Returns counts of pages, content chunks, entities, relationships,
    and LLM-generated extensions. Useful for understanding the scope
    of available knowledge.
    """
    stats = {}

    queries = {
        "pages": "SELECT COUNT(*) AS count FROM pages",
        "content_chunks": "SELECT COUNT(*) AS count FROM page_chunks",
        "categories": "SELECT COUNT(DISTINCT category_name) AS count FROM page_categories",
        "entities": "SELECT COUNT(*) AS count FROM entities",
        "relationships": "SELECT COUNT(*) AS count FROM entity_relationships",
        "extensions": "SELECT COUNT(*) AS count FROM page_extensions",
    }

    for name, sql in queries.items():
        try:
            row = fetch_one(sql)
            stats[name] = row["count"] if row else 0
        except Exception:
            stats[name] = "error"

    # Entity type breakdown
    try:
        type_rows = fetch_all(
            "SELECT entity_type, COUNT(*) AS count FROM entities GROUP BY entity_type ORDER BY count DESC"
        )
        entity_types = {r["entity_type"]: r["count"] for r in type_rows}
    except Exception:
        entity_types = {}

    # Last sync info
    try:
        last_sync = fetch_one(
            """SELECT sync_type, source_type, started_at, pages_updated, pages_created, status
               FROM sync_log ORDER BY started_at DESC LIMIT 1"""
        )
    except Exception:
        last_sync = None

    lines = [
        "OSGeo Wiki Knowledge Base Statistics",
        "=" * 40,
        f"Pages:          {stats['pages']}",
        f"Content chunks: {stats['content_chunks']}",
        f"Categories:     {stats['categories']}",
        f"Entities:       {stats['entities']}",
        f"Relationships:  {stats['relationships']}",
        f"Extensions:     {stats['extensions']} (LLM summaries)",
    ]

    if entity_types:
        lines.append("\nEntities by type:")
        for etype, count in entity_types.items():
            lines.append(f"  {etype}: {count}")

    if last_sync:
        lines.append(
            f"\nLast sync: {last_sync['started_at']} ({last_sync['sync_type']}, {last_sync['source_type']})"
        )
        lines.append(
            f"  Status: {last_sync['status']}, Updated: {last_sync['pages_updated']}, Created: {last_sync['pages_created']}"
        )

    return "\n".join(lines)


# -- CLI entry point -----------------------------------------------------------


def main():
    """Run the MCP server."""
    logger.info("Starting osgeo-knowledge MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
