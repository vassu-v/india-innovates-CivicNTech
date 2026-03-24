import argparse
import json
import sys
import os

# Add the current directory to sys.path so we can import engine
sys.path.append(os.path.dirname(__file__))
import engine as rag_engine

def main():
    parser = argparse.ArgumentParser(description="SarkarSathi Standalone RAG Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: init
    subparsers.add_parser("init", help="Initialize the RAG database")

    # Command: add
    add_parser = subparsers.add_parser("add", help="Add a knowledge node")
    add_parser.add_argument("--domain", required=True, help="commitment_history | context_file | complaint_pattern")
    add_parser.add_argument("--ward", help="Ward name or number")
    add_parser.add_argument("--topic", help="Topic like drainage, water, etc.")
    add_parser.add_argument("--title", required=True, help="Short title/label")
    add_parser.add_argument("--content", required=True, help="The actual text content")
    add_parser.add_argument("--ref", required=True, help="Source reference ID")

    # Command: query
    query_parser = subparsers.add_parser("query", help="Semantic search query")
    query_parser.add_argument("text", help="Search text")
    query_parser.add_argument("--limit", type=int, default=5, help="Number of results")
    query_parser.add_argument("--ward", help="Filter by ward")

    # Command: chat
    chat_parser = subparsers.add_parser("chat", help="Chat with Co-Pilot (Gemini)")
    chat_parser.add_argument("question", help="Your question")
    chat_parser.add_argument("--profile", help="Path to JSON file with profile data")
    chat_parser.add_argument("--digest", help="Path to JSON file with digest data")
    chat_parser.add_argument("--debug", action="store_true", help="Show assembled context")

    # Command: truncate
    subparsers.add_parser("truncate", help="Wipe all data from RAG database")

    args = parser.parse_args()

    if args.command == "init":
        rag_engine.init_db()
        print("RAG database initialized.")

    elif args.command == "add":
        node_id = rag_engine.store_node(
            args.domain, args.ward, args.topic, args.title, args.content, args.ref
        )
        print(f"Node added with ID: {node_id}")

    elif args.command == "query":
        nodes = rag_engine.query_nodes(args.text, limit=args.limit, ward_filter=args.ward)
        if not nodes:
            print("No matching nodes found.")
        else:
            for n in nodes:
                print(f"[{n['domain']}] {n['title']} (Sim: {n['similarity']:.3f})")
                print(f"Content: {n['content'][:100]}...")
                print("-" * 40)

    elif args.command == "chat":
        profile = None
        if args.profile and os.path.exists(args.profile):
            with open(args.profile, 'r') as f:
                profile = json.load(f)

        digest = None
        if args.digest and os.path.exists(args.digest):
            with open(args.digest, 'r') as f:
                digest = json.load(f)

        print("Thinking...")
        result = rag_engine.chat(args.question, profile=profile, digest=digest)

        if args.debug:
            print("\n=== ASSEMBLED CONTEXT (DEBUG) ===")
            print(result.get("raw_context", "N/A"))

        print("\n=== CO-PILOT RESPONSE ===")
        print(result["response"])
        print("\n=== SOURCES ===")
        for s in result["sources"]:
            print(f"- {s['title']} ({s['domain']})")

        # Optionally show context for debugging
        # print("\n=== DEBUG: ASSEMBLED CONTEXT ===")
        # print(result["raw_context"])

    elif args.command == "truncate":
        confirm = input("Are you sure you want to wipe all RAG data? (y/n): ")
        if confirm.lower() == 'y':
            rag_engine.truncate_db()
            print("RAG database wiped.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
