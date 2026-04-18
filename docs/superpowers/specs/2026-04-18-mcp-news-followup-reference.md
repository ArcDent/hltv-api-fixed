# MCP News Follow-up Reference

This file is a handoff/reference note for a future conversation that will update the MCP layer after the upstream API pagination work lands.

## Purpose

The upstream API will expose paginated news access through:

- `GET /api/v1/news?limit=50&offset=0`
- `GET /api/v1/news/<year>/<month>/?limit=50&offset=0`

The future MCP work should consume that paginated mode instead of assuming the API always returns a raw array.

## MCP Tasks To Implement Later

### 1. News query model

Update MCP-side news query/input types to support:

- `limit` defaulting to `50`
- `offset` defaulting to `0`
- optional `tag`, `year`, `month`, `timezone`

### 2. News facade logic

Update MCP `getNewsDigest(...)` flow so it:

1. requests upstream paginated mode (`limit=50`, `offset=0` by default)
2. preserves upstream pagination metadata
3. exposes enough metadata for renderer prompts:
   - `total`
   - `count`
   - `limit`
   - `offset`
   - `has_more`
   - `next_offset`

### 3. Required future MCP news-rendering work

News renderer should eventually show:

- total number of news items
- current displayed range (`1-50`, `51-100`, etc.)
- original English title
- Chinese title translation
- explicit continue guidance when `has_more` is true

Suggested footer copy:

```text
如需继续查看第 51-100 条，请继续，并携带 offset=50。
```

### 4. Team-name display rule

Future MCP rendering should prefer:

- `英文官称（中文俗称）` when a stable colloquial/community Chinese name exists
- English-only display when no stable colloquial Chinese name should be shown

Examples of agreed mappings:

- `Astralis（A队）`
- `PariVision（PV）`
- `FURIA（黑豹）`
- `Team Spirit（绿龙）`
- `MOUZ（老鼠）`
- `Natus Vincere（天生赢家）`
- `Falcons（猎鹰）`
- `Aurora（欧若拉）`
- `Vitality（小蜜蜂）`
- `Liquid（液体）`
- `TYLOO（天禄）`
- `Eternal Fire（永火）`
- `The MongolZ（蒙古队）`
- `Virtus.pro（VP）`
- `Lynn Vision（LVG）`
- `Rare Atom（RA）`
- `Ninjas in Pyjamas（忍者）`
- `Imperial（帝国）`

Conservative English-first entries for first MCP pass:

- `FaZe`
- `G2`
- `HEROIC`
- `BIG`
- `ENCE`
- `fnatic`
- `OG`
- `MIBR`
- `paiN`
- `Wildcard`

Important explicit correction:

- `PariVision -> PV`
- `paiN != PV`
- `paiN` must **not** be mapped to `PV`

### 5. Matching vs display

Keep the model split:

- matching should accept English names, abbreviations, colloquial Chinese aliases, and common nicknames
- display should output either:
  - `英文官称（中文俗称）`, or
  - English only when no stable colloquial Chinese name is approved

## MCP Files Likely To Change Later

- `src/types/hltv.ts`
- `src/types/common.ts`
- `src/services/hltvFacade.ts`
- `src/renderers/chineseRenderer.ts`
- `src/commands/commandHandlers.ts`
- `src/mcp/server.ts`
- `src/utils/localizedNames.ts`

## Suggested MCP Acceptance Criteria

1. `/News` defaults to requesting `limit=50, offset=0` from upstream.
2. Renderer shows total count and current range.
3. Renderer keeps English title visible and adds Chinese translation per item.
4. Renderer tells the user how to continue when more items exist.
5. Team/event rendering uses the agreed dual-name display rule where applicable.
