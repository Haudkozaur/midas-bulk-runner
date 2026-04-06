from pathlib import Path
from datetime import datetime

from experiment.experiment_config import ExperimentConfig, Model_Type
from experiment.batch_generator import BatchGenerator


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():

    # Getting paths and timpestamp to save models and results in a unique directory for each run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "models_data" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "results.csv"


    # DEFINE EXPERIMENT CONFIGURATION HERE
    cfg = ExperimentConfig(
        
        n_models=1, # number of models to generate
        model_type=Model_Type.SINGLE_SPAN_POST_TENSIONED_BEAM, # type of model to generate
        random_seed=None, # random seed for reproducibility, use same seed to get same results, use None for random seed
        save_inputs=True, # whether to save input parameters in the output csv
        save_analysis_status=True, # whether to save analysis status (OK/ERROR) in the output csv
        results_to_save=[
            "mid_deflection_dz",
            "left_reaction_fz",
            "right_reaction_fz",
            "mid_moment_sw",
            "mid_moment_udl",
            "mid_moment_ps",
            "mid_moment_total",
        ], # results to save in the output csv.

        # Paths to save results and models - these will be created in a unique directory for each run based on timestamp
        output_csv_path=str(output_path),
        output_model_dir=str(run_dir),
    )

    generator = BatchGenerator(cfg)
    generator.run()


if __name__ == "__main__":
    main()