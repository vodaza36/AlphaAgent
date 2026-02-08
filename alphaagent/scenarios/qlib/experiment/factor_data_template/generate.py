import os
import qlib
from qlib.data import D

if __name__ == '__main__':
    # Use environment variable for data path (defaults to ~/.qlib/qlib_data/us_data for backwards compatibility)
    provider_uri = os.environ.get("QLIB_DATA_URI", "~/.qlib/qlib_data/us_data")
    qlib.init(provider_uri=provider_uri)

    instruments = D.instruments()
    fields = ["$open", "$close", "$high", "$low", "$volume"]  # , "$amount", "$turn", "$pettm", "$pbmrq"
    data = D.features(instruments, fields, freq="day").swaplevel().sort_index().loc["2015-01-01":].sort_index()

    # 计算收益率
    data["$return"] = data.groupby(level=0)["$close"].pct_change().fillna(0)

    print(data)

    data.to_hdf("./daily_pv_all.h5", key="data")

    fields = ["$open", "$close", "$high", "$low", "$volume"]  # , "$amount", "$turn", "$pettm", "$pbmrq"
    data = (
        (
            D.features(instruments, fields, freq="day")
            .swaplevel()
            .sort_index()
        )
        .swaplevel()
        .loc[data.reset_index()["instrument"].unique()[:100]]
        .swaplevel()
        .sort_index()
    )

    # 计算收益率
    data["$return"] = data.groupby(level=0)["$close"].pct_change().fillna(0)
    print(data)
    data.to_hdf("./daily_pv_debug.h5", key="data")