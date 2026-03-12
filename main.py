"""
RAGCore — CLI entry point
=========================

Usage examples
--------------
Index a document:
    python main.py index reports/budget_session.pdf

Summarise a document:
    python main.py summarise reports/cabinet_minutes.pdf

Ask a question:
    python main.py query "What was decided about infrastructure funding?"

Interactive Q&A session:
    python main.py chat

Reset the vector store:
    python main.py index reports/new_doc.pdf --reset
"""

import argparse
import json
import logging
import sys
import textwrap

from src.engine import PipelineConfig, RAGPipeline

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.WARNING,          # keep output clean by default
)

BANNER = """
  ██████╗  █████╗  ██████╗  ██████╗ ██████╗ ██████╗ ███████╗
  ██╔══██╗██╔══██╗██╔════╝ ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██████╔╝███████║██║  ███╗██║     ██║   ██║██████╔╝█████╗
  ██╔══██╗██╔══██║██║   ██║██║     ██║   ██║██╔══██╗██╔══╝
  ██║  ██║██║  ██║╚██████╔╝╚██████╗╚██████╔╝██║  ██║███████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
  Retrieval Augmented Generation — v1.0.0
"""

DIVIDER = "─" * 62


def _print(label: str, value: str, width: int = 54):
    wrapped = textwrap.fill(value, width=width, subsequent_indent="             ")
    print(f"  {label:<12} {wrapped}")


def cmd_index(args, pipeline: RAGPipeline):
    print(f"\n  Indexing: {args.file}")
    n = pipeline.index(args.file, reset=args.reset)
    print(f"  ✓ {n} chunks stored in vector store.\n")


def cmd_summarise(args, pipeline: RAGPipeline):
    print(f"\n  Summarising: {args.file}")
    result = pipeline.summarise(args.file)
    print(f"\n{DIVIDER}")
    _print("Source:", result.source)
    _print("Summary:", result.summary)
    print(f"  {'Time:':<12} {result.latency_ms:.0f} ms")
    print(f"{DIVIDER}\n")

    if args.json:
        print(json.dumps(result.__dict__, indent=2))


def cmd_query(args, pipeline: RAGPipeline):
    result = pipeline.query(args.question)
    if args.json:
        print(json.dumps(result.__dict__, indent=2))
        return

    print(f"\n{DIVIDER}")
    _print("Query:", result.query)
    _print("Answer:", result.answer)
    print(f"  {'Confidence:':<12} {result.confidence:.1%}")
    print(f"  {'Latency:':<12} {result.latency_ms:.0f} ms")
    if result.sources:
        _print("Sources:", ", ".join(result.sources))
    if args.verbose and result.passages:
        print(f"\n  Top passage:")
        print(textwrap.fill(
            result.passages[0][:500] + "…",
            width=60,
            initial_indent="    ",
            subsequent_indent="    ",
        ))
    print(f"{DIVIDER}\n")


def cmd_chat(pipeline: RAGPipeline):
    print("\n  Interactive mode — type 'exit' to quit.\n")
    while True:
        try:
            q = input("  ❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Session ended.")
            break
        if not q:
            continue
        if q.lower() in {"exit", "quit", "q"}:
            print("  Session ended.")
            break

        result = pipeline.query(q)
        print(f"\n  Answer     : {result.answer}")
        print(f"  Confidence : {result.confidence:.1%}")
        print(f"  Latency    : {result.latency_ms:.0f} ms\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ragcore",
        description="RAGCore — local retrieval-augmented generation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # index
    idx = sub.add_parser("index", help="Ingest a document into the vector store")
    idx.add_argument("file", help="Path to .pdf, .txt, or .md file")
    idx.add_argument("--reset", action="store_true",
                     help="Wipe existing index before ingesting")

    # summarise
    s = sub.add_parser("summarise", help="Abstractive summary of a document")
    s.add_argument("file", help="Path to document")
    s.add_argument("--json", action="store_true", help="Output as JSON")

    # query
    q = sub.add_parser("query", help="Ask a question against indexed documents")
    q.add_argument("question", help="Natural language question")
    q.add_argument("--json", action="store_true", help="Output as JSON")
    q.add_argument("--verbose", action="store_true",
                   help="Print top source passage")

    # chat
    sub.add_parser("chat", help="Start an interactive Q&A session")

    return p


def main():
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args()

    cfg = PipelineConfig()
    pipeline = RAGPipeline(cfg)

    dispatch = {
        "index": lambda: cmd_index(args, pipeline),
        "summarise": lambda: cmd_summarise(args, pipeline),
        "query": lambda: cmd_query(args, pipeline),
        "chat": lambda: cmd_chat(pipeline),
    }

    try:
        dispatch[args.cmd]()
    except FileNotFoundError as e:
        print(f"\n  ✗ {e}\n", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
