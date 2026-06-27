"""
RCE CHO SPARQL MCP Server
Stelt een LLM in staat om het RCE Cultureel Erfgoed endpoint te bevragen
via MCP tools met ingebouwde ontologie-kennis.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────
# Configuratie
# ──────────────────────────────────────────────

SPARQL_ENDPOINT = os.getenv(
    "SPARQL_ENDPOINT",
    "https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql"
)

CEO_TTL_URL = os.getenv(
    "CEO_TTL_URL",
    "https://raw.githubusercontent.com/cultureelerfgoed/CEO/refs/heads/master/CEO_RCE.ttl"
)

def _load_ttl_context(url: str) -> str:
    """Extraheer klassen en properties uit de CEO TTL via GitHub."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCE-MCP/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        return f"[TTL kon niet worden geladen: {e} — alleen datamodelregels beschikbaar]"

    class_matches = sorted(set(re.findall(r'(ceo:\w+)\s*\n\s*rdf:type owl:Class', content)))
    blocks = re.split(r'\n(?=ceo:\w+\s*\n\s*rdf:type owl:)', content)
    op_info, dp_info = {}, {}

    for block in blocks:
        name_match = re.match(r'(ceo:\w+)', block)
        if not name_match:
            continue
        name = name_match.group(1)
        is_op = 'owl:ObjectProperty' in block[:200]
        is_dp = 'owl:DatatypeProperty' in block[:200]
        domain = re.search(r'rdfs:domain\s+(ceo:\w+)', block)
        range_ = re.search(r'rdfs:range\s+(ceo:\w+|xsd:\w+)', block)
        d = domain.group(1) if domain else '?'
        r = range_.group(1) if range_ else '?'
        if is_op:
            op_info[name] = {'domain': d, 'range': r}
        elif is_dp:
            dp_info[name] = {'domain': d, 'range': r}

    lines = ["=== ONTOLOGIE (automatisch geladen uit CEO_RCE.ttl) ===", ""]
    lines.append(f"KLASSEN ({len(class_matches)}):")
    for c in class_matches:
        lines.append(f"  {c}")
    lines.append("")
    lines.append(f"OBJECTPROPERTIES ({len(op_info)}) — domain → range:")
    for p, v in sorted(op_info.items()):
        lines.append(f"  {p}  [{v['domain']} → {v['range']}]")
    lines.append("")
    lines.append(f"DATATYPEPROPERTIES ({len(dp_info)}) — domain → type:")
    for p, v in sorted(dp_info.items()):
        lines.append(f"  {p}  [{v['domain']} → {v['range']}]")

    return '\n'.join(lines)

TTL_CONTEXT = _load_ttl_context(CEO_TTL_URL)

WORKFLOW_INSTRUCTIONS = (
    "Je bent een specialist in het RCE Cultureel Erfgoed SPARQL endpoint. "
    "Je volgt ALTIJD deze vaste volgorde — geen uitzonderingen:\n\n"
    "STAP 1 — get_ontology_context()\n"
    "  Roep dit aan aan het begin van ELKE nieuwe vraag over erfgoeddata. "
    "  Sla deze stap nooit over, ook niet als je denkt de ontologie al te kennen. "
    "  Zonder deze stap mag je geen query opstellen.\n\n"
    "STAP 2 — Stel de SPARQL query op\n"
    "  Gebruik uitsluitend de classes, properties en paden uit de ontologie-context. "
    "  Verzin nooit classes of properties. "
    "  Voeg altijd FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce> toe.\n\n"
    "STAP 3 — validate_query(query)\n"
    "  Valideer de query voordat je hem uitvoert. "
    "  Los alle fouten (gemarkeerd met x) op voor je doorgaat naar stap 4. "
    "  Bij fouten: pas de query aan en valideer opnieuw.\n\n"
    "STAP 4 — query_sparql(query)\n"
    "  Voer de gevalideerde query uit. "
    "  Bij een HTTP-fout of leeg resultaat: herzie de query en begin opnieuw bij stap 2.\n\n"
    "STAP 5 — Presenteer de resultaten\n"
    "  Vertaal de resultaten naar begrijpelijke Nederlandse tekst voor de gebruiker. "
    "  Vermeld het aantal gevonden resultaten en eventuele beperkingen.\n\n"
    "VERBODEN:\n"
    "  - query_sparql() aanroepen zonder voorafgaande get_ontology_context()\n"
    "  - query_sparql() aanroepen zonder voorafgaande validate_query()\n"
    "  - Classes of properties verzinnen die niet in de ontologie staan\n"
    "  - De FROM-clause weglaten\n"
    "  - Prefixen ceosp: of ceox: gebruiken"
)

mcp = FastMCP("RCE CHO SPARQL", instructions=WORKFLOW_INSTRUCTIONS)

# ──────────────────────────────────────────────
# Ingebouwde ontologie-context (uit CEO_RCE.ttl + datamodel_rules.txt)
# ──────────────────────────────────────────────

ONTOLOGY_CONTEXT = """
=== RCE CHO ONTOLOGIE-CONTEXT ===

ENDPOINT
  https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql
  Gebruik altijd: FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>

PREFIXEN (gebruik alleen deze)
  PREFIX graph: <https://linkeddata.cultureelerfgoed.nl/graph/>
  PREFIX ceo:   <https://linkeddata.cultureelerfgoed.nl/def/ceo#>
  PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
  PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
  PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
  PREFIX geo:   <http://www.opengis.net/ont/geosparql#>
  PREFIX geof:  <http://www.opengis.net/def/function/geosparql/>

VERBODEN prefixen: ceosp:  ceox:

──────────────────────────────────────────────
HOOFDCLASSES
──────────────────────────────────────────────
  ceo:Rijksmonument            - beschermd rijksmonument
  ceo:Complex                  - monumentencomplex
  ceo:ArcheologischComplex     - archeologisch complex
  ceo:ArcheologischTerrein     - archeologisch terrein
  ceo:ArcheologischOnderzoeksgebied
  ceo:Vondstlocatie
  ceo:Vondsten
  ceo:Grondsporen
  ceo:BasisregistratieRelatie
  ceo:BAGRelatie
  ceo:BRKRelatie
  ceo:Naam
  ceo:Omschrijving
  ceo:LocatieAanduiding
  ceo:Functie
  ceo:Type
  ceo:Gebeurtenis
  ceo:Materiaal
  ceo:Geometrie
  ceo:Kennisregistratie
  ceo:ActorEnRol
  ceo:StijlEnCultuur
  ceo:Werelderfgoed
  ceo:Gezicht

VERBODEN classnamen (gebruik nooit):
  ceo:Rijksmonumenten  ceo:ArcheologischeComplexen  ceo:Vondst

──────────────────────────────────────────────
PADEN NAAR LITERALS (altijd volledig uitschrijven)
──────────────────────────────────────────────
Naam:
  ?cho ceo:heeftNaam ?naamNode . ?naamNode ceo:naam ?naam .

Omschrijving:
  ?cho ceo:heeftOmschrijving ?omschrijvingNode . ?omschrijvingNode ceo:omschrijving ?omschrijving .

Geometrie:
  ?cho ceo:heeftGeometrie ?geo . ?geo geo:asWKT ?wkt .

Rijksmonumentnummer:
  ?rm ceo:rijksmonumentnummer ?nummer .   (xsd:string)

Monumentaard:
  ?rm ceo:heeftMonumentAard ?aardConcept . ?aardConcept skos:prefLabel ?aard .

Juridische status:
  ?rm ceo:heeftJuridischeStatus ?statusConcept . ?statusConcept skos:prefLabel ?status .

Oorspronkelijke functie:
  ?rm ceo:heeftOorspronkelijkeFunctie ?fObj . ?fObj ceo:heeftFunctieNaam ?fConcept . ?fConcept skos:prefLabel ?fLabel .

Huidige functie:
  ?rm ceo:heeftHuidigeFunctie ?fObj . ?fObj ceo:heeftFunctieNaam ?fConcept . ?fConcept skos:prefLabel ?fLabel .

Type (via Kennisregistratie):
  ?rm ceo:heeftKennisregistratie ?tObj . ?tObj a ceo:Type .
  ?tObj ceo:heeftTypeNaam ?tConcept . ?tConcept skos:prefLabel ?tLabel .

Actor/rol (architect etc.):
  ?rm ceo:heeftGebeurtenis ?geb . ?geb ceo:heeftActorEnRol ?ar .
  ?ar ceo:heeftActor ?actor . ?ar ceo:heeftRol ?rol .

Provincie (via BasisregistratieRelatie):
  ?cho ceo:heeftBasisregistratieRelatie ?rel . ?rel ceo:heeftProvincie <PROVINCIE_URI> .

Gemeente (via BRKRelatie):
  ?cho ceo:heeftBasisregistratieRelatie ?rel . ?rel ceo:heeftBRKRelatie ?brk . ?brk ceo:gemeentenaam ?gemeente .

Adres/woonplaats (via BAGRelatie):
  ?cho ceo:heeftBasisregistratieRelatie ?rel . ?rel ceo:heeftBAGRelatie ?bag .
  OPTIONAL { ?bag ceo:woonplaatsnaam ?woonplaats . }
  OPTIONAL { ?bag ceo:volledigAdres ?adres . }

──────────────────────────────────────────────
PROVINCIE URI'S
──────────────────────────────────────────────
  Drenthe:       <http://standaarden.overheid.nl/owms/terms/Drenthe>
  Flevoland:     <http://standaarden.overheid.nl/owms/terms/Flevoland>
  Fryslân:       <http://standaarden.overheid.nl/owms/terms/Fryslan>
  Gelderland:    <http://standaarden.overheid.nl/owms/terms/Gelderland>
  Groningen:     <http://standaarden.overheid.nl/owms/terms/Groningen_(provincie)>
  Limburg:       <http://standaarden.overheid.nl/owms/terms/Limburg>
  Noord-Brabant: <http://standaarden.overheid.nl/owms/terms/Noord-Brabant>
  Noord-Holland: <http://standaarden.overheid.nl/owms/terms/Noord-Holland>
  Overijssel:    <http://standaarden.overheid.nl/owms/terms/Overijssel>
  Utrecht:       <http://standaarden.overheid.nl/owms/terms/Utrecht_(provincie)>
  Zeeland:       <http://standaarden.overheid.nl/owms/terms/Zeeland_(provincie)>
  Zuid-Holland:  <http://standaarden.overheid.nl/owms/terms/Zuid-Holland>

──────────────────────────────────────────────
SEMANTISCHE MAPPING
──────────────────────────────────────────────
  "gezicht" / "stadsgezicht" / "dorpsgezicht"  → ceo:Gezicht
  "werelderfgoed" / "UNESCO"                   → ceo:Werelderfgoed
  "internationaal kenteken" / "blauw-wit schildje" → ?cho ceo:internationaalKenteken true .
  "architect" / "ontwerper"                    → ceo:Gebeurtenis + ceo:ActorEnRol, FILTER op rol
  "archeologisch rijksmonument"                → ceo:Rijksmonument + ceo:heeftMonumentAard skos:prefLabel "archeologisch"
  "gebouwd rijksmonument"                      → ceo:Rijksmonument + ceo:heeftMonumentAard skos:prefLabel "onroerend gebouwd"

──────────────────────────────────────────────
SPELREGELS
──────────────────────────────────────────────
  - Gebruik ALTIJD FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>
  - Gebruik SELECT DISTINCT bij lijstqueries met joins
  - Gebruik COUNT(DISTINCT ?hoofdobject) bij tellingen met joins
  - Zet verplichte filterpaden NOOIT in OPTIONAL
  - Gebruik GEEN lang(), LANGMATCHES(), of @nl filters
  - Verzin geen classes of properties buiten deze lijst
  - Bij functie/type zoekvragen: gebruik UNION-blok over oorspronkelijke + huidige functie + type
  - ceo:heeft... → verwijst naar een URI/node, nooit direct filteren als tekst
  - Navigatie omlaag: ceo:bevatObject; omhoog: ceo:ligtInObject
  - Ruimtelijk: gebruik geof:sfWithin of geof:sfIntersects, NOOIT ceo:ligtInObject voor gezichten

──────────────────────────────────────────────
VERBODEN PROPERTIES (nooit gebruiken)
──────────────────────────────────────────────
  ceosp:heeftProvincie  ceox:heeftProvincie  ceox:heeftAdresgegevens
  ceo:heeftPlaats  ceo:heeftGemeente  ceo:heeftAdres  ceo:heeftArchitect
  ceo:heeftFunctie  ceo:ligtInObject (voor gezichten)
  ceo:heeftFunctieNaam direct op hoofdobject
  ceo:heeftTypeNaam direct op hoofdobject
"""

EXAMPLE_QUERIES = """
──────────────────────────────────────────────
VOORBEELDQUERIES
──────────────────────────────────────────────

1. Rijksmonumenten met naam en adres in Utrecht:
SELECT DISTINCT ?rm ?nummer ?naam ?adres
FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>
WHERE {
  ?rm a ceo:Rijksmonument .
  ?rm ceo:rijksmonumentnummer ?nummer .
  OPTIONAL { ?rm ceo:heeftNaam ?nNode . ?nNode ceo:naam ?naam . }
  ?rm ceo:heeftBasisregistratieRelatie ?rel .
  ?rel ceo:heeftProvincie <http://standaarden.overheid.nl/owms/terms/Utrecht_(provincie)> .
  ?rel ceo:heeftBAGRelatie ?bag .
  OPTIONAL { ?bag ceo:volledigAdres ?adres . }
}
LIMIT 10

2. Kerken (functie of type):
SELECT DISTINCT ?rm ?nummer ?naam ?functieLabel ?bron
FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>
WHERE {
  ?rm a ceo:Rijksmonument .
  ?rm ceo:rijksmonumentnummer ?nummer .
  OPTIONAL { ?rm ceo:heeftNaam ?nNode . ?nNode ceo:naam ?naam . }
  {
    { ?rm ceo:heeftOorspronkelijkeFunctie ?fObj . ?fObj ceo:heeftFunctieNaam ?fC . ?fC skos:prefLabel ?functieLabel .
      FILTER(CONTAINS(LCASE(STR(?functieLabel)), "kerk")) BIND("oorspronkelijk" AS ?bron) }
    UNION
    { ?rm ceo:heeftHuidigeFunctie ?fObj . ?fObj ceo:heeftFunctieNaam ?fC . ?fC skos:prefLabel ?functieLabel .
      FILTER(CONTAINS(LCASE(STR(?functieLabel)), "kerk")) BIND("huidig" AS ?bron) }
    UNION
    { ?rm ceo:heeftKennisregistratie ?tObj . ?tObj a ceo:Type .
      ?tObj ceo:heeftTypeNaam ?tC . ?tC skos:prefLabel ?functieLabel .
      FILTER(CONTAINS(LCASE(STR(?functieLabel)), "kerk")) BIND("type" AS ?bron) }
  }
}
LIMIT 20

3. Rijksmonumenten binnen een beschermd gezicht (ruimtelijk):
SELECT DISTINCT ?rm ?nummer ?naam
FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>
WHERE {
  ?gezicht a ceo:Gezicht .
  ?gezicht ceo:heeftNaam ?gnNode . ?gnNode ceo:naam ?gezichtsnaam .
  FILTER(CONTAINS(LCASE(STR(?gezichtsnaam)), "amsterdam"))
  ?gezicht ceo:heeftGeometrie ?gGeo . ?gGeo geo:asWKT ?gWkt .
  ?rm a ceo:Rijksmonument .
  ?rm ceo:rijksmonumentnummer ?nummer .
  OPTIONAL { ?rm ceo:heeftNaam ?nNode . ?nNode ceo:naam ?naam . }
  ?rm ceo:heeftGeometrie ?rmGeo . ?rmGeo geo:asWKT ?rmWkt .
  FILTER(geof:sfWithin(?rmWkt, ?gWkt))
}
LIMIT 20
"""


# ──────────────────────────────────────────────
# Hulpfunctie: SPARQL query uitvoeren
# ──────────────────────────────────────────────

def _execute_sparql(query: str, timeout: int = 30) -> dict:
    """Voer een SPARQL query uit en retourneer het JSON-resultaat."""
    params = urllib.parse.urlencode({"query": query})
    url = f"{SPARQL_ENDPOINT}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "RCE-MCP/1.0",
        }
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def _format_results(data: dict, max_rows: int = 100) -> str:
    """Zet SPARQL JSON-resultaat om naar leesbare tekst."""
    if "boolean" in data:
        return f"Resultaat: {data['boolean']}"

    bindings = data.get("results", {}).get("bindings", [])
    variables = data.get("head", {}).get("vars", [])

    if not bindings:
        return "Geen resultaten gevonden."

    total = len(bindings)
    rows = bindings[:max_rows]

    lines = [f"Gevonden: {total} resultaat/resultaten (max {max_rows} getoond)\n"]
    lines.append(" | ".join(variables))
    lines.append("-" * 60)

    for row in rows:
        values = []
        for var in variables:
            cell = row.get(var, {})
            values.append(cell.get("value", "—"))
        lines.append(" | ".join(values))

    return "\n".join(lines)


# ──────────────────────────────────────────────
# MCP TOOLS
# ──────────────────────────────────────────────

@mcp.tool()
def get_ontology_context(include_examples: bool = True) -> str:
    """
    Geeft de volledige ontologie-context van het RCE CHO endpoint terug:
    - Klassen en properties (automatisch uit CEO_RCE.ttl via GitHub)
    - Prefixen, paden, spelregels en semantische mapping (datamodelregels)
    - Voorbeeldqueries

    Roep dit ALTIJD aan voordat je een SPARQL query opstelt.

    Args:
        include_examples: Voeg voorbeeldqueries toe (standaard: True)
    """
    result = TTL_CONTEXT + "\n\n" + ONTOLOGY_CONTEXT
    if include_examples:
        result += "\n" + EXAMPLE_QUERIES
    return result


@mcp.tool()
def query_sparql(sparql_query: str, max_rows: int = 100) -> str:
    """
    Voer een SPARQL SELECT of ASK query uit op het RCE CHO endpoint.

    VERPLICHTE WORKFLOW — deze tool weigert queries met bekende fouten:
      1. Roep eerst get_ontology_context() aan
      2. Roep dan validate_query() aan en los alle fouten op
      3. Roep dan pas deze tool aan

    Endpoint: https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql
    Graph:    https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce

    Args:
        sparql_query: Volledige SPARQL query (inclusief PREFIX-declaraties en FROM)
        max_rows:     Maximum aantal rijen om terug te geven (standaard 100)
    """
    # ── Ingebouwde validatie: query wordt geweigerd bij bekende fouten ──
    blokkerende_fouten = []
    q = sparql_query

    if "ceosp:" in q:
        blokkerende_fouten.append("Verboden prefix 'ceosp:' aanwezig.")
    if "ceox:" in q:
        blokkerende_fouten.append("Verboden prefix 'ceox:' aanwezig.")
    import re as _re
    for cls in ["ceo:Rijksmonumenten", "ceo:ArcheologischeComplexen", "ceo:ArcheologischeTerreinen", "ceo:Vondst"]:
        if _re.search(r'\b' + _re.escape(cls) + r'\b', q):
            blokkerende_fouten.append(f"Verboden classnaam '{cls.strip()}' — gebruik enkelvoud.")
    for prop in ["ceosp:heeftProvincie", "ceox:heeftProvincie", "ceox:heeftAdresgegevens",
                 "ceo:heeftPlaats", "ceo:heeftGemeente", "ceo:heeftAdres",
                 "ceo:heeftArchitect", "ceo:heeftFunctie"]:
        if _re.search(r'\b' + _re.escape(prop) + r'\b', q):
            blokkerende_fouten.append(f"Verboden property '{prop}' aanwezig.")
    if "FROM" not in q.upper():
        blokkerende_fouten.append(
            "Ontbrekende FROM-clause. Voeg toe: "
            "FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>"
        )
    for term in ["lang(", "LANG(", "LANGMATCHES(", "langmatches(", "@nl"]:
        if term in q:
            blokkerende_fouten.append(f"Verboden taalfilter '{term}' aanwezig.")

    if blokkerende_fouten:
        foutlijst = "\n".join(f"  - {f}" for f in blokkerende_fouten)
        return (
            "QUERY GEWEIGERD — los de volgende fouten op en roep validate_query() "
            "aan voordat je deze tool opnieuw aanroept:\n\n"
            f"{foutlijst}\n\n"
            "Raadpleeg get_ontology_context() voor de juiste classes, properties en paden."
        )

    # ── Query uitvoeren ──
    try:
        data = _execute_sparql(sparql_query)
        return _format_results(data, max_rows=max_rows)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return (
            f"HTTP fout {e.code} van endpoint {SPARQL_ENDPOINT}: {e.reason}\n\n"
            f"Endpoint antwoord:\n{body[:1000]}\n\n"
            "Controleer de query-syntaxis en raadpleeg get_ontology_context()."
        )
    except urllib.error.URLError as e:
        return f"Verbindingsfout met {SPARQL_ENDPOINT}: {e.reason}"
    except json.JSONDecodeError as e:
        return f"Kon het antwoord niet parsen als JSON: {e}"
    except Exception as e:
        return f"Onverwachte fout: {type(e).__name__}: {e}"


@mcp.tool()
def describe_resource(uri: str) -> str:
    """
    Haal alle bekende triples op voor een specifieke URI (DESCRIBE query).
    Handig om een individueel object te inspecteren.

    Args:
        uri: Volledige URI van het te beschrijven object,
             bijv. https://linkeddata.cultureelerfgoed.nl/cho-kennis/id/rijksmonument/12345
    """
    query = f"""DESCRIBE <{uri}>
FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>"""
    try:
        # DESCRIBE geeft Turtle/N-Triples terug, geen JSON
        params = urllib.parse.urlencode({"query": query})
        url = f"{SPARQL_ENDPOINT}?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/turtle",
                "User-Agent": "RCE-MCP/1.0",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"Fout bij DESCRIBE: {type(e).__name__}: {e}"


@mcp.tool()
def validate_query(sparql_query: str) -> str:
    """
    Controleer een SPARQL query op veelgemaakte fouten volgens de
    RCE datamodelregels, zonder de query daadwerkelijk uit te voeren.

    Checks:
    - Gebruik van verboden prefixen (ceosp:, ceox:)
    - Gebruik van verboden properties
    - Ontbrekende FROM clause
    - Verboden classnamen (meervoud)
    - Gebruik van lang() / LANGMATCHES() / @nl

    Args:
        sparql_query: De te valideren SPARQL query
    """
    errors = []
    warnings = []
    q = sparql_query

    # Verboden prefixen
    if "ceosp:" in q:
        errors.append("❌ Gebruik van verboden prefix 'ceosp:' gevonden.")
    if "ceox:" in q:
        errors.append("❌ Gebruik van verboden prefix 'ceox:' gevonden.")

    # Verboden classnamen (exacte woordgrens)
    verboden_classes = [
        "ceo:Rijksmonumenten", "ceo:ArcheologischeComplexen",
        "ceo:ArcheologischeTerreinen", "ceo:Vondst"
    ]
    for cls in verboden_classes:
        if re.search(r'\b' + re.escape(cls) + r'\b', q):
            errors.append(f"❌ Verboden classnaam '{cls}' – gebruik enkelvoud.")

    # Verboden properties (exacte woordgrens)
    verboden_props = [
        "ceosp:heeftProvincie", "ceox:heeftProvincie", "ceox:heeftAdresgegevens",
        "ceo:heeftPlaats", "ceo:heeftGemeente", "ceo:heeftAdres",
        "ceo:heeftArchitect", "ceo:heeftFunctie"
    ]
    for prop in verboden_props:
        if re.search(r'\b' + re.escape(prop) + r'\b', q):
            errors.append(f"❌ Verboden property '{prop}' gevonden.")

    # FROM clause
    if "FROM" not in q.upper():
        errors.append("❌ Ontbrekende FROM clause – voeg toe: FROM <https://linkeddata.cultureelerfgoed.nl/graph/instanties-rce>")

    # Taalfilters
    for term in ["lang(", "LANG(", "LANGMATCHES(", "langmatches(", "@nl"]:
        if term in q:
            errors.append(f"❌ Gebruik van '{term}' is verboden (geen taallabels in deze dataset).")

    # Waarschuwingen
    if "SELECT " in q.upper() and "DISTINCT" not in q.upper():
        warnings.append("⚠️  Overweeg SELECT DISTINCT bij queries met meerdere joins.")

    if "COUNT(" in q.upper() and "DISTINCT" not in q.upper():
        warnings.append("⚠️  Gebruik COUNT(DISTINCT ?var) bij tellingen met joins.")

    if errors or warnings:
        lines = ["Validatierapport:"]
        lines += errors
        lines += warnings
        return "\n".join(lines)
    else:
        return "✅ Geen bekende fouten gevonden. Query ziet er geldig uit."


@mcp.tool()
def get_provincie_uri(provincie_naam: str) -> str:
    """
    Geef de correcte URI voor een Nederlandse provincie.
    Gebruik deze URI in queries met ceo:heeftProvincie.

    Args:
        provincie_naam: Naam van de provincie (bijv. "Utrecht", "Noord-Holland")
    """
    mapping = {
        "drenthe":       "http://standaarden.overheid.nl/owms/terms/Drenthe",
        "flevoland":     "http://standaarden.overheid.nl/owms/terms/Flevoland",
        "fryslan":       "http://standaarden.overheid.nl/owms/terms/Fryslan",
        "friesland":     "http://standaarden.overheid.nl/owms/terms/Fryslan",
        "fryslân":       "http://standaarden.overheid.nl/owms/terms/Fryslan",
        "gelderland":    "http://standaarden.overheid.nl/owms/terms/Gelderland",
        "groningen":     "http://standaarden.overheid.nl/owms/terms/Groningen_(provincie)",
        "limburg":       "http://standaarden.overheid.nl/owms/terms/Limburg",
        "noord-brabant": "http://standaarden.overheid.nl/owms/terms/Noord-Brabant",
        "brabant":       "http://standaarden.overheid.nl/owms/terms/Noord-Brabant",
        "noord-holland": "http://standaarden.overheid.nl/owms/terms/Noord-Holland",
        "overijssel":    "http://standaarden.overheid.nl/owms/terms/Overijssel",
        "utrecht":       "http://standaarden.overheid.nl/owms/terms/Utrecht_(provincie)",
        "zeeland":       "http://standaarden.overheid.nl/owms/terms/Zeeland_(provincie)",
        "zuid-holland":  "http://standaarden.overheid.nl/owms/terms/Zuid-Holland",
        "holland":       "http://standaarden.overheid.nl/owms/terms/Zuid-Holland",
    }

    key = provincie_naam.lower().strip()
    uri = mapping.get(key)

    if uri:
        return f"Provincie URI voor '{provincie_naam}':\n<{uri}>\n\nGebruik in query:\n?cho ceo:heeftBasisregistratieRelatie ?rel .\n?rel ceo:heeftProvincie <{uri}> ."
    else:
        beschikbaar = "\n".join(f"  - {k}" for k in sorted(mapping.keys()))
        return f"Onbekende provincie: '{provincie_naam}'\n\nBeschikbare provincies:\n{beschikbaar}"


# ──────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
