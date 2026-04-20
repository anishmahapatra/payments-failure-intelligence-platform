from training.scripts.generate_synthetic_data import main as generate_data


def main() -> None:
    generate_data()
    print("Local sample data generated")


if __name__ == "__main__":
    main()

