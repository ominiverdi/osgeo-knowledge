# Planet OSGeo Skill

Search Planet OSGeo -- aggregated blog posts and news from the open-source
geospatial community (GeoServer, QGIS, Mappery, GeoSolutions, gvSIG, etc.).

## Tools to use

- osgeo-knowledge_search_wiki with source="planet"
- osgeo-knowledge_search_content with source="planet"

## When to use

- "Latest news from Planet OSGeo"
- "Recent GeoServer blog posts"
- "What's new in the geospatial community"
- Questions about specific blog posts or tutorials

## Date filtering

Both search tools support date_from and date_to (YYYY-MM-DD format)
to narrow results to a time period. Use these for questions like
"what happened in December?" or "latest news this month".

## Example calls

search_wiki(query="QGIS", source="planet")
search_wiki(query="GeoServer", source="planet", date_from="2025-12-01", date_to="2025-12-31")
search_content(query="GeoServer WPS tutorial", source="planet")
search_wiki(query="release", source="planet", date_from="2026-03-01")

## Notes

- Planet posts come from external blogs (geoserver.org, blog.qgis.org,
  mappery.org, camptocamp.com, etc.)
- Content is synced periodically -- may not include the very latest posts
- If no results, suggest the user check https://planet.osgeo.org directly
