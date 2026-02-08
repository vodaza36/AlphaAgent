"""
Factor workflow with session control
"""

from typing import Any
import fire
import signal
import sys
import threading
from functools import wraps
import time
import ctypes
import os
from alphaagent.app.qlib_rd_loop.conf import ALPHA_AGENT_FACTOR_PROP_SETTING
from alphaagent.app.utils.data import is_data_initialized
from alphaagent.components.workflow.alphaagent_loop import AlphaAgentLoop
from alphaagent.core.exception import FactorEmptyError
from alphaagent.log import logger
from alphaagent.log.time import measure_time
from alphaagent.oai.llm_conf import LLM_SETTINGS




def force_timeout():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Prioritize timeout parameter
            seconds = LLM_SETTINGS.factor_mining_timeout
            def handle_timeout(signum, frame):
                logger.error(f"Forcing program termination, exceeded {seconds} seconds")
                sys.exit(1)

            # Set signal handler
            signal.signal(signal.SIGALRM, handle_timeout)
            # Set alarm
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Cancel alarm
                signal.alarm(0)
            return result
        return wrapper
    return decorator


@force_timeout()
def main(path=None, step_n=None, potential_direction=None, stop_event=None):
    """
    Autonomous alpha factor mining.

    Args:
        path: Session path
        step_n: Number of steps
        potential_direction: Initial market hypothesis/direction for factor mining
        stop_event: Stop event

    You can continue running session by

    .. code-block:: python

        dotenv run -- python rdagent/app/qlib_rd_loop/factor_alphaagent.py $LOG_PATH/__session__/1/0_propose  --step_n 1  --potential_direction "[Initial Direction (Optional)]"  # `step_n` is a optional paramter

    """
    # Check if data is initialized
    if not is_data_initialized():
        logger.error("Qlib data not initialized!")
        logger.error("Please run: alphaagent init")
        logger.error("This will extract the bundled market data (~2 minutes)")
        sys.exit(1)

    try:
        use_local = os.getenv("USE_LOCAL", "True").lower()
        use_local = True if use_local in ["true", "1"] else False
        logger.info(f"Use {'Local' if use_local else 'Docker container'} to execute factor backtest")
        if path is None:
            model_loop = AlphaAgentLoop(ALPHA_AGENT_FACTOR_PROP_SETTING, potential_direction=potential_direction, stop_event=stop_event, use_local=use_local)
        else:
            model_loop = AlphaAgentLoop.load(path, use_local=use_local, stop_event=stop_event)
        model_loop.run(step_n=step_n, stop_event=stop_event)
    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}")
        raise
    finally:
        logger.info("Program execution completed or terminated")

if __name__ == "__main__":
    fire.Fire(main)
