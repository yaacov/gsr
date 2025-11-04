# Google Search Resource (GSR)

A tool for researching and analyzing Google search page behavior and structure.

## Purpose

GSR is designed for legitimate research purposes:
- Understanding how Google search pages are structured
- Analyzing search result formatting
- Studying how search interfaces change over time
- Educational purposes and web development learning

## Installation

### From PyPI

```bash
# Install the package
pip install google-search-resource

# Install playwright browsers
playwright install chromium firefox
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yaacov/gsr.git
cd gsr

# Complete setup (create venv, install dependencies and browsers)
make setup

# Activate virtual environment
source venv/bin/activate
```

## Usage

### Command Line Interface

After installation, use the `gsr` command:

```bash
# Basic usage with default query
gsr

# Custom search query
gsr --query "machine learning"

# Headless mode (no browser window)
gsr --headless --query "python web scraping"

# Get help
gsr --help
```

### Available CLI Options

```bash
gsr [OPTIONS]

Options:
  --query, -q TEXT          Search query
  --headless                Run browser in headless mode
  --new-session             Force create new session
  --session-id TEXT         Use specific session ID
  --typing [fast|normal|slow]  Typing speed style
  --max-results INT         Maximum results to display
  --verbose, -v             Increase verbosity (-v: INFO, -vv: DEBUG)
  --quiet                   Suppress all output except results
  --timeout INT             Timeout in seconds
  --browser [chromium|firefox]  Browser to use
  --output-format [text|json|csv]  Output format
  --no-images               Disable image loading
  --config PATH             Load configuration from YAML/JSON file
```

## Usage Examples

### Library Usage

```python
from gsr.searcher import HumanLikeGoogleSearcher
from gsr.enums import SearchStatus

# Simple search with defaults
searcher = HumanLikeGoogleSearcher()

try:
    result = searcher.search("python programming")
    
    if result.status == SearchStatus.SUCCESS:
        for r in result.results:
            print(f"{r['title']}: {r['url']}")
    
    elif result.status == SearchStatus.CAPTCHA_DETECTED:
        print("Rate limit reached - stopping research")
        
finally:
    searcher.close()
```

## Development

### Setup for Contributors

```bash
# Clone and setup
git clone https://github.com/yaacov/gsr.git
cd gsr

# Install with dev dependencies
make install-dev
make install-browsers

# Code quality tools
make format        # Auto-format code
make lint          # Check code style
make format-check  # Check formatting without changes
```

### Building and Publishing

```bash
# Build package
make build

# Test on TestPyPI
make publish-test

# Publish to PyPI (production)
make publish
```

## License

MIT License - Copyright (c) 2025 Yaacov Zamir

For educational and research purposes.
