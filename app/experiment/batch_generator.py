import csv
import os
import random
from pathlib import Path
import polars as pl

from midas_civil import *

from experiment.cases.single_span_post_tensioned_beam import SingleSpanPostTensionedBeam
from experiment.cases.single_span_beam import SingleSpanBeam

import config as app_config
from experiment.experiment_config import ExperimentConfig, Model_Type


class BatchGenerator:
    def __init__(self, experiment_config: ExperimentConfig):
        self.config = experiment_config
        self.config.validate()
        self.rng = random.Random(self.config.random_seed)

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
                # self._dump_debug_tables(model_meta)
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

    def _get_debug_excel_path(self) -> Path:
        csv_path = Path(self.config.output_csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        return csv_path.parent / "results_debug.xlsx"

    def _write_df_to_excel(
        self,
        df,
        sheet_name: str,
        excel_path: Path | None = None,
    ) -> None:
        if df is None:
            return

        if getattr(df, "height", 0) == 0:
            return

        if excel_path is None:
            excel_path = self._get_debug_excel_path()

        if not isinstance(df, pl.DataFrame):
            return

        mode = "a" if excel_path.exists() else "w"

        with open(excel_path, mode="ab" if mode == "a" else "wb") as _:
            pass

        df.write_excel(
            workbook=str(excel_path),
            worksheet=sheet_name,
        )

    def _dump_result_table_to_excel(
        self,
        table_type: str,
        keys: list[int],
        loadcases: list[str],
        sheet_name: str,
    ) -> None:
        df = Result.TABLE(
            table_type,
            keys=keys,
            loadcase=loadcases,
        )
        self._write_df_to_excel(df, sheet_name)

    def _dump_beam_force_to_excel(
        self,
        beam_ids: list[int],
        loadcases: list[str],
        sheet_name: str,
        parts: list[str] | None = None,
        components: list[str] | None = None,
    ) -> None:
        if parts is None:
            parts = ["PartI", "PartJ"]

        if components is None:
            components = ["all"]

        df = Result.TABLE.BeamForce(
            keys=beam_ids,
            loadcase=loadcases,
            parts=parts,
            components=components,
        )
        self._write_df_to_excel(df, sheet_name)

    def _dump_beam_force_prestress_to_excel(
        self,
        beam_ids: list[int],
        loadcases: list[str],
        sheet_name: str,
        parts: list[str] | None = None,
        components: list[str] | None = None,
    ) -> None:
        if parts is None:
            parts = ["PartI", "PartJ"]

        if components is None:
            components = ["all"]

        df = Result.TABLE.BeamForce_StaticPrestress(
            keys=beam_ids,
            loadcase=loadcases,
            parts=parts,
            components=components,
        )
        self._write_df_to_excel(df, sheet_name)


    def _dump_user_defined_table_to_excel(
        self,
        table_name: str,
        sheet_name: str,
        summary: int = 0,
    ) -> None:
        df = Result.UserDefinedTable(
            table_name,
            summary=summary,
            force_unit="KN",
            len_unit="M",
        )
        self._write_df_to_excel(df, sheet_name)

    def _dump_debug_tables(self, model_meta: dict) -> None:
        loadcases = [
            model_meta["self_weight_result_name"],
            model_meta["udl_case_result_name"],
        ]

        if "prestress_case_result_name" in model_meta:
            loadcases.append(model_meta["prestress_case_result_name"])

        beam_ids = model_meta["beam_ids"]
        mid_index = len(beam_ids) // 2

        if len(beam_ids) % 2 == 0:
            mid_beam_ids = [beam_ids[mid_index - 1], beam_ids[mid_index]]
        else:
            mid_beam_ids = [beam_ids[mid_index]]

        self._dump_result_table_to_excel(
            table_type="DISPLACEMENTG",
            keys=model_meta["mid_nodes"],
            loadcases=loadcases,
            sheet_name="mid_disp",
        )

        self._dump_result_table_to_excel(
            table_type="REACTIONG",
            keys=model_meta["left_nodes"],
            loadcases=loadcases,
            sheet_name="left_reaction",
        )

        self._dump_result_table_to_excel(
            table_type="REACTIONG",
            keys=model_meta["right_nodes"],
            loadcases=loadcases,
            sheet_name="right_reaction",
        )

        self._dump_beam_force_to_excel(
            beam_ids=mid_beam_ids,
            loadcases=loadcases,
            sheet_name="mid_beam_force",
            parts=["PartI", "Part1/4", "PartJ"],
            components=["all"],
        )

        if "prestress_case_result_name" in model_meta:
            self._dump_beam_force_prestress_to_excel(
                beam_ids=mid_beam_ids,
                loadcases=[model_meta["prestress_case_result_name"]],
                sheet_name="mid_beam_prestress",
                parts=["PartI", "Part1/4", "PartJ"],
                components=["all"],
            )

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