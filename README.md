# RCE CHO SPARQL MCP Server

MCP server waarmee een LLM het RCE Cultureel Erfgoed SPARQL endpoint kan bevragen.
Gebouwd op de CEO ontologie v1.5 en de RCE datamodelregels.

## Installatie

```bash
# Kloon of kopieer deze map, dan:
pip install mcp[cli]

# Of installeer als pakket:
pip install -e .
```

## Koppelen aan Claude Desktop

Voeg het volgende toe aan `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "rce-cho-sparql": {
      "command": "python",
      "args": ["/pad/naar/rce-sparql-mcp/server.py"],
      "env": {
        "SPARQL_ENDPOINT": "https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql"
      }
    }
  }
}
```

Herstart Claude Desktop daarna.

## Beschikbare tools

| Tool | Beschrijving |
|---|---|
| `get_ontology_context` | Geeft prefixen, classes, paden, regels en voorbeeldqueries terug. **Altijd eerst aanroepen.** |
| `query_sparql` | Voert een SPARQL SELECT/ASK query uit op het endpoint |
| `validate_query` | Checkt een query op veelgemaakte fouten vóór uitvoering |
| `describe_resource` | DESCRIBE op een specifieke URI |
| `get_provincie_uri` | Geeft de correcte URI voor een Nederlandse provincie |

## Aanbevolen LLM workflow

1. Gebruiker stelt een vraag over erfgoed
2. LLM roept `get_ontology_context()` aan → krijgt alle regels + voorbeelden
3. LLM stelt SPARQL query op
4. LLM roept `validate_query(query)` aan → checkt op fouten
5. LLM roept `query_sparql(query)` aan → haalt resultaten op
6. LLM presenteert resultaten in mensentaal

## Omgevingsvariabelen

| Variabele | Standaard | Omschrijving |
|---|---|---|
| `SPARQL_ENDPOINT` | RCE CHO endpoint | SPARQL endpoint URL |

## Endpoint

```
https://linkeddata.cultureelerfgoed.nl/rce/cho/sparql
```

Publiek beschikbaar, geen authenticatie vereist.
Graph: `https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce`
