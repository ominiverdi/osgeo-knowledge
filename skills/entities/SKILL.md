# OSGeo Entities Skill

Search the OSGeo knowledge graph -- 20000+ entities (people, projects,
organizations, conferences) and 17000+ relationships between them.

## Tools to use

- osgeo-knowledge_search_entities
- osgeo-knowledge_get_entity_relationships

## When to use

- "Who is [person name]?"
- "Who is the president of OSGeo?"
- "Where was FOSS4G 2023 held?"
- "What projects did Frank Warmerdam create?"
- "List FOSS4G conferences and their locations"
- Any question about relationships between people, projects, and organizations

## Example calls

search_entities(query="strk", entity_type="person")
search_entities(query="FOSS4G 2024")
get_entity_relationships(entity_name="OSGeo", predicate="president_of")
get_entity_relationships(entity_name="FOSS4G", predicate="located_in")

## Tips

- Entity types: person, project, organization, conference, meeting,
  location, topic, sprint, software, year
- Fuzzy matching: typos work ("strk" finds "Sandro Santilli")
- Common predicates: member_of, contributes_to, located_in, happened_in,
  president_of, created_by, founded_by, sponsors
- Combine: search_entities to find someone, then get_entity_relationships
  to see their connections
