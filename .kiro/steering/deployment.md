# Deployment & Environment

## Hosting Platform

### Vercel (Production)
- Serverless Python deployment
- Entry point: `api/index.py`
- Configuration: `vercel.json`
- Automatic deployment on git push
- Environment variables via Vercel dashboard

### Local Development
- Entry point: `run.py`
- Flask development server
- Port: 5000
- Debug mode enabled

## Environment Configuration

### Environment Variables
Required variables in `.env` file:
```
MYSQL_HOST=up-de-fra1-mysql-1.db.run-on-seenode.com
MYSQL_PORT=11550
MYSQL_DATABASE=db_rrpq0erbdujn
MYSQL_USERNAME=db_rrpq0erbdujn
MYSQL_PASSWORD=5fUNbSRcPP3LN9K2I33Pr0ge
```

### Loading Environment Variables
```python
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv('MYSQL_HOST', 'localhost')
port = int(os.getenv('MYSQL_PORT', '3306'))
```

## Vercel Configuration

### vercel.json
```json
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### Python Version
Specified in `runtime.txt`:
```
python-3.9
```

## Entry Points

### Production (Vercel)
`api/index.py`:
```python
from app.routes import app
from app.smt_routes_clean import register_smt_routes
from app.api_po_wo import registrar_rutas_po_wo
from app.aoi_api import aoi_api

# Register routes
register_smt_routes(app)
registrar_rutas_po_wo(app)
app.register_blueprint(aoi_api)

# Vercel detects 'app' variable
```

### Local Development
`run.py`:
```python
from app.routes import app
from app.smt_routes_clean import register_smt_routes
from app.api_po_wo import registrar_rutas_po_wo

# Register routes
register_smt_routes(app)
registrar_rutas_po_wo(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

## Static Files

### Development
- Served by Flask from `app/static/`
- URL: `{{ url_for('static', filename='js/script.js') }}`

### Production (Vercel)
- Served by Vercel CDN
- Same URL pattern as development
- Automatic caching and optimization

## Database Connection

### Connection Pooling
- Not implemented at application level
- Handled by MySQL server
- Each request creates new connection via `execute_query()`

### Connection Timeouts
```python
MYSQL_CONFIG = {
    'connect_timeout': 60,
    'read_timeout': 60,
    'write_timeout': 60
}
```

### Fallback Behavior
If MySQL unavailable:
- Returns empty results for queries
- Logs errors to console
- Application continues running (degraded mode)

## Logging

### Console Logging
```python
print("✅ Success message")
print("❌ Error message")
print("⚠️ Warning message")
```

### Audit Logging
All important actions logged to `auditoria` table:
```python
auth_system.registrar_auditoria(
    usuario=session.get('usuario'),
    modulo='sistema',
    accion='deploy',
    descripcion='Application deployed',
    resultado='EXITOSO'
)
```

## Performance Optimization

### Database Queries
- Use indexes on frequently queried columns
- Limit result sets with `LIMIT` clause
- Avoid N+1 query patterns
- Use JOINs instead of multiple queries

### Frontend
- Minimize AJAX requests
- Cache data in JavaScript variables
- Use event delegation for dynamic content
- Lazy load modules on demand

### Static Assets
- Minify JavaScript and CSS (not currently implemented)
- Use CDN for libraries (Axios, Font Awesome)
- Browser caching via headers

## Security Considerations

### Production Checklist
- [ ] Change Flask secret key from default
- [ ] Use HTTPS only (enforced by Vercel)
- [ ] Validate all user input
- [ ] Use parameterized queries (already implemented)
- [ ] Enable CSRF protection (not currently implemented)
- [ ] Set secure session cookies
- [ ] Implement rate limiting
- [ ] Regular security audits

### Secret Management
- Never commit `.env` file
- Use Vercel environment variables for production
- Rotate database passwords regularly
- Use strong Flask secret key

## Monitoring

### Health Check
```python
@app.get("/")
def health():
    return "ok", 200
```

### Database Health
```python
from app.config_mysql import test_connection

if test_connection():
    print("✅ Database connected")
else:
    print("❌ Database connection failed")
```

## Backup & Recovery

### Database Backup
- Manual exports via MySQL client
- Scheduled backups (not automated)
- Store backups securely off-site

### Application Backup
- Git repository is source of truth
- Tag releases for easy rollback
- Document configuration changes

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Error: Can't connect to MySQL server
```
Solution: Check environment variables, verify network access

#### Import Errors
```
ModuleNotFoundError: No module named 'app'
```
Solution: Ensure `app/__init__.py` exists, check Python path

#### Session Issues
```
User logged out unexpectedly
```
Solution: Check Flask secret key consistency, verify session timeout

#### Static Files Not Loading
```
404 on /static/js/script.js
```
Solution: Verify file exists in `app/static/`, check `url_for()` usage

### Debug Mode

Enable debug mode in development:
```python
app.run(debug=True)
```

Never enable in production:
```python
app.run(debug=False)  # Production
```

## Deployment Workflow

### Development to Production
1. Develop and test locally
2. Commit changes to git
3. Push to main branch
4. Vercel automatically deploys
5. Verify deployment via health check
6. Monitor logs for errors

### Rollback Procedure
1. Identify last working commit
2. Revert to that commit
3. Push to trigger redeployment
4. Verify functionality restored

## Scaling Considerations

### Current Limitations
- Single database server
- No connection pooling
- No caching layer
- No load balancing

### Future Improvements
- Implement Redis for caching
- Add connection pooling
- Use CDN for static assets
- Implement horizontal scaling
- Add database read replicas
