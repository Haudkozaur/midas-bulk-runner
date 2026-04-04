import csv
import os
import random
from pathlib import Path

from midas_civil import *

import config as app_config
from experiment.experiment_config import ExperimentConfig, ModelType

class BatchGenerator:
    def __init__(self, experiment_config: ExperimentConfig):
        self.config = experiment_config
        self.config.validate()
        self.rng = random.Random(self.config.random_seed)

    def run(self) -> None:
        self._initialize_midas()
        self._ensure_output_dir()

        rows: list[dict] = []

        for i in range(1, self.config.n_models + 1):
            print(f"\n--- Generating model {i}/{self.config.n_models} ---")

            sampled = self._sample_parameters()

            try:
                self._reset_model_if_possible()
                model_meta = self._build_model(sampled)

                Model.create()

                model_file_path = self._build_model_file_path(i)
                print(f"Saving MIDAS model to: {model_file_path}")
                Model.saveAs(str(model_file_path))

                Model.analyse()

                results = self._collect_results(model_meta)
                status = "OK"
                error_message = ""

            except Exception as ex:
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

    def _sample_parameters(self) -> dict:
        if self.config.model_type == ModelType.SINGLE_SPAN_BEAM:
            beam_cfg = self.config.single_span_beam

            beam_divisions = self.rng.randint(
                beam_cfg.beam_divisions.min,
                beam_cfg.beam_divisions.max,
            )

            if beam_divisions % 2 != 0:
                beam_divisions += 1

            return {
                "model_type": ModelType.SINGLE_SPAN_BEAM,
                "span_length_m": round(
                    self.rng.uniform(
                        beam_cfg.span_length_m.min,
                        beam_cfg.span_length_m.max,
                    ),
                    4,
                ),
                "udl_kn_per_m": round(
                    self.rng.uniform(
                        beam_cfg.udl_kn_per_m.min,
                        beam_cfg.udl_kn_per_m.max,
                    ),
                    4,
                ),
                "beam_divisions": beam_divisions,
            }

        raise ValueError(f"Unsupported model_type: {self.config.model_type}")

    def _build_model(self, sampled: dict) -> dict:
        if sampled["model_type"] == ModelType.SINGLE_SPAN_BEAM:
            return self._build_single_span_beam(sampled)

        raise ValueError(f"Unsupported model_type: {sampled['model_type']}")


    def _build_single_span_beam(self, sampled: dict) -> dict:
        beam_cfg = self.config.single_span_beam

        L = sampled["span_length_m"]
        w = sampled["udl_kn_per_m"]
        div = sampled["beam_divisions"]

        Material.STEEL(
            beam_cfg.material_name,
            beam_cfg.material_code,
            beam_cfg.material_grade,
        )

        Section.DB(
            beam_cfg.section_name,
            beam_cfg.section_shape,
            beam_cfg.section_db,
            beam_cfg.section_db_name,
            id=beam_cfg.section_id,
        )

        Element.Beam.SDL(
            [0, 0, 0],
            [1, 0, 0],
            L,
            n=div,
            sect=beam_cfg.section_id,
        )
        # TODO invent better way to solve problem described in comment below. 
        # MIDAS keeps increasing element IDs between iterations,
        # so we take the last `div` elements, which correspond
        # to the beam created in the current model.

        all_beam_ids_in_box = sorted(Model.Select.Box([0, 0, 0], [L, 0, 0], "ELEM_ID"))

        if len(all_beam_ids_in_box) < div:
            raise ValueError(
                f"Expected at least {div} beam elements in selection box, got {len(all_beam_ids_in_box)}"
            )

        beam_ids = all_beam_ids_in_box[-div:]

        left_nodes = sorted(Model.Select.Box([0, 0, 0], [0, 0, 0]))
        right_nodes = sorted(Model.Select.Box([L, 0, 0], [L, 0, 0]))

        if not left_nodes:
            raise ValueError("No left support nodes found at x=0")
        if not right_nodes:
            raise ValueError(f"No right support nodes found at x={L}")

        Boundary.Support(left_nodes, beam_cfg.left_support)
        Boundary.Support(right_nodes, beam_cfg.right_support)

        Load.SW(beam_cfg.self_weight_case)

        Load.Beam(
            beam_ids,
            beam_cfg.udl_case,
            "",
            direction="GZ",
            D=[0, 1],
            P=[-w, -w],
        )

        mid_x = L / 2.0
        mid_nodes = sorted(Model.Select.Box([mid_x, 0, 0], [mid_x, 0, 0]))
        if not mid_nodes:
            raise ValueError(f"No mid-span node found at x={mid_x}")

        return {
            "span_length_m": L,
            "left_nodes": left_nodes,
            "right_nodes": right_nodes,
            "mid_nodes": mid_nodes,
            "beam_ids": beam_ids,
            "udl_case_result_name": f"{beam_cfg.udl_case}(ST)",
            "self_weight_result_name": f"{beam_cfg.self_weight_case}(ST)",
        }

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