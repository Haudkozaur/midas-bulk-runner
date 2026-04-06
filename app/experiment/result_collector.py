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
        ts_lc = model_meta.get("ts_case_result_name")
        ps_lc = model_meta.get("prestress_case_result_name")

        # =========================
        # MIDSPAN DEFLECTIONS
        # =========================
        if "mid_deflection_sw" in result_names:
            out["mid_deflection_sw"] = self._get_mid_deflection_dz(
                mid_nodes=model_meta["mid_nodes"],
                loadcase=sw_lc,
            )

        if "mid_deflection_udl" in result_names:
            out["mid_deflection_udl"] = self._get_mid_deflection_dz(
                mid_nodes=model_meta["mid_nodes"],
                loadcase=udl_lc,
            )

        if "mid_deflection_ts" in result_names:
            out["mid_deflection_ts"] = (
                self._get_mid_deflection_dz(
                    mid_nodes=model_meta["mid_nodes"],
                    loadcase=ts_lc,
                )
                if ts_lc is not None
                else None
            )

        if "mid_deflection_ps" in result_names:
            out["mid_deflection_ps"] = (
                self._get_mid_deflection_dz(
                    mid_nodes=model_meta["mid_nodes"],
                    loadcase=ps_lc,
                )
                if ps_lc is not None
                else None
            )

        if "mid_deflection_dz" in result_names or "mid_deflection_total" in result_names:
            values = [
                self._get_mid_deflection_dz(
                    mid_nodes=model_meta["mid_nodes"],
                    loadcase=sw_lc,
                ),
                self._get_mid_deflection_dz(
                    mid_nodes=model_meta["mid_nodes"],
                    loadcase=udl_lc,
                ),
            ]

            if ts_lc is not None:
                values.append(
                    self._get_mid_deflection_dz(
                        mid_nodes=model_meta["mid_nodes"],
                        loadcase=ts_lc,
                    )
                )

            if ps_lc is not None:
                values.append(
                    self._get_mid_deflection_dz(
                        mid_nodes=model_meta["mid_nodes"],
                        loadcase=ps_lc,
                    )
                )

            total_deflection = self._sum_not_none(values)

            if "mid_deflection_dz" in result_names:
                out["mid_deflection_dz"] = total_deflection

            if "mid_deflection_total" in result_names:
                out["mid_deflection_total"] = total_deflection

        # =========================
        # LEFT SUPPORT REACTIONS
        # =========================
        if "left_reaction_sw" in result_names:
            out["left_reaction_sw"] = self._get_support_reaction_fz(
                support_nodes=model_meta["left_nodes"],
                loadcase=sw_lc,
            )

        if "left_reaction_udl" in result_names:
            out["left_reaction_udl"] = self._get_support_reaction_fz(
                support_nodes=model_meta["left_nodes"],
                loadcase=udl_lc,
            )

        if "left_reaction_ts" in result_names:
            out["left_reaction_ts"] = (
                self._get_support_reaction_fz(
                    support_nodes=model_meta["left_nodes"],
                    loadcase=ts_lc,
                )
                if ts_lc is not None
                else None
            )

        if "left_reaction_ps" in result_names:
            out["left_reaction_ps"] = (
                self._get_support_reaction_fz(
                    support_nodes=model_meta["left_nodes"],
                    loadcase=ps_lc,
                )
                if ps_lc is not None
                else None
            )

        if "left_reaction_fz" in result_names or "left_reaction_total" in result_names:
            values = [
                self._get_support_reaction_fz(
                    support_nodes=model_meta["left_nodes"],
                    loadcase=sw_lc,
                ),
                self._get_support_reaction_fz(
                    support_nodes=model_meta["left_nodes"],
                    loadcase=udl_lc,
                ),
            ]

            if ts_lc is not None:
                values.append(
                    self._get_support_reaction_fz(
                        support_nodes=model_meta["left_nodes"],
                        loadcase=ts_lc,
                    )
                )

            if ps_lc is not None:
                values.append(
                    self._get_support_reaction_fz(
                        support_nodes=model_meta["left_nodes"],
                        loadcase=ps_lc,
                    )
                )

            total_left_reaction = self._sum_not_none(values)

            if "left_reaction_fz" in result_names:
                out["left_reaction_fz"] = total_left_reaction

            if "left_reaction_total" in result_names:
                out["left_reaction_total"] = total_left_reaction

        # =========================
        # RIGHT SUPPORT REACTIONS
        # =========================
        if "right_reaction_sw" in result_names:
            out["right_reaction_sw"] = self._get_support_reaction_fz(
                support_nodes=model_meta["right_nodes"],
                loadcase=sw_lc,
            )

        if "right_reaction_udl" in result_names:
            out["right_reaction_udl"] = self._get_support_reaction_fz(
                support_nodes=model_meta["right_nodes"],
                loadcase=udl_lc,
            )

        if "right_reaction_ts" in result_names:
            out["right_reaction_ts"] = (
                self._get_support_reaction_fz(
                    support_nodes=model_meta["right_nodes"],
                    loadcase=ts_lc,
                )
                if ts_lc is not None
                else None
            )

        if "right_reaction_ps" in result_names:
            out["right_reaction_ps"] = (
                self._get_support_reaction_fz(
                    support_nodes=model_meta["right_nodes"],
                    loadcase=ps_lc,
                )
                if ps_lc is not None
                else None
            )

        if "right_reaction_fz" in result_names or "right_reaction_total" in result_names:
            values = [
                self._get_support_reaction_fz(
                    support_nodes=model_meta["right_nodes"],
                    loadcase=sw_lc,
                ),
                self._get_support_reaction_fz(
                    support_nodes=model_meta["right_nodes"],
                    loadcase=udl_lc,
                ),
            ]

            if ts_lc is not None:
                values.append(
                    self._get_support_reaction_fz(
                        support_nodes=model_meta["right_nodes"],
                        loadcase=ts_lc,
                    )
                )

            if ps_lc is not None:
                values.append(
                    self._get_support_reaction_fz(
                        support_nodes=model_meta["right_nodes"],
                        loadcase=ps_lc,
                    )
                )

            total_right_reaction = self._sum_not_none(values)

            if "right_reaction_fz" in result_names:
                out["right_reaction_fz"] = total_right_reaction

            if "right_reaction_total" in result_names:
                out["right_reaction_total"] = total_right_reaction

        # =========================
        # TOTAL SUPPORT REACTION
        # useful equilibrium check
        # =========================
        if (
            "support_reaction_total_sw" in result_names
            or "support_reaction_total_udl" in result_names
            or "support_reaction_total_ts" in result_names
            or "support_reaction_total_ps" in result_names
            or "support_reaction_total_fz" in result_names
        ):
            left_sw = self._get_support_reaction_fz(model_meta["left_nodes"], sw_lc)
            right_sw = self._get_support_reaction_fz(model_meta["right_nodes"], sw_lc)

            left_udl = self._get_support_reaction_fz(model_meta["left_nodes"], udl_lc)
            right_udl = self._get_support_reaction_fz(model_meta["right_nodes"], udl_lc)

            total_sw = self._sum_not_none([left_sw, right_sw])
            total_udl = self._sum_not_none([left_udl, right_udl])

            total_ts = None
            if ts_lc is not None:
                left_ts = self._get_support_reaction_fz(model_meta["left_nodes"], ts_lc)
                right_ts = self._get_support_reaction_fz(model_meta["right_nodes"], ts_lc)
                total_ts = self._sum_not_none([left_ts, right_ts])

            total_ps = None
            if ps_lc is not None:
                left_ps = self._get_support_reaction_fz(model_meta["left_nodes"], ps_lc)
                right_ps = self._get_support_reaction_fz(model_meta["right_nodes"], ps_lc)
                total_ps = self._sum_not_none([left_ps, right_ps])

            total_all = self._sum_not_none(
                [value for value in [total_sw, total_udl, total_ts, total_ps] if value is not None]
            )

            if "support_reaction_total_sw" in result_names:
                out["support_reaction_total_sw"] = total_sw

            if "support_reaction_total_udl" in result_names:
                out["support_reaction_total_udl"] = total_udl

            if "support_reaction_total_ts" in result_names:
                out["support_reaction_total_ts"] = total_ts

            if "support_reaction_total_ps" in result_names:
                out["support_reaction_total_ps"] = total_ps

            if "support_reaction_total_fz" in result_names:
                out["support_reaction_total_fz"] = total_all

        # =========================
        # MIDSPAN MOMENTS
        # =========================
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

        if "mid_moment_ts" in result_names:
            out["mid_moment_ts"] = (
                self._get_midspan_moment_my(
                    beam_ids=model_meta["beam_ids"],
                    loadcase=ts_lc,
                )
                if ts_lc is not None
                else None
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

            if ts_lc is not None:
                values.append(
                    self._get_midspan_moment_my(
                        beam_ids=model_meta["beam_ids"],
                        loadcase=ts_lc,
                    )
                )

            if ps_lc is not None:
                values.append(
                    self._get_midspan_moment_my(
                        beam_ids=model_meta["beam_ids"],
                        loadcase=ps_lc,
                    )
                )

            out["mid_moment_total"] = self._sum_not_none(values)

        return out

    def _get_mid_deflection_dz(self, mid_nodes: list[int], loadcase: str):
        return self._get_single_result_value(
            table_type="DISPLACEMENTG",
            keys=mid_nodes,
            loadcase=loadcase,
            column_candidates=["DZ"],
        )

    def _get_support_reaction_fz(self, support_nodes: list[int], loadcase: str):
        return self._get_single_result_value(
            table_type="REACTIONG",
            keys=support_nodes,
            loadcase=loadcase,
            column_candidates=["FZ"],
        )

    def _get_single_result_value(
        self,
        table_type: str,
        keys: list[int],
        loadcase: str,
        column_candidates: list[str],
    ):
        if loadcase is None:
            return None

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
        if not beam_ids or loadcase is None:
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