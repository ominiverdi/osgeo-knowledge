# OSGeo Wiki Skill

Search the OSGeo wiki (wiki.osgeo.org) -- 5300+ pages covering projects,
governance, board meetings, local chapters, and community guidelines.

## Tools to use

- osgeo-knowledge_search_wiki with source="wiki"
- osgeo-knowledge_search_content with source="wiki"
- osgeo-knowledge_get_page

## When to use

- "What is QGIS / GDAL / PostGIS / GeoServer?"
- "OSGeo board governance"
- "How to become a charter member"
- "Local chapters in Europe"
- Board meeting minutes, election manifestos

## Date filtering

Both search tools support date_from and date_to (YYYY-MM-DD format)
to narrow results to a time period. Useful for board meetings and
recent changes.

## Example calls

search_wiki(query="QGIS plugins", source="wiki")
search_content(query="charter member requirements", source="wiki")
search_wiki(query="board meeting", source="wiki", date_from="2025-01-01")
get_page(title="Board Meeting 2024-02-27")
