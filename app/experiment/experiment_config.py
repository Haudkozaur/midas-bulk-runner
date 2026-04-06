from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from experiment.ranges import FloatRange, IntRange

# ENUM to specify which type of model to generate
class Model_Type(Enum):
    SINGLE_SPAN_BEAM = "single_span_beam"
    SINGLE_SPAN_POST_TENSIONED_BEAM = "single_span_post_tensioned_beam"
    SINGLE_SPAN_BRIDGE = "single_span_bridge"
    MULTI_SPAN_BEAM = "multi_span_beam"


# Configuration for cases

@dataclass
class SingleSpanPostTensionedBeamConfig:
    span_length_m: FloatRange = field(default_factory=lambda: FloatRange("random", 10.0, 30.0))
    beam_height_m: FloatRange = field(default_factory=lambda: FloatRange("random", 0.6, 1.2))
    beam_width_m: FloatRange = field(default_factory=lambda: FloatRange("random", 0.25, 0.50))
    udl_kn_per_m: FloatRange = field(default_factory=lambda: FloatRange("random", 5.0, 30.0))
    beam_divisions: IntRange = field(default_factory=lambda: IntRange("random", 10, 30))

    concrete_material_name: str = "C40/50"
    concrete_material_code: str = "EN04(RC)"
    concrete_material_grade: str = "C40/50"

    section_name: str = "RECT_PSC"
    section_shape: str = "DBUSER"
    section_db: str = "USER"
    section_db_name: str = "RECT_PSC"
    section_id: int = 2

    left_support: str = "111000"
    right_support: str = "011000"

    self_weight_case: str = "Self Weight"
    udl_case: str = "UDL"
    prestress_case: str = "Prestress"

    n_tendons: int = 1
    tendon_force_kn: float = 220.0
    tendon_ecc_start_m: float = -0.05
    tendon_ecc_mid_m: float = -0.35
    tendon_ecc_end_m: float = -0.05
    tendon_area_mm2: float = 150.0
    tendon_profile_type: str = "parabolic"

    def validate(self) -> None:
        self.span_length_m.validate("span_length_m")
        self.beam_height_m.validate("beam_height_m")
        self.beam_width_m.validate("beam_width_m")
        self.udl_kn_per_m.validate("udl_kn_per_m")
        self.beam_divisions.validate("beam_divisions")

        self.tendon_force_kn.validate("tendon_force_kn")
        self.tendon_ecc_start_m.validate("tendon_ecc_start_m")
        self.tendon_ecc_mid_m.validate("tendon_ecc_mid_m")
        self.tendon_ecc_end_m.validate("tendon_ecc_end_m")
        self.tendon_area_mm2.validate("tendon_area_mm2")

        if self.beam_divisions.min < 2:
            raise ValueError("beam_divisions.min must be >= 2")

        if self.tendon_profile_type not in {"parabolic", "straight"}:
            raise ValueError("tendon_profile_type must be 'parabolic' or 'straight'")

@dataclass
class SingleSpanBeamConfig:
    span_length_m: FloatRange = field(default_factory=lambda: FloatRange("random", 5.0, 20.0))
    udl_kn_per_m: FloatRange = field(default_factory=lambda: FloatRange("random", 5.0, 30.0))
    beam_divisions: IntRange = field(default_factory=lambda: IntRange("fixed", 10))

    material_name: str = "A36"
    material_code: str = "ASTM(S)"
    material_grade: str = "A36"

    section_name: str = "W8x35"
    section_shape: str = "H"
    section_db: str = "AISC"
    section_db_name: str = "W8x35"
    section_id: int = 1

    left_support: str = "111000"   # pin
    right_support: str = "011000"  # roller

    self_weight_case: str = "Self Weight"
    udl_case: str = "UDL"

    def validate(self) -> None:
        self.span_length_m.validate("span_length_m")
        self.udl_kn_per_m.validate("udl_kn_per_m")
        self.beam_divisions.validate("beam_divisions")

        if self.beam_divisions.min < 2:
            raise ValueError("beam_divisions.min must be >= 2")


# Main experiment configuration
# Start parameters are defined in main.py when creating the ExperimentConfig object
@dataclass
class ExperimentConfig:
    n_models: int
    model_type: Model_Type = Model_Type.SINGLE_SPAN_BEAM
    random_seed: int | None = None
    output_csv_path: str = "results.csv"
    output_model_dir: str = "models_data"
    save_inputs: bool = True
    save_analysis_status: bool = True
    results_to_save: list[str] = field(
        default_factory=lambda: [
            "mid_deflection_dz",
            "left_reaction_fz",
            "right_reaction_fz",
        ]
    )
    # in this part we have to add all currently supported Model_Types as possible types for model_config, 
    # and then in __post_init__ we set the default config based on the model_type
    ###
    model_config: Union[
        SingleSpanBeamConfig,
        SingleSpanPostTensionedBeamConfig,
        None,
    ] = None

    def __post_init__(self) -> None:
        if self.model_config is None:
            match self.model_type:
                case Model_Type.SINGLE_SPAN_BEAM:
                    self.model_config = SingleSpanBeamConfig()

                case Model_Type.SINGLE_SPAN_POST_TENSIONED_BEAM:
                    self.model_config = SingleSpanPostTensionedBeamConfig()

                case _:
                    raise ValueError(f"Unsupported model_type: {self.model_type}")

    ###

    def validate(self) -> None:
        if self.n_models <= 0:
            raise ValueError("n_models must be > 0")

        if self.random_seed is not None and not isinstance(self.random_seed, int):
            raise ValueError("random_seed must be int or None")

        if not self.output_csv_path or not self.output_csv_path.strip():
            raise ValueError("output_csv_path cannot be empty")

        if not self.output_model_dir or not self.output_model_dir.strip():
            raise ValueError("output_model_dir cannot be empty")

        if not isinstance(self.results_to_save, list):
            raise ValueError("results_to_save must be a list[str]")

        if len(self.results_to_save) == 0:
            raise ValueError("results_to_save cannot be empty")

        allowed_results = {
            "mid_deflection_dz",
            "left_reaction_fz",
            "right_reaction_fz",
        }

        invalid_results = [r for r in self.results_to_save if r not in allowed_results]
        if invalid_results:
            raise ValueError(
                f"Unsupported results_to_save: {invalid_results}. "
                f"Allowed values: {sorted(allowed_results)}"
            )

        if not isinstance(self.model_type, Model_Type):
            raise ValueError(f"model_type must be an instance of ModelType, got: {self.model_type}")

        if self.model_config is None:
            raise ValueError("model_config cannot be None")

        self.model_config.validate()