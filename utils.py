from pathlib import Path
from typing import Optional

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import sqlalchemy as sa
from gtfs_functions import Feed

TIMEZONE = "America/Vancouver"


def strictmode(s: pd.Series):
    mode = pd.Series.mode(s)
    if len(mode) > 1:
        print(s.name)
        raise ValueError(f"Multiple modes found: {s.value_counts()}")
    return mode.item()


class RouteInfo:
    feed: Feed
    db_path: str
    route: str
    directions: tuple[str, str]
    _segments: gpd.GeoDataFrame
    _point_data: dict[int, gpd.GeoDataFrame]

    def __init__(
        self, feed: Feed, db_path: str, route: str, directions: tuple[str, str]
    ):
        self.feed = feed
        self.db_path = db_path
        self.route = route
        self.directions = directions
        self._segments = feed.segments.query("route_id == @route")
        self._point_data = {}

    def plot_route(self, directions=(0, 1), figsize=(8, 10)):
        fig, axs = plt.subplots(
            1, len(directions), figsize=figsize, sharex=True, sharey=True
        )
        for i, direction in enumerate(directions):
            self._segments.query("direction_id == @direction").plot(
                column="segment_id", ax=axs[i]
            )
            axs[i].set_title(
                f"{self.route} - {self.directions[direction]} ({direction})"
            )
        return fig

    def _vehicle_positions(self, direction: int) -> gpd.GeoDataFrame:
        query = sa.text(
            """
            select
                latitude,
                longitude,
                start_time,
                timestamp,
                speed,
                odometer,
                vehicle_id,
                route_id,
                direction_id,
                stop_id,
                current_status,
                trip_id
            from vehicle_positions
            where route_id = :route and direction_id = :direction
            order by timestamp
            """
        )

        vehicle_positions = pd.read_sql_query(
            query,
            self.db_path,
            params={"route": self.route, "direction": direction},
        )
        vehicle_positions["timestamp"] = pd.to_datetime(
            vehicle_positions["timestamp"], unit="s", utc=True
        ).dt.tz_convert(TIMEZONE)
        vehicle_positions["start_time"] = pd.to_datetime(
            vehicle_positions["start_time"], unit="s", utc=True
        ).dt.tz_convert(TIMEZONE)
        vehicle_positions["timestamp_binned"] = vehicle_positions["timestamp"].dt.round(
            "h"
        )
        vehicle_positions["hour_of_day"] = vehicle_positions["timestamp"].dt.hour
        vehicle_positions["speed_km"] = vehicle_positions["speed"] * 3.6
        vehicle_positions = gpd.GeoDataFrame(
            vehicle_positions,
            geometry=gpd.points_from_xy(
                vehicle_positions["longitude"],
                vehicle_positions["latitude"],
                crs="WGS-84",
            ),
        )
        return vehicle_positions

    def points(self, direction: int) -> gpd.GeoDataFrame:
        points = self._point_data.get(direction)
        if points is None:
            vehicle_positions = self._vehicle_positions(direction)
            route_segments = self._segments.query("direction_id == @direction")
            route_segments = route_segments.to_crs("EPSG:26910")
            route_segments["shape"] = route_segments["geometry"]
            segments_by_shape = route_segments.groupby("shape_id")

            join_cols = ["trip_id", "route_id", "direction_id"]
            vehicle_positions = vehicle_positions.to_crs("EPSG:26910").join(
                self.feed.trips_patterns.set_index(join_cols), on=join_cols
            )
            points = vehicle_positions.groupby("shape_id").apply(
                lambda x: x.sjoin_nearest(
                    segments_by_shape.get_group(x.name),
                    max_distance=12,
                    rsuffix="segment",
                )  # 12 meters/40 feet
            )
            self._point_data[direction] = points.to_crs("WGS-84")
        return points

    def plot_points(
        self,
        direction: int,
        *,
        save_dir: Optional[Path] = None,
        colour_scale=px.colors.diverging.Portland_r,
        mapbox_style="open-street-map",
        height=1000,
        zoom=12,
        **kwargs,
    ):
        points = self.points(direction)
        fig = px.scatter_mapbox(
            points,
            lat="latitude",
            lon="longitude",
            # size="speed_km",
            # size_max=10,
            color="speed_km",
            range_color=(0, 80),
            color_continuous_scale=colour_scale,
            mapbox_style=mapbox_style,
            hover_data=[
                "vehicle_id",
                "speed_km",
                "timestamp",
                "stop_id",
                "current_status",
                "start_time",
                "trip_id",
            ],
            animation_frame="hour_of_day",
            animation_group="trip_id",
            height=height,
            zoom=zoom,
            **kwargs,
        )

        if save_dir is not None:
            filename = f"{direction}-{self.directions[direction]}_points.html"
            fig.write_html(save_dir / filename, auto_play=False, include_plotlyjs="cdn")
        return fig

    def plot_slow_zones(
        self,
        direction: int,
        threshold: float = 15,
        *,
        save_dir: Optional[Path] = None,
        colour_scale="magma",
        mapbox_style="open-street-map",
        height=1000,
        zoom=12,
        **kwargs,
    ):
        points = self.points(direction).query("speed_km < @threshold")
        fig = px.density_mapbox(
            points,
            lat="latitude",
            lon="longitude",
            # z="speed_km",
            radius=10,
            color_continuous_scale=colour_scale,
            mapbox_style=mapbox_style,
            hover_data=[
                "vehicle_id",
                "speed_km",
                "timestamp",
                "stop_id",
                "current_status",
                "start_time",
                "trip_id",
            ],
            animation_frame="hour_of_day",
            animation_group="trip_id",
            height=height,
            zoom=zoom,
            **kwargs,
        )

        if save_dir is not None:
            filename = f"{direction}-{self.directions[direction]}_slow_zones.html"
            fig.write_html(save_dir / filename, auto_play=False, include_plotlyjs="cdn")
        return fig

    def plot_hourly(
        self,
        direction: int,
        time_range=(10, 60),
        reference_hour: Optional[int] = None,
        *,
        save_dir: Optional[Path] = None,
        colour_scale=px.colors.diverging.Portland,
        mapbox_style="open-street-map",
        height=1000,
        zoom=12,
        **kwargs,
    ):
        points = self.points(direction)
        segment_times = gpd.GeoDataFrame(
            points.groupby(["segment_id", "trip_id", "start_time", "shape"])
            .agg({"timestamp": ["min", "max", "median"]})
            .droplevel(0, axis=1)
            .reset_index()
            .rename(
                columns={"shape": "geometry", "min": "enter_time", "max": "exit_time"}
            )
        )
        segment_times["travel_time"] = (
            segment_times["exit_time"] - segment_times["enter_time"]
        ).dt.total_seconds()
        segment_times["hour_of_day"] = segment_times.pop("median").dt.hour
        hourly_segment_times = gpd.GeoDataFrame(
            segment_times.query("travel_time > 0")
            .groupby(["segment_id", "hour_of_day", "geometry"])
            .agg({"travel_time": "describe"})
            .droplevel(0, axis=1)
            .reset_index()
        )

        time_col = "mean"
        if reference_hour is not None:
            ref_times = (
                hourly_segment_times.pivot_table(
                    index="hour_of_day", columns="segment_id", values="mean"
                )
                .loc[reference_hour]
                .fillna(0)[hourly_segment_times["segment_id"]]
                .reset_index(drop=True)
            )
            cmp_times = hourly_segment_times[time_col]
            time_col = f"{time_col}_diff_{reference_hour:02d}"
            hourly_segment_times[time_col] = cmp_times - ref_times

        hourly_segment_times = hourly_segment_times.join(
            self._segments.set_index("segment_id").drop(columns=["geometry"]),
            on="segment_id",
        )
        hourly_segment_times.sort_values("hour_of_day", inplace=True)
        buffered_geo = (
            hourly_segment_times["geometry"]
            .to_crs("EPSG:26910")
            .buffer(10, cap_style=2)
        )

        fig = px.choropleth_mapbox(
            hourly_segment_times,
            locations=hourly_segment_times.index,
            geojson=buffered_geo.to_crs("WGS-84"),
            color=time_col,
            range_color=time_range,
            color_continuous_scale=colour_scale,
            mapbox_style=mapbox_style,
            category_orders={"hour_of_day": list(range(24))},
            opacity=0.9,
            zoom=zoom,
            hover_data={
                time_col: True,
                "std": True,
                "25%": True,
                "50%": True,
                "75%": True,
                "count": True,
                "segment_id": True,
                "start_stop_name": True,
                "end_stop_name": True,
                "distance_m": True,
            },
            height=height,
            animation_frame="hour_of_day",
            animation_group="segment_id",
            **kwargs,
        )
        fig.update_traces(marker_line_width=0)

        if save_dir is not None:
            filename = (
                f"{direction}-{self.directions[direction]}_hourly_{reference_hour}.html"
            )
            fig.write_html(save_dir / filename, auto_play=False, include_plotlyjs="cdn")
        return fig

    def plot_hourly_distributions(
        self,
        direction: int,
        colour_sequence=px.colors.qualitative.Dark24,
        clip_threshold=1000,
        show_variants=False,
        *,
        save_dir: Optional[Path] = None,
        **kwargs,
    ):
        points = self.points(direction)
        segment_times = (
            points.groupby(
                [
                    "pattern_name",
                    "segment_id",
                    "start_stop_name",
                    "start_stop_id",
                    "end_stop_name",
                    "end_stop_id",
                    "trip_id",
                    "start_time",
                    "shape",
                ]
            )
            .agg({"timestamp": ["min", "max", "median"], "stop_sequence": [strictmode]})
            .droplevel(0, axis=1)
            .reset_index()
            .rename(
                columns={
                    "min": "enter_time",
                    "max": "exit_time",
                    "strictmode": "stop_sequence",
                }
            )
        )

        travel_times = segment_times["exit_time"] - segment_times["enter_time"]
        segment_times["travel_time"] = travel_times.dt.total_seconds()
        segment_times["hour_of_day"] = segment_times.pop("median").dt.hour
        hourly_segment_times = segment_times.query(
            "travel_time > 0 and travel_time < @clip_threshold"
        )
        hourly_segment_times["segment_name"] = (
            segment_times["start_stop_name"] + " ... " + segment_times["end_stop_name"]
        )
        hourly_segment_times.sort_values(
            ["hour_of_day", "pattern_name", "stop_sequence"], inplace=True
        )
        pattern_names = sorted(hourly_segment_times["pattern_name"].unique())

        fig = px.box(
            hourly_segment_times,
            x="start_stop_name",
            y="travel_time",
            color="hour_of_day",
            color_discrete_sequence=colour_sequence,
            category_orders={
                "hour_of_day": list(range(24)),
                "pattern_name": pattern_names,
            },
            hover_name="segment_name",
            boxmode="overlay",
            points="all",
            range_y=(0, clip_threshold),
            hover_data={
                "stop_sequence": True,
                "start_stop_name": True,
                "end_stop_name": True,
                "segment_id": True,
            },
            facet_row="pattern_name" if show_variants else None,
            facet_row_spacing=0.01,
            **kwargs,
        )
        # To avoid hogging all system resources, don't show any hours by default
        for trace in fig.data[1:]:
            trace.visible = "legendonly"
        if "facet_row" in kwargs and len(pattern_names) > 2:
            fig.update_xaxes(row=len(pattern_names), side="top", showticklabels=True)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))

        if save_dir is not None:
            filename = f"{direction}-{self.directions[direction]}_distr_hourly.html"
            fig.write_html(save_dir / filename, auto_play=False, include_plotlyjs="cdn")
        return fig
