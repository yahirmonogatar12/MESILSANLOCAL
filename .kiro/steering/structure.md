# Project Structure

## Root Directory

```
/
├── app/                    # Main application package
├── api/                    # Vercel serverless entry point
├── scripts/                # Utility scripts
├── Sistema_Trazabilidad/   # Traceability system module
├── ZebraPrintService/      # Zebra printer Windows service
├── docs/                   # Documentation
├── run.py                  # Local development entry point
├── requirements.txt        # Python dependencies
└── vercel.json            # Vercel deployment config
```

## App Directory Structure

```
app/
├── __init__.py            # Package initialization
├── routes.py              # Main Flask routes and app initialization
├── db.py                  # SQLite database functions (legacy)
├── db_mysql.py            # MySQL database functions
├── auth_system.py         # Authentication and authorization
├── user_admin.py          # User administration blueprint
├── admin_api.py           # Admin API endpoints
│
├── templates/             # Jinja2 HTML templates
│   ├── MaterialTemplate.html          # Main SPA container
│   ├── login.html                     # Login page
│   ├── Control de material/           # Material control templates
│   ├── Control de proceso/            # Process control templates
│   └── [other modules]/
│
├── static/                # Static assets
│   ├── js/
│   │   ├── scriptMain.js              # Main navigation orchestrator
│   │   ├── plan.js                    # Production planning module
│   │   └── [other modules].js
│   └── css/
│       └── styles.css                 # Global styles
│
├── database/              # Database-related files
├── includes/              # PHP includes (legacy)
├── php/                   # PHP files (legacy)
├── py/                    # Python modules
│   └── control_modelos_smt.py
│
└── [API modules]          # Modular API files
    ├── api_po_wo.py       # PO/WO API
    ├── api_raw_modelos.py # Raw models API
    ├── aoi_api.py         # AOI API
    ├── smd_inventory_api.py # SMD inventory API
    ├── smt_routes*.py     # SMT routes (multiple versions)
    └── models_po_wo.py    # PO/WO data models
```

## Key Architectural Patterns

### Dynamic Module Loading
- Main container: `MaterialTemplate.html`
- Navigation orchestrator: `scriptMain.js`
- Modules loaded via AJAX using `cargarContenidoDinamico()`
- Each module has: HTML template, JS file, optional CSS

### Blueprint Pattern
Flask blueprints for modular routes:
- `user_admin_bp` - User administration
- `admin_bp` - Admin API
- `aoi_api` - AOI operations
- `control_modelos_bp` - SMT model control
- `api_raw` - Raw models API
- `smt_bp` - SMT routes

### Database Access
- Direct SQL via `execute_query()` wrapper in `db_mysql.py`
- No ORM, raw SQL queries throughout
- Connection pooling handled by PyMySQL

### Authentication
- Session-based authentication via Flask sessions
- Role-based permissions stored in database
- Decorators: `@login_requerido`, `@requiere_permiso_dropdown`

## Module Naming Conventions

### Files
- Templates: `[category]/[module_name].html`
- JavaScript: `[module-name].js` (kebab-case)
- Python APIs: `[module]_api.py` or `api_[module].py`

### IDs and Functions
- HTML IDs: `[module]-[element]-[action]` (e.g., `plan-btn-guardar`)
- JS Functions: `[module][Action]` (e.g., `planGuardar()`)
- Global Functions: Exposed via `window.[functionName]`

### API Endpoints
- AJAX templates: `/[module]-ajax`
- API data: `/api/[module]/[action]`

## Configuration Files

- `.env` - Environment variables (database credentials)
- `vercel.json` - Vercel deployment configuration
- `runtime.txt` - Python version for hosting
- `.gitignore` - Git ignore patterns
