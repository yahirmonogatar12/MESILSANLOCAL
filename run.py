from app.routes import app

if __name__ == '__main__':
    app.run(host='192.168.0.211', port=5000, debug=True)

# waitress-serve --port=5002 app.routes:app
