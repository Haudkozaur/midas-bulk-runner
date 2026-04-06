import os
import random
from pathlib import Path

from midas_civil import *

from experiment.cases.single_span_post_tensioned_beam import SingleSpanPostTensionedBeam
from experiment.cases.single_span_beam import SingleSpanBeam
from experiment.writers.csv_writer import CsvWriter

import config as app_config
from experiment.experiment_config import ExperimentConfig, Model_Type


class BatchGenerator:
    def __init__(self, experiment_config: ExperimentConfig):
        self.config = experiment_config
        self.config.validate()
        self.rng = random.Random(self.config.random_seed)
        self.results_writer = CsvWriter(self.config.output_csv_path)

        match self.config.model_type:
            case Model_Type.SINGLE_SPAN_BEAM:
                self.model_generator = SingleSpanBeam(
                    config=self.config.model_config,
                    rng=self.rng,
                )

            case Model_Type.SINGLE_SPAN_POST_TENSIONED_BEAM:
                self.model_generator = SingleSpanPostTensionedBeam(
                    config=self.config.model_config,
                    rng=self.rng,
                )

            case _:
                raise ValueError(f"Unsupported model_type: {self.config.model_type}")

    def run(self) -> None:
        self._initialize_midas()
        self._ensure_output_dir()

        rows: list[dict] = []

        for i in range(1, self.config.n_models + 1):
            print(f"\n--- Generating model {i}/{self.config.n_models} ---")

            try:
                self._reset_model_if_possible()

                sampled = self.model_generator.sample_parameters()
                model_meta = self.model_generator.build_model(sampled)

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

        self.results_writer.write(rows)
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

        sw_lc = model_meta["self_weight_result_name"]
        udl_lc = model_meta["udl_case_result_name"]
        ps_lc = model_meta.get("prestress_case_result_name")

        loadcases = [sw_lc, udl_lc]
        if ps_lc is not None:
            loadcases.append(ps_lc)

        if "mid_deflection_dz" in result_names:
            values = [
                self._get_single_result_value(
                    table_type="DISPLACEMENTG",
                    keys=model_meta["mid_nodes"],
                    loadcase=lc,
                    column_candidates=["DZ"],
                )
                for lc in loadcases
            ]
            out["mid_deflection_dz"] = self._sum_not_none(values)

        if "left_reaction_fz" in result_names:
            values = [
                self._get_single_result_value(
                    table_type="REACTIONG",
                    keys=model_meta["left_nodes"],
                    loadcase=lc,
                    column_candidates=["FZ"],
                )
                for lc in loadcases
            ]
            out["left_reaction_fz"] = self._sum_not_none(values)

        if "right_reaction_fz" in result_names:
            values = [
                self._get_single_result_value(
                    table_type="REACTIONG",
                    keys=model_meta["right_nodes"],
                    loadcase=lc,
                    column_candidates=["FZ"],
                )
                for lc in loadcases
            ]
            out["right_reaction_fz"] = self._sum_not_none(values)

        if "mid_moment_sw" in result_names:
            out["mid_moment_sw"] = self._get_midspan_moment_my(
                beam_ids=model_meta["beam_ids"],
                loadcase=sw_lc,
            )

        if "mid_moment_udl" in result_names:
            out["mid_moment_udl"] = self._get_midspan_moment_my(
                beam_ids=model_meta["beam_ids"],
                loadcase=udl_lc,
            )

        if "mid_moment_ps" in result_names:
            out["mid_moment_ps"] = (
                self._get_midspan_moment_my(
                    beam_ids=model_meta["beam_ids"],
                    loadcase=ps_lc,
                )
                if ps_lc is not None
                else None
            )

        if "mid_moment_total" in result_names:
            values = [
                self._get_midspan_moment_my(
                    beam_ids=model_meta["beam_ids"],
                    loadcase=sw_lc,
                ),
                self._get_midspan_moment_my(
                    beam_ids=model_meta["beam_ids"],
                    loadcase=udl_lc,
                ),
            ]

            if ps_lc is not None:
                values.append(
                    self._get_midspan_moment_my(
                        beam_ids=model_meta["beam_ids"],
                        loadcase=ps_lc,
                    )
                )

            out["mid_moment_total"] = self._sum_not_none(values)

        return out

    def _get_single_result_value(
        self,
        table_type: str,
        keys: list[int],
        loadcase: str,
        column_candidates: list[str],
    ):
        df = Result.TABLE(
            table_type,
            keys=keys,
            loadcase=[loadcase],
        )

        if df is None or df.height == 0:
            return None

        for column_name in column_candidates:
            if column_name in df.columns:
                value = df[column_name][0]
                try:
                    return float(value)
                except Exception:
                    return value

        return None

    def _get_midspan_moment_my(self, beam_ids: list[int], loadcase: str):
        if not beam_ids:
            return None

        # for even number of elements the middle node is PartJ
        left_mid_beam_id = beam_ids[len(beam_ids) // 2 - 1]

        df = Result.TABLE.BeamForce(
            keys=[left_mid_beam_id],
            loadcase=[loadcase],
            parts=["PartJ"],
        )

        if df is None or df.height == 0:
            return None

        for column_name in ["Moment-y", "My", "MY"]:
            if column_name in df.columns:
                value = df[column_name][0]
                try:
                    return float(value)
                except Exception:
                    return value

        return None

    def _sum_not_none(self, values: list):
        numeric_values = [v for v in values if v is not None]
        if not numeric_values:
            return None
        return sum(numeric_values)

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