# Juba Checker - Credential Validation Tool

A robust, Python-based credential checker tool with concurrent processing, proxy support, and a user-friendly web interface.

## Features

- **Batch Credential Processing**: Process multiple text files containing credentials in `domain:username:password` format
- **Concurrent Processing**: Multi-threaded credential checking with configurable worker threads
- **Proxy Support**: Rotate through proxies with automatic validation
- **Web Interface**: Flask-based UI for easy file uploads and result viewing
- **CLI Interface**: Command-line interface for automation and scripting
- **Smart Login Detection**: Attempts multiple common login endpoints and field names
- **Organized Results**: Results saved by domain in separate folders
- **Error Handling**: Graceful handling of network errors and invalid credentials
- **Detailed Logging**: Comprehensive logging for debugging and monitoring

## Installation

### Requirements

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

1. Start the Flask web server:

```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`
3. Upload your credential files (search_*.txt format)
4. Optionally upload a proxy.txt file
5. Set the number of worker threads
6. Click "Start Processing" and view results in real-time

### Command Line Interface

Basic usage:

```bash
python juba_checker.py --folder /path/to/credentials
```

With all options:

```bash
python juba_checker.py --folder /path/to/credentials --output ./results --workers 20 --proxy-file proxy.txt
```

Dry run (preview without checking):

```bash
python juba_checker.py --folder /path/to/credentials --dry-run
```

### CLI Options

- `--folder`: (Required) Folder containing search_*.txt files
- `--output`: Output directory for results (default: `results`)
- `--workers`: Number of concurrent worker threads (default: 10)
- `--proxy-file`: Path to proxy.txt file for proxy rotation
- `--dry-run`: Preview what would be checked without performing login attempts

## File Formats

### Credential Files (search_*.txt)

Each line should follow this format:

```
example.com:user@email.com:password123
domain.com:username:pass:word:with:colons
site.org:admin:secretpass
```

### Proxy File (proxy.txt)

One proxy per line in standard format:

```
http://proxy1.com:8080
http://user:pass@proxy2.com:3128
socks5://proxy3.com:1080
```

## Output Structure

Results are organized by domain:

```
results/
├── example.com/
│   └── results.txt
├── domain.com/
│   └── results.txt
└── site.org/
    └── results.txt
```

Each results.txt contains successful credentials in the same format as input.

## Building Standalone Executable

To create a standalone Windows executable:

```bash
pyinstaller juba_checker.spec
```

The executable will be created in the `dist/` folder.

## Web Interface Routes

- `/` - Home page with upload form
- `/upload` - Handle file uploads and start processing
- `/results/<job_id>` - View results for a specific job
- `/status/<job_id>` - Get JSON status of a job
- `/download/<filepath>` - Download results file
- `/jobs` - List all processing jobs

## Security Considerations

- This tool is for authorized security testing only
- Always obtain proper authorization before testing credentials
- Use responsibly and ethically
- Keep proxy credentials secure
- Results files contain sensitive information - protect them appropriately

## Logging

Logs are written to:
- Console output (real-time)
- `juba_checker.log` file (persistent)

Log levels:
- INFO: Successful logins and processing status
- DEBUG: Detailed request information
- ERROR: Failed operations and exceptions

## Troubleshooting

### No successful logins found

- Verify credential format is correct
- Check that domains are accessible
- Try reducing worker count to avoid rate limiting
- Enable DEBUG logging for more details

### Proxy validation fails

- Ensure proxies are in correct format
- Test proxies manually before use
- Some proxies may require authentication

### Web interface not accessible

- Check firewall settings
- Ensure port 5000 is not in use
- Try accessing via `http://127.0.0.1:5000`

## Performance Tips

- Start with 10 workers and adjust based on your system
- Use proxies to avoid IP-based rate limiting
- Process smaller batches for faster feedback
- Monitor system resources during processing

## License

This tool is provided as-is for educational and authorized security testing purposes only.

## Disclaimer

The authors are not responsible for misuse of this tool. Always ensure you have proper authorization before testing any credentials or systems.

## Support

For issues, questions, or contributions, please refer to the project documentation or contact the development team.
