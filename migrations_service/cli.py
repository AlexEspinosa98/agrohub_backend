import typer
from alembic import command
from alembic.config import Config
from pathlib import Path

app = typer.Typer(help="Gestor de migraciones con Alembic")

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_CFG = str(BASE_DIR / "alembic.ini")

@app.command()
def make(message: list[str] = typer.Argument(None)):
    """Genera una nueva migración (revision --autogenerate)."""
    alembic_cfg = Config(ALEMBIC_CFG)
    msg = " ".join(message) if message else "auto migration"
    command.revision(alembic_cfg, autogenerate=True, message=msg)
    typer.echo(f"📦 Migración creada: {msg}")
    


@app.command()
def upgrade(revision: str = "head"):
    """Aplica migraciones (upgrade head por defecto)."""
    alembic_cfg = Config(ALEMBIC_CFG)
    command.upgrade(alembic_cfg, revision)
    typer.echo(f"🚀 Migración aplicada hasta {revision}")

@app.command()
def downgrade(revision: str = "-1"):
    """Revierte migraciones (downgrade -1 por defecto)."""
    alembic_cfg = Config(ALEMBIC_CFG)
    command.downgrade(alembic_cfg, revision)
    typer.echo(f"↩️ Migración revertida a {revision}")

if __name__ == "__main__":
    app()
