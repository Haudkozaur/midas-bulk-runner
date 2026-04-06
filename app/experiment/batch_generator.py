import csv
import os
import random
from pathlib import Path

from midas_civil import *

from experiment.cases.single_span_beam import SingleSpanBeam
import config as app_config
from experiment.experiment_config import ExperimentConfig



class BatchGenerator:
    def __init__(self, experiment_config: ExperimentConfig):
        self.config = experiment_config
        self.config.validate()
        self.rng = random.Random(self.config.random_seed)

        self.single_span_beam = SingleSpanBeam(
            config=self.config.model_config,
            rng=self.rng,
        )

    def run(self) -> None:
        self._initialize_midas()
        self._ensure_output_dir()

        rows: list[dict] = []

        for i in range(1, self.config.n_models + 1):
            print(f"\n--- Generating model {i}/{self.config.n_models} ---")

            try:
                self._reset_model_if_possible()

                sampled = self.single_span_beam.sample_parameters()
                model_meta = self.single_span_beam.build_model(sampled)

                Model.create()

                model_file_path = self._build_model_file_path(i)
                print(f"Saving MIDAS model to: {model_file_path}")
                Model.saveAs(str(model_file_path))

                Model.analyse()

                results = self._collect_results(model_meta)
                status = "OK"
                error_message = ""

            except Exception as ex:
                sampled = {}
                results = {name: None for name in self.config.results_to_save}
                status = "ERROR"
                error_message = str(ex)
                print(f"Model {i} failed: {ex}")

            row = {}

            if self.config.save_inputs:
                row.update(sampled)

            row.update(results)

            if self.config.save_analysis_status:
                row["analysis_status"] = status
                row["error_message"] = error_message

            rows.append(row)

        self._write_csv(rows)
        print(f"\nDone. Dataset saved to: {self.config.output_csv_path}")

    def _initialize_midas(self) -> None:
        app_config.validate_config()
        MAPI_KEY(app_config.MIDAS_MAPI_KEY)
        MAPI_BASEURL(app_config.MIDAS_BASE_URL)

    def _ensure_output_dir(self) -> None:
        csv_dir = os.path.dirname(self.config.output_csv_path)
        if csv_dir:
            os.makedirs(csv_dir, exist_ok=True)

        if self.config.output_model_dir:
            os.makedirs(self.config.output_model_dir, exist_ok=True)

    def _build_model_file_path(self, model_index: int) -> Path:
        return Path(self.config.output_model_dir) / f"model_{model_index:04d}.mcb"

    def _collect_results(self, model_meta: dict) -> dict:
        result_names = self.config.results_to_save
        out = {}

        loadcase = [model_meta["udl_case_result_name"]]

        if "mid_deflection_dz" in result_names:
            disp_df = Result.TABLE(
                "DISPLACEMENTG",
                keys=model_meta["mid_nodes"],
                loadcase=loadcase,
            )
            out["mid_deflection_dz"] = self._first_value(disp_df, "DZ")

        if "left_reaction_fz" in result_names:
            reaction_left_df = Result.TABLE(
                "REACTIONG",
                keys=model_meta["left_nodes"],
                loadcase=loadcase,
            )
            out["left_reaction_fz"] = self._first_value(reaction_left_df, "FZ")

        if "right_reaction_fz" in result_names:
            reaction_right_df = Result.TABLE(
                "REACTIONG",
                keys=model_meta["right_nodes"],
                loadcase=loadcase,
            )
            out["right_reaction_fz"] = self._first_value(reaction_right_df, "FZ")

        return out

    def _first_value(self, df, column_name: str):
        if df is None:
            return None

        if column_name not in df.columns:
            return None

        if df.height == 0:
            return None

        value = df[column_name][0]
        try:
            return float(value)
        except Exception:
            return value

    def _write_csv(self, rows: list[dict]) -> None:
        if not rows:
            return

        fieldnames = list(rows[0].keys())

        with open(self.config.output_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _reset_model_if_possible(self) -> None:
        try:
            Model.close()
        except Exception:
            pass

        try:
            Model.new()
        except Exception:
            pass

        try:
            Model.clear()
        except Exception:
            pass

        Model.units(force="KN", length="M")
        Model.type()