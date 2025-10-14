# Technology Stack

## Backend

- **Framework**: Flask 2.3.3 (Python web framework)
- **WSGI Server**: Gunicorn 21.2.0 (production)
- **Database**: MySQL (via PyMySQL and mysql-connector-python)
- **ORM**: Direct SQL queries using custom execute_query wrapper

## Frontend

- **Architecture**: Dynamic AJAX-based SPA with server-side templates
- **Template Engine**: Jinja2
- **JavaScript**: Vanilla JS with Axios for HTTP requests
- **UI Framework**: Custom CSS with Font Awesome icons
- **Loading Pattern**: Dynamic content loading via `cargarContenidoDinamico()` function

## Key Libraries

- **pandas**: Excel file processing and data manipulation
- **openpyxl/xlrd**: Excel file reading/writing
- **beautifulsoup4**: HTML parsing and web scraping
- **flask-cors**: CORS support for API endpoints
- **python-dotenv**: Environment configuration
- **watchdog**: File system monitoring (SMT)
- **psutil**: System utilities

## Deployment

- **Hosting**: Vercel (serverless Python)
- **Entry Point**: `api/index.py` (Vercel) or `run.py` (local)
- **Configuration**: `.env` file for database credentials
- **Static Files**: Served from `app/static/`

## Database Configuration

MySQL connection via environment variables or hardcoded config in `db_mysql.py`:

- Host: up-de-fra1-mysql-1.db.run-on-seenode.com
- Port: 11550
- Database: db_rrpq0erbdujn

## Common Commands

### Development

```bash
# Run locally
python run.py

# Install dependencies
pip install -r requirements.txt

# Check JavaScript syntax
python scripts/check_js_syntax.py
```

### Testing

No automated test suite currently configured. Manual testing via browser console and API endpoints.

### Deployment

Automatic deployment via Vercel on git push. Configuration in `vercel.json`.
