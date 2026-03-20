# OSGeo Knowledge Base Skill

You have access to the osgeo-knowledge MCP server -- a PostgreSQL database
containing the full OSGeo wiki (wiki.osgeo.org) with 5700+ pages, 20000+
entities, and 17000+ relationships.

ALWAYS use these tools for questions about OSGeo, its projects, people,
events, governance, or community. Do NOT rely on general knowledge or
web search for OSGeo-specific questions when these tools are available.

## Available tools

- osgeo-knowledge_search_wiki -- PRIMARY search tool. Searches LLM-generated
  summaries and keywords. Best for general questions ("What is QGIS?",
  "Tell me about FOSS4G", "OSGeo board governance").

- osgeo-knowledge_search_content -- Raw wiki text search. Use when search_wiki
  lacks detail, or for specific text/quotes from wiki pages.

- osgeo-knowledge_search_entities -- Find people, projects, organizations,
  events. Fuzzy matching handles typos ("strk" finds "Sandro Santilli").

- osgeo-knowledge_get_entity_relationships -- Knowledge graph queries.
  "Who is president of OSGeo?", "Where was FOSS4G 2023?",
  "What projects did someone contribute to?"
  Common predicates: member_of, contributes_to, located_in, happened_in,
  president_of, created_by, founded_by, sponsors.

- osgeo-knowledge_get_page -- Full wiki page content by title.

- osgeo-knowledge_get_wiki_stats -- Database statistics.

## Search strategy

1. Start with search_wiki for most questions
2. If the answer involves people/orgs/events, also try search_entities
3. For relationship questions ("who is...", "where was..."), use
   get_entity_relationships
4. If summaries lack detail, fall back to search_content
5. Use get_page when you know the exact page title

## Tips

- Entity types: person, project, organization, conference, meeting,
  location, topic, sprint, software, year
- The wiki covers: OSGeo governance, FOSS4G conferences, board meetings,
  project pages (QGIS, GDAL, PostGIS, GeoServer...), local chapters,
  community guidelines, and more
- Combine tools: search_entities to find someone, then
  get_entity_relationships to see their connections
