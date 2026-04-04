from dataclasses import dataclass, field
from enum import Enum

# ENUM to specify which type of model to generate
class ModelType(Enum):
    SINGLE_SPAN_BEAM = "single_span_beam"
    SINGLE_SPAN_BRIDGE = "single_span_bridge"
    MULTI_SPAN_BEAM = "multi_span_beam"

#########
# Configuration classes for the experiment

@dataclass
class FloatRange:
    min: float
    max: float

    def validate(self, name: str) -> None:
        if self.min > self.max:
            raise ValueError(f"{name}: min cannot be greater than max")

@dataclass
class IntRange:
    min: int
    max: int

    def validate(self, name: str) -> None:
        if self.min > self.max:
            raise ValueError(f"{name}: min cannot be greater than max")

#########


@dataclass
class SingleSpanBeamConfig:
    span_length_m: FloatRange = field(default_factory=lambda: FloatRange(5.0, 20.0))
    udl_kn_per_m: FloatRange = field(default_factory=lambda: FloatRange(5.0, 30.0))
    beam_divisions: IntRange = field(default_factory=lambda: IntRange(10, 20))

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


@dataclass
class ExperimentConfig:
    n_models: int
    model_type: ModelType = ModelType.SINGLE_SPAN_BEAM
    random_seed: int | None = 42
    output_csv_path: str = "output/single_span_beam_dataset.csv"
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

    single_span_beam: SingleSpanBeamConfig = field(default_factory=SingleSpanBeamConfig)

    def validate(self) -> None:
        if self.n_models <= 0:
            raise ValueError("n_models must be > 0")

        if self.model_type != ModelType.SINGLE_SPAN_BEAM:
            raise ValueError(f"Unsupported model_type: {self.model_type}")

        self.single_span_beam.validate()