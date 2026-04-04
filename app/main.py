from pathlib import Path
from datetime import datetime

from experiment.experiment_config import ExperimentConfig
from experiment.batch_generator import BatchGenerator


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_dir = PROJECT_ROOT / "models_data" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    output_path = run_dir / "results.csv"

    cfg = ExperimentConfig(
        n_models=3,
        output_csv_path=str(output_path),
        output_model_dir=str(run_dir),
        results_to_save=[
            "mid_deflection_dz",
            "left_reaction_fz",
            "right_reaction_fz",
        ],
    )

    generator = BatchGenerator(cfg)
    generator.run()


if __name__ == "__main__":
    main()