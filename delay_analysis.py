# %%
from pathlib import Path

from gtfs_functions import Feed

import utils

# %%
# DB_PATH = "sqlite:///data/realtime_2024-06-01.db"
DB_PATH = "sqlite:///data/realtime_2024-09-09.db"
PLOT_PARAMS = {
    "center": {"lat": 48.4566, "lon": -123.3763},
}
SAVE_DIR = Path("figures")


# %%
# feed = Feed("data/static_2024-05-17.zip")
feed = Feed("data/static_2024-09-09.zip")

# %%
route_6_dir = SAVE_DIR / "6-VIC"
route_6_dir.mkdir(exist_ok=True)
route_6 = utils.RouteInfo(feed, DB_PATH, "6-VIC", ("Royal Oak", "Downtown"))

# %%
# route_6.plot_route()

# %%
for direction in range(2):
    route_6.plot_points(direction, **PLOT_PARAMS, save_dir=route_6_dir)
    # route_6.plot_hourly(direction, **PLOT_PARAMS, save_dir=route_6_dir)
    # route_6.plot_hourly(
    #     direction, **PLOT_PARAMS, save_dir=route_6_dir, reference_hour=6
    # )
    route_6.plot_hourly_distributions(direction, save_dir=route_6_dir)
    route_6.plot_slow_zones(direction, **PLOT_PARAMS, save_dir=route_6_dir)

# %%
route_10_dir = SAVE_DIR / "10-VIC"
route_10_dir.mkdir(exist_ok=True)
route_10 = utils.RouteInfo(feed, DB_PATH, "10-VIC", ("Royal Jubilee", "James Bay"))

# %%
# route_10.plot_route()

# %%
for direction in range(2):
    route_10.plot_points(direction, **PLOT_PARAMS, save_dir=route_10_dir)
    # route_10.plot_hourly(direction, **PLOT_PARAMS, save_dir=route_10_dir)
    # route_10.plot_hourly(
    #     direction, **PLOT_PARAMS, save_dir=route_10_dir, reference_hour=6
    # )
    route_10.plot_hourly_distributions(direction, save_dir=route_10_dir)
    route_10.plot_slow_zones(direction, **PLOT_PARAMS, save_dir=route_10_dir)

# %%
route_26_dir = SAVE_DIR / "26-VIC"
route_26_dir.mkdir(exist_ok=True)
route_26 = utils.RouteInfo(feed, DB_PATH, "26-VIC", ("UVic", "Dockyard"))

# # %%
# route_26.plot_route()

# # %%
for direction in range(2):
    route_26.plot_points(direction, **PLOT_PARAMS, save_dir=route_26_dir)
    # route_26.plot_hourly(direction, **PLOT_PARAMS, save_dir=route_26_dir)
    # route_26.plot_hourly(
    #     direction, **PLOT_PARAMS, save_dir=route_26_dir, reference_hour=6
    # )
    route_26.plot_hourly_distributions(direction, save_dir=route_26_dir)
    route_26.plot_slow_zones(direction, **PLOT_PARAMS, save_dir=route_26_dir)

# %%
route_24_dir = SAVE_DIR / "24-VIC"
route_24_dir.mkdir(exist_ok=True)
route_24 = utils.RouteInfo(feed, DB_PATH, "24-VIC", ("Cedar Hill", "Tillicum Ctr"))

# %%
# route_24.plot_route()

# %%
for direction in range(2):
    route_24.plot_points(direction, **PLOT_PARAMS, save_dir=route_24_dir)
    # route_24.plot_hourly(direction, **PLOT_PARAMS, save_dir=route_24_dir)
    # route_24.plot_hourly(
    #     direction, **PLOT_PARAMS, save_dir=route_24_dir, reference_hour=6
    # )
    route_24.plot_hourly_distributions(direction, save_dir=route_24_dir)
    route_24.plot_slow_zones(direction, **PLOT_PARAMS, save_dir=route_24_dir)