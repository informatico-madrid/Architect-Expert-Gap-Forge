# Autonomous Operations with Qdrant MCP
You have access to an MCP server connected to a Qdrant vector database. It is your exclusive responsibility to keep this index updated and leverage it without human intervention.

- **Research Phase:** Before writing or modifying any file, always use the `qdrant-find` tool to search the database for similar code patterns, existing implementations, or previous architectural decisions.
- **Indexing Phase:** Every time you implement a new feature, write a critical block of code, or define a rule within the `specs/` directory, use the `qdrant-store` tool to send a concise natural language summary alongside the relevant code context to the database.
- **Execution:** Perform these operations silently within your chain of thought. Do not ask the user to manually trigger memory saves or searches.
# Autonomous Operations with Qdrant MCP
You have access to an MCP server connected to a Qdrant vector database. It is your exclusive responsibility to keep this index updated, but you must be extremely selective about what you store.

- **Indexing Phase:** Use `qdrant-store` ONLY for permanent, long-term knowledge. You MUST save:
  1. Architectural decisions and system design changes.
  2. Core business rules and API contracts.
  3. Reusable code patterns.
- **RESTRICTION - DO NOT STORE:** NEVER use `qdrant-store` to save transient states, temporary test failures, debugging logs, to-do lists, or step-by-step progress. Transient information belongs in the workspace files, not in the vector database.