import os
import random
import socket
import time

from datetime import datetime, timezone

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import URL

app = Flask(__name__)

# Configuration de la base de données
# Configuration de la base de données
if os.environ.get("POSTGRES_USER"):
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get(
            "DB_HOST",
            "postgres.cat.svc.cluster.local"
        ),
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ["POSTGRES_DB"]
    )
else:
    # SQLite pour les tests locaux
    database_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///cats.db"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}
db = SQLAlchemy(app)

# Images de chats disponibles
images = [
    "https://media.giphy.com/media/cfuL5gqFDreXxkWQ4o/giphy.gif",
    "https://media.giphy.com/media/W8krmZSDxPIfm/giphy.gif",
    "https://media.giphy.com/media/UxGNvgpU1hoAw/giphy.gif",
    "https://media.giphy.com/media/WLNASdXoq0ZtC/giphy.gif",
    "https://media.giphy.com/media/HYpZKsyLOn1ks/giphy.gif",
    "https://media.giphy.com/media/l8px6snusvpII/giphy.gif",
    "https://media.giphy.com/media/l0Iy9Kry5yhBSwQSs/giphy.gif",
    "https://media.giphy.com/media/7SfAXqgRgh0li/giphy.gif",
    "https://media.giphy.com/media/W80Y9y1XwiL84/giphy.gif"
]


# Modèle de données : une consultation de chat
class CatVisit(db.Model):
    __tablename__ = "cat_visits"

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    pod_name = db.Column(db.String(255), nullable=False)
    visited_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


# Initialisation explicite de la base via Flask CLI
@app.cli.command("init-db")
def initialize_database():
    """Attend PostgreSQL et crée les tables nécessaires."""

    for attempt in range(10):
        try:
            db.create_all()
            print("Database initialized successfully.")
            return

        except OperationalError:
            print(f"Database unavailable: attempt {attempt + 1}/10")

            if attempt == 9:
                raise

            time.sleep(3)


# Page d'accueil : affiche une image et enregistre la visite
@app.route("/")
def index():
    url = random.choice(images)
    hostname = socket.gethostname()

    visit = CatVisit(
        image_url=url,
        pod_name=hostname
    )

    db.session.add(visit)
    db.session.commit()

    return render_template(
        "index.html",
        url=url,
        hostname=hostname
    )


# Historique des 50 dernières consultations
@app.route("/history")
def history():
    visits = (
        CatVisit.query
        .order_by(desc(CatVisit.visited_at))
        .limit(50)
        .all()
    )

    return render_template(
        "history.html",
        visits=visits
    )


# Statistiques : total et top 5 des images
@app.route("/stats")
def stats():
    total_visits = db.session.query(
        func.count(CatVisit.id)
    ).scalar()

    popular_images = (
        db.session.query(
            CatVisit.image_url,
            func.count(CatVisit.id).label("total")
        )
        .group_by(CatVisit.image_url)
        .order_by(desc("total"))
        .limit(5)
        .all()
    )

    return render_template(
        "stats.html",
        total_visits=total_visits,
        popular_images=popular_images
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)