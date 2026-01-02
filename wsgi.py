from app import app, db

with app.app_context():
    db.create_all()

application = app

if __name__ == '__main__':
    app.run()

