from app.db.session import initialize_database


def main() -> None:
    initialize_database()
    print("Database tables initialized")


if __name__ == "__main__":
    main()

