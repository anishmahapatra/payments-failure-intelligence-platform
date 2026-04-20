from training.scripts.generate_synthetic_data import generate_synthetic_payments


def test_synthetic_data_generator_shape_and_labels() -> None:
    frame = generate_synthetic_payments(num_rows=200, seed=7)
    assert len(frame) == 200
    assert {"label_failure", "label_failure_class", "payment_amount_bucket"}.issubset(frame.columns)
    assert frame["amount"].min() > 0
    assert set(frame["label_failure_class"].unique())

