# RCE CHO SPARQL MCP Server

MCP server waarmee een LLM het RCE Cultureel Erfgoed SPARQL endpoint kan bevragen.
Gebouwd op de CEO ontologie (automatisch geladen van GitHub) en de RCE datamodelregels.

## Remote gebruik (geen installatie nodig)

De server draait publiek op Render en is direct te gebruiken:

```
https://mcp-server-rce-cho-http.onrender.com/mcp
```

### Claude Desktop (via mcp-remote proxy)

```json
{
  "mcpServers": {
    "rce-cho-sparql": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-server-rce-cho-http.onrender.com/mcp"]
    }
  }
}
```

### Cursor

Voeg toe aan `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "rce-cho-sparql": {
      "url": "https://mcp-server-rce-cho-http.onrender.com/mcp"
    }
  }
}
```

### Open WebUI / andere MCP clients

Gebruik de URL direct: `https://mcp-server-rce-cho-http.onrender.com/mcp`

> **Let op:** de server draait op de gratis Render-tier en kan na 15 minuten inactiviteit sluimeren.
> De eerste aanroep na een pauze duurt dan 20-30 seconden.

---

## Lokale installatie

```bash
git clone https://github.com/rschalkrce/MCP-server-RCE-CHO-http.git
cd MCP-server-RCE-CHO-http
pip install -r requirements.txt
python server.py
```

### Koppelen aan Claude Desktop (lokaal)

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "rce-cho-sparql": {
      "command": "python",
      "args": ["/pad/naar/server.py"]
    }
  }
}
```

---

## Beschikbare tools

| Tool | Beschrijving |
|---|---|
| `get_ontology_context` | Geeft de volledige ontologie-context terug (klassen, properties, paden, spelregels). Altijd eerst aanroepen. |
| `query_sparql` | Voert een SPARQL SELECT/ASK query uit op het endpoint |
| `validate_query` | Checkt een query op veelgemaakte fouten vóór uitvoering |
| `describe_resource` | DESCRIBE op een specifieke URI |
| `get_provincie_uri` | Geeft de correcte URI voor een Nederlandse provincie |

## Hoe het werkt

1. LLM roept `get_ontology_context()` aan → krijgt alle klassen, properties en spelregels
2. LLM stelt SPARQL query op op basis van de ontologie
3. LLM roept `validate_query(query)` aan → fouten worden geblokkeerd
4. LLM roept `query_sparql(query)` aan → resultaten uit de brondata
5. LLM presenteert resultaten in mensentaal

## Omgevingsvariabelen

| Variabele | Standaard | Omschrijving |
|---|---|---|
| `SPARQL_ENDPOINT` | RCE CHO endpoint | SPARQL endpoint URL |
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http` of `sse` |
| `CEO_TTL_URL` | GitHub URL | URL naar de CEO ontologie TTL |

## Technische details

- **SPARQL endpoint:** `https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql`
- **Graph:** `https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce`
- **Ontologie:** CEO v1.5, automatisch geladen van [GitHub](https://github.com/cultureelerfgoed/CEO)
- **Licentie:** CC0 1.0

## Bronnen

- [RCE Linked Data](https://linkeddata.cultureelerfgoed.nl)
- [CEO Ontologie](https://github.com/cultureelerfgoed/CEO)
- [SPARQL IDE](https://linkeddata.cultureelerfgoed.nl/rce/cho/sparql)
