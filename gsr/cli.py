"""
Google Search Resource (GSR) - Main Entry Point
Research tool for analyzing Google search page structure
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from gsr.searcher import HumanLikeGoogleSearcher
from gsr.enums import SearchStatus

logger = logging.getLogger(__name__)


def load_config_file(config_path):
    """Load configuration from YAML or JSON file"""
    if not config_path:
        return {}

    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_file, "r") as f:
            content = f.read()

        # Try JSON first
        try:
            config = json.loads(content)
            logger.info(f"Loaded JSON config from {config_path}")
            return config
        except json.JSONDecodeError:
            pass

        # Try YAML
        try:
            import yaml

            config = yaml.safe_load(content)
            logger.info(f"Loaded YAML config from {config_path}")
            return config
        except ImportError:
            logger.error("YAML support requires 'pyyaml' package: pip install pyyaml")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to parse config file: {e}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        sys.exit(1)


def merge_config(args, config):
    """
    Merge config file with command-line args (CLI takes precedence)
    
    Priority order:
    1. User explicitly set via CLI (not None)
    2. Value from config file (if present)
    3. Default value (applied last)
    """
    # Define defaults here (to be applied last)
    defaults = {
        "query": "python web scraping",
        "headless": False,
        "new_session": False,
        "session_id": None,
        "typing": "normal",
        "max_results": 5,
        "verbose": 0,
        "quiet": False,
        "timeout": 30,
        "browser": None,
        "output_format": "text",
        "no_images": False,
    }

    # Map config keys to argument names
    config_mapping = {
        "query": "query",
        "headless": "headless",
        "new_session": "new_session",
        "session_id": "session_id",
        "typing": "typing",
        "max_results": "max_results",
        "verbose": "verbose",
        "quiet": "quiet",
        "timeout": "timeout",
        "browser": "browser",
        "output_format": "output_format",
        "no_images": "no_images",
    }

    # Apply values in priority order: CLI > Config > Defaults
    for config_key, arg_name in config_mapping.items():
        current_value = getattr(args, arg_name)
        
        # If user explicitly set via CLI (not None), keep it
        if current_value is not None:
            continue
            
        # Try config file next
        if config and config_key in config:
            config_value = config[config_key]
            
            # Handle verbose specially (can be bool or int)
            if arg_name == "verbose" and isinstance(config_value, bool):
                setattr(args, arg_name, 1 if config_value else 0)
            else:
                setattr(args, arg_name, config_value)
        else:
            # Finally, apply default value
            setattr(args, arg_name, defaults[arg_name])

    return args


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Google Search Resource (GSR) - Research Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Default: visible browser, normal typing
  %(prog)s --headless                         # Run without browser window
  %(prog)s --query "machine learning"         # Search for specific query
  %(prog)s --new-session                      # Force create new session
  %(prog)s --session-id session_123           # Use specific session
  %(prog)s --typing fast                      # Fast typing speed
  %(prog)s --headless --query "AI" --typing slow  # Combined options
        """,
    )

    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help='Search query (default: "python web scraping")',
    )

    parser.add_argument(
        "--headless", 
        action="store_true", 
        default=None,
        help="Run browser in headless mode (no window)"
    )

    parser.add_argument(
        "--new-session", 
        action="store_true",
        default=None,
        help="Force create new session instead of reusing"
    )

    parser.add_argument(
        "--session-id", 
        type=str,
        default=None,
        help="Force use specific session ID"
    )

    parser.add_argument(
        "--typing",
        type=str,
        choices=["fast", "normal", "slow"],
        default=None,
        help="Typing speed style (default: normal)",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of results to display (default: 5)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=None,
        help="Increase verbosity (-v: INFO, -vv: DEBUG)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=None,
        help="Suppress all output except results (overrides --verbose)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds for page operations (default: 30)",
    )

    parser.add_argument(
        "--browser",
        type=str,
        choices=["chromium", "firefox"],
        default=None,
        help="Browser to use (default: auto-select)",
    )

    parser.add_argument(
        "--output-format",
        type=str,
        choices=["text", "json", "csv"],
        default=None,
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--no-images", 
        action="store_true",
        default=None,
        help="Disable image loading (faster, less bandwidth)"
    )

    parser.add_argument("--config", type=str, help="Load configuration from file (YAML or JSON)")

    return parser.parse_args()


def setup_logging(verbosity, quiet):
    """Configure logging based on verbosity level"""
    if quiet:
        # Suppress all logging
        logging.basicConfig(level=logging.CRITICAL + 1)
        return False  # Don't show banner
    elif verbosity == 0:
        # Default: WARNING and above (minimal output)
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
        return True
    elif verbosity == 1:
        # -v: INFO level
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
        return True
    else:
        # -vv: DEBUG level
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s:%(name)s: %(message)s"
        )
        return True


def output_results(results, format_type, query, args):
    """Output results in specified format"""
    if format_type == "json":
        import json

        output = {"query": query, "count": len(results), "results": results}
        print(json.dumps(output, indent=2))

    elif format_type == "csv":
        import csv
        import io

        output = io.StringIO()
        if results:
            writer = csv.DictWriter(output, fieldnames=["title", "url", "snippet"])
            writer.writeheader()
            writer.writerows(results)
        print(output.getvalue(), end="")

    else:  # text format (default)
        print(f"Found {len(results)} results")
        print()
        for i, r in enumerate(results[: args.max_results], 1):
            print(f"{i}. {r['title']}")
            print(f"   {r['url']}")
            if r["snippet"]:
                print(f"   {r['snippet'][:100]}...")
            print()


def main():
    """Main entry point - simple search research example"""
    args = parse_args()

    # Load config file if specified
    config = load_config_file(args.config)
    args = merge_config(args, config)

    # Setup logging
    show_banner = setup_logging(args.verbose, args.quiet)

    # Show banner and configuration (unless quiet)
    if show_banner and not args.quiet:
        print("=" * 50)
        print("Google Search Resource (GSR)")
        print("Research Tool - Educational Use Only")
        print("=" * 50)
        print()

        # Show configuration
        if args.headless:
            print("🔕 Mode: Headless (no browser window)")
        else:
            print("👁️  Mode: Visible browser window")
        print(f"⌨️  Typing: {args.typing}")
        print(f"🔍 Query: {args.query}")
        if args.browser:
            print(f"🌐 Browser: {args.browser}")
        if args.session_id:
            print(f"📁 Session: {args.session_id} (forced)")
        elif args.new_session:
            print("📁 Session: New (forced)")
        if args.output_format != "text":
            print(f"📄 Output: {args.output_format}")
        print()

    searcher = HumanLikeGoogleSearcher(
        headless=args.headless,
        typing_style=args.typing,
        session_id=args.session_id,
        block_images=args.no_images,
    )

    try:
        result = searcher.search(args.query, reuse_session=not args.new_session)

        if result.status == SearchStatus.SUCCESS:
            output_results(result.results, args.output_format, args.query, args)

        elif result.status == SearchStatus.CAPTCHA_DETECTED:
            print(f"CAPTCHA detected: {result.captcha_info['type']}")
            print("Rate limit reached - stopping as requested by Google")
            print(f"Details: {result.captcha_info}")

        elif result.status == SearchStatus.BLOCKED:
            print(f"Blocked! {result.error}")

        else:
            print(f"Error: {result.error}")

        # Show statistics (unless quiet or non-text output)
        if not args.quiet and args.output_format == "text":
            print()
            print("=" * 50)
            stats = searcher.get_statistics()
            print(f"Statistics:")
            print(f"  Total searches: {stats['total_searches']}")
            print(f"  Successful: {stats['successful_searches']}")
            print(f"  CAPTCHAs: {stats['captcha_encounters']}")
            print(f"  Success rate: {stats['success_rate']:.1%}")
            print("=" * 50)

    finally:
        searcher.close()


if __name__ == "__main__":
    main()
