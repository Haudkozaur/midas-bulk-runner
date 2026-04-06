# MidasBulkRunner

MidasBulkRunner is a lightweight framework for automated generation of large numbers of MIDAS Civil NX models and extraction of selected analysis results.

## Usage

The entry point is `main.py`.

In `main.py`, define the main experiment settings such as:
- number of models,
- model type,
- output paths,
- results to save.

Detailed parameters for each model type are defined in `experiment_config.py`.

### Required .env file:

MIDAS_MAPI_KEY=your_key

MIDAS_BASE_URL=your_url