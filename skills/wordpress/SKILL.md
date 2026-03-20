# OSGeo Website Skill

Search the OSGeo website (osgeo.org) -- 89 pages covering official
announcements, project descriptions, sponsorship info, and organization pages.

## Tools to use

- osgeo-knowledge_search_wiki with source="wordpress"
- osgeo-knowledge_search_content with source="wordpress"

## When to use

- "What's on the OSGeo website about sponsorship?"
- "OSGeo official project descriptions"
- "How to become an OSGeo sponsor"
- Questions about osgeo.org content specifically

## Date filtering

Both search tools support date_from and date_to (YYYY-MM-DD format)
to narrow results to a time period.

## Example calls

search_wiki(query="sponsorship", source="wordpress")
search_content(query="incubation process", source="wordpress")
search_wiki(query="announcements", source="wordpress", date_from="2025-01-01")
