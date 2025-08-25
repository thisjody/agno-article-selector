#!/usr/bin/env python3
"""View and analyze saved agent responses."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.response_tracker import response_tracker


def view_summary():
    """Display summary of all saved responses."""
    summary = response_tracker.get_summary()
    
    print("\n" + "="*60)
    print("RESPONSE TRACKER SUMMARY")
    print("="*60)
    
    print(f"\nTotal Responses: {summary['total_responses']}")
    
    print("\nResponses by Agent:")
    for agent_type, count in summary['by_agent'].items():
        print(f"  {agent_type:20} {count:5} files")
    
    if summary['latest_files']:
        print("\nLatest Files:")
        for file_info in summary['latest_files']:
            print(f"\n  Agent: {file_info['agent']}")
            print(f"  File:  {Path(file_info['file']).name}")
            print(f"  Time:  {file_info['modified']}")


def list_responses(
    agent_type: Optional[str] = None,
    article_id: Optional[str] = None,
    limit: int = 20
):
    """List response files.
    
    Args:
        agent_type: Filter by agent type
        article_id: Filter by article ID
        limit: Maximum files to show
    """
    files = response_tracker.get_response_files(
        agent_type=agent_type,
        article_id=article_id,
        limit=limit
    )
    
    if not files:
        print("No response files found.")
        return
    
    print(f"\nFound {len(files)} response file(s):")
    print("-" * 60)
    
    for filepath in files:
        path = Path(filepath)
        stat = path.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n📄 {path.name}")
        print(f"   Size: {size_kb:.1f} KB")
        print(f"   Modified: {modified}")
        print(f"   Path: {path.parent.name}/{path.name}")


def view_response(filepath: str, show_input: bool = True, show_output: bool = True):
    """View a specific response file.
    
    Args:
        filepath: Path to response file
        show_input: Show input data
        show_output: Show output data
    """
    # Handle relative paths
    if not Path(filepath).is_absolute():
        # Try to find in output directory
        possible_paths = [
            Path(filepath),
            Path(response_tracker.output_dir) / filepath,
        ]
        
        # Check each agent directory
        for agent_dir in response_tracker.agent_dirs.values():
            possible_paths.append(agent_dir / filepath)
        
        for path in possible_paths:
            if path.exists():
                filepath = str(path)
                break
        else:
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
    
    # Check if it's a text file (sanity check input)
    if filepath.endswith('.txt'):
        print(f"\n{'='*60}")
        print(f"SANITY CHECK INPUT: {Path(filepath).name}")
        print('='*60)
        with open(filepath, 'r') as f:
            print(f.read())
        return
    
    # Load JSON response
    try:
        data = response_tracker.load_response(filepath)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"RESPONSE FILE: {Path(filepath).name}")
    print('='*60)
    
    # Display metadata
    print(f"\nAgent Type: {data.get('agent_type', 'Unknown')}")
    print(f"Timestamp:  {data.get('timestamp', 'Unknown')}")
    
    if 'article_id' in data:
        print(f"Article ID: {data['article_id']}")
    if 'batch_id' in data:
        print(f"Batch ID:   {data['batch_id']}")
    
    # Display metadata
    if data.get('metadata'):
        print("\nMetadata:")
        for key, value in data['metadata'].items():
            print(f"  {key}: {value}")
    
    # Display input
    if show_input and 'input' in data:
        print("\n" + "-"*40)
        print("INPUT:")
        print("-"*40)
        
        input_data = data['input']
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                if key == 'content' and len(str(value)) > 500:
                    print(f"{key}: {str(value)[:500]}...")
                else:
                    print(f"{key}: {value}")
        else:
            print(input_data)
    
    # Display output
    if show_output and 'output' in data:
        print("\n" + "-"*40)
        print("OUTPUT:")
        print("-"*40)
        
        output_data = data['output']
        if isinstance(output_data, dict):
            print(json.dumps(output_data, indent=2))
        else:
            print(output_data)


def compare_responses(file1: str, file2: str):
    """Compare two response files.
    
    Args:
        file1: First file path
        file2: Second file path
    """
    try:
        data1 = response_tracker.load_response(file1)
        data2 = response_tracker.load_response(file2)
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("RESPONSE COMPARISON")
    print('='*60)
    
    # Compare metadata
    print("\nFile 1:", Path(file1).name)
    print("  Agent:", data1.get('agent_type', 'Unknown'))
    print("  Time:", data1.get('timestamp', 'Unknown'))
    
    print("\nFile 2:", Path(file2).name)
    print("  Agent:", data2.get('agent_type', 'Unknown'))
    print("  Time:", data2.get('timestamp', 'Unknown'))
    
    # Compare outputs
    if 'output' in data1 and 'output' in data2:
        output1 = str(data1['output'])
        output2 = str(data2['output'])
        
        if output1 == output2:
            print("\n✅ Outputs are identical")
        else:
            print("\n❌ Outputs differ")
            print(f"\nOutput 1 length: {len(output1)} chars")
            print(f"Output 2 length: {len(output2)} chars")


def clean_old_responses(days: int = 7, dry_run: bool = True):
    """Clean old response files.
    
    Args:
        days: Remove files older than this many days
        dry_run: If True, only show what would be deleted
    """
    import time
    
    cutoff_time = time.time() - (days * 24 * 3600)
    files_to_delete = []
    total_size = 0
    
    for agent_dir in response_tracker.agent_dirs.values():
        if not agent_dir.exists():
            continue
        
        for filepath in agent_dir.glob("*"):
            if filepath.stat().st_mtime < cutoff_time:
                files_to_delete.append(filepath)
                total_size += filepath.stat().st_size
    
    if not files_to_delete:
        print(f"No files older than {days} days found.")
        return
    
    print(f"\n{'DRY RUN: ' if dry_run else ''}Found {len(files_to_delete)} files to delete")
    print(f"Total size: {total_size / (1024*1024):.2f} MB")
    
    if dry_run:
        print("\nFiles that would be deleted:")
        for filepath in files_to_delete[:10]:
            print(f"  - {filepath.name}")
        if len(files_to_delete) > 10:
            print(f"  ... and {len(files_to_delete) - 10} more")
        print("\nRun with --confirm to actually delete files")
    else:
        for filepath in files_to_delete:
            filepath.unlink()
        print(f"✅ Deleted {len(files_to_delete)} files")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="View and analyze saved agent responses"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Summary command
    subparsers.add_parser("summary", help="Show summary of all responses")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List response files")
    list_parser.add_argument(
        "-a", "--agent",
        choices=["first_pass", "scoring", "selector", "comparative_ranker"],
        help="Filter by agent type"
    )
    list_parser.add_argument(
        "-i", "--article-id",
        help="Filter by article ID"
    )
    list_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=20,
        help="Maximum files to show (default: 20)"
    )
    
    # View command
    view_parser = subparsers.add_parser("view", help="View a response file")
    view_parser.add_argument("file", help="Path to response file")
    view_parser.add_argument(
        "--no-input",
        action="store_true",
        help="Don't show input data"
    )
    view_parser.add_argument(
        "--no-output",
        action="store_true",
        help="Don't show output data"
    )
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two responses")
    compare_parser.add_argument("file1", help="First file")
    compare_parser.add_argument("file2", help="Second file")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean old response files")
    clean_parser.add_argument(
        "-d", "--days",
        type=int,
        default=7,
        help="Remove files older than N days (default: 7)"
    )
    clean_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete files (otherwise dry run)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        view_summary()
    elif args.command == "summary":
        view_summary()
    elif args.command == "list":
        list_responses(
            agent_type=args.agent,
            article_id=args.article_id,
            limit=args.limit
        )
    elif args.command == "view":
        view_response(
            args.file,
            show_input=not args.no_input,
            show_output=not args.no_output
        )
    elif args.command == "compare":
        compare_responses(args.file1, args.file2)
    elif args.command == "clean":
        clean_old_responses(days=args.days, dry_run=not args.confirm)


if __name__ == "__main__":
    main()