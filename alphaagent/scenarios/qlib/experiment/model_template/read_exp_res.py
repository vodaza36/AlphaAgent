import pickle
import sys
from pathlib import Path

import pandas as pd
import qlib
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient
from ruamel.yaml import YAML

# Read qlib_init config from the config file
config_path = Path(__file__).resolve().parent / "conf.yaml"
if config_path.exists():
    yaml = YAML(typ="safe", pure=True)
    with open(config_path, "r") as fp:
        config = yaml.load(fp)
    qlib_init_config = config.get("qlib_init", {})
    qlib.init(**qlib_init_config)
else:
    # Fallback to default init if config not found
    qlib.init()

from qlib.workflow import R

# here is the documents of the https://qlib.readthedocs.io/en/latest/component/recorder.html

# TODO: list all the recorder and metrics

# Assuming you have already listed the experiments
experiments = R.list_experiments()

# Iterate through each experiment to find the latest recorder
experiment_name = None
latest_recorder = None
for experiment in experiments:
    recorders = R.list_recorders(experiment_name=experiment)
    for recorder_id in recorders:
        if recorder_id is not None:
            experiment_name = experiment
            recorder = R.get_recorder(recorder_id=recorder_id, experiment_name=experiment)
            end_time = recorder.info["end_time"]
            if latest_recorder is None or end_time > latest_recorder.info["end_time"]:
                latest_recorder = recorder

# Check if the latest recorder is found
if latest_recorder is None:
    print("No recorders found")
    sys.exit(1)
else:
    print(f"Latest recorder: {latest_recorder}")

    # Load the specified file from the latest recorder
    metrics = pd.Series(latest_recorder.list_metrics())

    output_path = Path(__file__).resolve().parent / "qlib_res.csv"
    metrics.to_csv(output_path)

    print(f"Output has been saved to {output_path}")

    try:
        ret_data_frame = latest_recorder.load_object("portfolio_analysis/report_normal_1day.pkl")
        ret_data_frame.to_pickle("ret.pkl")
    except Exception as e:
        print(f"Error: Failed to load portfolio_analysis/report_normal_1day.pkl: {e}")
        print("PortAnaRecord may have failed during backtest execution.")
        sys.exit(1)
