from midas_civil import Result

from experiment.experiment_config import ExperimentConfig


class ResultCollector:
    def __init__(self, config: ExperimentConfig):
        self.config = config

    def collect(self, model_meta: dict) -> dict:
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