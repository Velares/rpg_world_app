from pathlib import Path

from app.database import Database
from app.game_state import GameState
from app.gui import RPGWorldApp
from app.table_loader import TableLoader


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    tables_dir = base_dir / "data" / "tables"
    database_path = base_dir / "data" / "saves" / "worlds.db"
    loader = TableLoader(tables_dir)
    database = Database(database_path)
    state = GameState(loader, database)
    app = RPGWorldApp(state)
    app.mainloop()


if __name__ == "__main__":
    main()
