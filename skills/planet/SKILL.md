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

## Example calls

search_wiki(query="QGIS", source="planet")
search_content(query="GeoServer WPS tutorial", source="planet")

## Notes

- Planet posts come from external blogs (geoserver.org, blog.qgis.org,
  mappery.org, camptocamp.com, etc.)
- Content is synced periodically -- may not include the very latest posts
- If no results, suggest the user check https://planet.osgeo.org directly
