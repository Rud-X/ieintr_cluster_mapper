# Industrial Cluster Material Flow Analysis — Project Spec

> Living document. Update as the project evolves. Intended to be passed to Claude Code for implementation.

---

## Project Goal

Extract material flow data from a poorly structured Excel file and organize it into a clean, queryable database. The primary use case is **graph analysis to identify which companies could be connected** based on matching inflows and outflows — i.e. industrial symbiosis matching.

Companies are **not yet connected** in the real world. The `streams` table captures what each company consumes and produces independently. The `flows` table starts empty and is only populated after matching analysis identifies candidate connections.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/data_model.md](docs/data_model.md) | Tables, columns, ER diagram, key design decisions |
| [docs/migrations_and_extraction.md](docs/migrations_and_extraction.md) | Source CSV formats, `extract.py` pipeline, composition string parser, migration scripts |
| [docs/analysis_tools.md](docs/analysis_tools.md) | `normalize_streams.py` and `carbon.py` CLI reference |
| [docs/folder_structure.md](docs/folder_structure.md) | Annotated directory tree and file roles |

---

## TODO / Next Steps


