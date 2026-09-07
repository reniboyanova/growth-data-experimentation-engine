from app.database import Base, engine
from app.models import Event

def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables ready:", ", ".join(Base.metadata.tables))

if __name__ == "__main__":
    main()