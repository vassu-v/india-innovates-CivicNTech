import argparse
import sys
import os
from ingestion_engine import IngestionEngine

def main():
    parser = argparse.ArgumentParser(description="Ingestion Engine CLI - CoPilot MVP")
    parser.add_argument("--text", type=str, help="Raw text to process")
    parser.add_argument("--file", type=str, help="Path to a text file to process")
    parser.add_argument("--user", type=str, default="User", help="Name of the primary user (default: User)")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="HuggingFace embedding model name")
    
    args = parser.parse_args()

    if not args.text and not args.file:
        print("Usage: python cli.py --text \"your text here\" OR python cli.py --file \"path/to/file.txt\"")
        sys.exit(1)

    input_text = ""
    source_id = "manual_input"

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        with open(args.file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        source_id = os.path.basename(args.file)
    else:
        input_text = args.text

    print("\n--- Ingestion Engine MVP starting ---")
    print(f"User Name: {args.user}")
    print(f"Source: {source_id}")
    print("NOTE: In this CLI, the model is loaded every time. In production (API),")
    print("the model is loaded once on startup and stays in memory for instant response.")
    print("------------------------------------\n")

    engine = IngestionEngine(model_name=args.model, user_name=args.user)
    results = engine.process_text(input_text, source_id=source_id)

    print("\n--- Processing Result Summary ---")
    print(f"Total Chunks: {results['total_chunks']}")
    for key, count in results['routed'].items():
        print(f"  {key.replace('_', ' ').capitalize()}: {count}")
    print("----------------------------------\n")

    print("Detailed Breakdown:")
    for i, item in enumerate(results['items']):
        speaker_str = f"[{item['speaker']}]" if item['speaker'] else "[No Speaker]"
        print(f"\nChunk {i+1}: {speaker_str} {item['chunk_text']}")
        print(f"  Confidence: {item['confidence']:.2f} | Label: {item['label']}")
        print(f"  Routed To:  {item['routed_to'].upper()}")

if __name__ == "__main__":
    main()
