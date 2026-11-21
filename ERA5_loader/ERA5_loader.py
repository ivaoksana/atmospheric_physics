from ecmwf.datastores import Client

import pandas as pd
import os
from datetime import datetime, date
from numbers import Real
from typing import Any
import logging
import sys
from pathlib import Path
import re
import math
import hashlib
import json

REGIONS = {

    # ==================================================
    # GLOBAL AND POLAR REGIONS
    # ==================================================
    "global": [90, -180, -90, 180],
    "arctic": [90, -180, 60, 180],
    "antarctica": [-60, -180, -90, 180],
    "southern_ocean": [-50, -180, -90, 180],

    # ==================================================
    # EUROPE
    # ==================================================
    "europe": [72, -25, 34, 45],
    "western_europe": [60, -15, 35, 15],
    "northern_europe": [72, -10, 54, 35],
    "southern_europe": [46, -10, 34, 30],
    "eastern_europe": [60, 20, 40, 50],
    "central_europe": [55, 5, 40, 25],
    "iberian_peninsula": [44, -10, 35, 5],
    "scandinavia": [72, 4, 54, 32],
    "baltic_region": [66, 10, 53, 31],
    "british_isles": [61, -12, 49, 3],
    "alps": [48, 5, 44, 17],
    "mediterranean": [48, -10, 30, 40],
    "black_sea": [48, 27, 40, 42],

    # ==================================================
    # AFRICA
    # ==================================================
    "africa": [38, -20, -35, 52],
    "north_africa": [38, -18, 20, 38],
    "west_africa": [25, -20, 0, 15],
    "east_africa": [20, 28, -12, 52],
    "central_africa": [15, 10, -15, 30],
    "southern_africa": [-15, 10, -35, 42],
    "sahel": [20, -18, 10, 40],
    "congo_basin": [5, 10, -10, 30],

    # ==================================================
    # ASIA
    # ==================================================
    "asia": [80, 25, -10, 180],
    "central_asia": [55, 45, 30, 90],
    "east_asia": [55, 100, 15, 150],
    "south_asia": [40, 60, 5, 100],
    "southeast_asia": [30, 90, -15, 145],
    "north_asia": [80, 40, 50, 180],
    "siberia": [80, 60, 50, 180],
    "middle_east": [42, 25, 12, 65],
    "arabian_peninsula": [33, 34, 12, 60],
    "indian_subcontinent": [38, 60, 5, 100],
    "tibetan_plateau": [40, 70, 25, 105],
    "japan": [46, 127, 30, 150],
    "china": [54, 73, 18, 135],
    "indonesia": [10, 94, -12, 142],

    # ==================================================
    # NORTH AMERICA
    # ==================================================
    "north_america": [85, -170, 5, -50],
    "usa": [50, -125, 24, -66],
    "canada": [84, -141, 42, -52],
    "alaska": [72, -180, 51, -130],
    "greenland": [84, -75, 59, -10],
    "central_america": [33, -118, 5, -77],
    "mexico": [33, -118, 14, -86],
    "caribbean": [30, -90, 8, -58],

    # ==================================================
    # SOUTH AMERICA
    # ==================================================
    "south_america": [13, -82, -57, -34],
    "amazon_basin": [10, -80, -20, -45],
    "andes": [12, -82, -56, -65],
    "tropical_south_america": [15, -80, -25, -35],
    "southern_south_america": [-20, -75, -57, -35],
    "patagonia": [-38, -75, -56, -63],

    # ==================================================
    # OCEANIA
    # ==================================================
    "oceania": [0, 110, -50, 180],
    "australia": [-10, 112, -44, 154],
    "new_zealand": [-33, 165, -48, 180],
    "papua_new_guinea": [0, 140, -12, 160],

    # ==================================================
    # ATLANTIC OCEAN
    # ==================================================
    "atlantic_ocean": [70, -80, -60, 20],
    "north_atlantic": [70, -80, 0, 10],
    "tropical_atlantic": [30, -60, -30, 20],
    "south_atlantic": [0, -70, -60, 20],

    # ==================================================
    # PACIFIC OCEAN
    # ==================================================
    "pacific_ocean": [65, 120, -60, -70],
    "north_pacific": [65, 120, 0, -70],
    "tropical_pacific": [30, 120, -30, -70],
    "south_pacific": [0, 120, -60, -70],

    # ==================================================
    # INDIAN OCEAN
    # ==================================================
    "indian_ocean": [30, 30, -60, 120],
    "tropical_indian_ocean": [25, 30, -25, 120],

    # ==================================================
    # CLIMATE AND ATMOSPHERIC RESEARCH REGIONS
    # ==================================================
    "tropics": [30, -180, -30, 180],
    "equatorial_region": [10, -180, -10, 180],
    "northern_hemisphere": [90, -180, 0, 180],
    "southern_hemisphere": [0, -180, -90, 180],
    "nh": [90, -180, 0, 180],
    "sh": [0, -180, -90, 180],
    "subtropics_nh": [40, -180, 20, 180],
    "subtropics_sh": [-20, -180, -40, 180],
    "midlatitudes_nh": [60, -180, 30, 180],
    "midlatitudes_sh": [-30, -180, -60, 180],
    "polar_nh": [90, -180, 60, 180],
    "polar_sh": [-60, -180, -90, 180],

    # ==================================================
    # MONSOON REGIONS
    # ==================================================
    "south_asian_monsoon": [35, 60, 5, 100],
    "east_asian_monsoon": [50, 100, 15, 150],
    "west_african_monsoon": [25, -20, 0, 25],
    "australian_monsoon": [0, 110, -20, 155],

    # ==================================================
    # IMPORTANT CLIMATE MODES
    # ==================================================
    "enso_region": [5, -170, -5, -120],
    "nino4": [5, 160, -5, -150],
    "nino34": [5, -170, -5, -120],
    "nino3": [5, -150, -5, -90],
}
ERA5_PATH = Path(__file__).parent / "era5_parameters_database.csv"
DATABASE_PATH = Path(__file__).parent / "ERA5_requests.db"

def load_era5_database():
    if not ERA5_PATH.exists():
        raise FileNotFoundError(f"ERA5 parameter database not found: {ERA5_PATH}")

    return pd.read_csv(
        ERA5_PATH,
        sep=";",
        encoding="utf-8-sig"
    )

def search_era5_variables(
    keyword,
    level_type=None,
    parameter_type=None
):
    database = load_era5_database()

    search_columns = ["name", "cds_variable", "short_name"]

    # Search by keyword
    mask = pd.Series(False, index=database.index)

    for column in search_columns:
        mask |= database[column].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False
        )

    result = database[mask].copy()

    # Filter by level type
    if level_type is not None:
        result = result[
            result["level_type"].str.contains(
                level_type,
                case=False,
                na=False,
                regex=False
            )
        ]

    # Filter by parameter type
    if parameter_type is not None:
        result = result[
            result["parameter_type"].str.contains(
                parameter_type,
                case=False,
                na=False,
                regex=False
            )
        ]
    if result.empty:
        raise ValueError(
            f"No parameters found for keyword '{keyword}' "
            f"with level_type={level_type} and parameter_type={parameter_type}."
        )

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 40)
    pd.set_option("display.expand_frame_repr", True)

    print(f"There are following variables with keyword '{keyword}', "
          f"level_type:{level_type}, parameter_type:{parameter_type}:")

    output = (
        result.reset_index(drop=True)[
            ["name", "units", "cds_variable", "level_type", "parameter_type"]
        ].to_string(index=False)
    )

    separator = "-" * max(len(line) for line in output.splitlines())

    print(separator)
    print(output)
    print(separator)

    print("Note: `cds_variable` is used in CDS API download requests.\n")

    return result.reset_index(drop=True)

# Color Formatter for Logs
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[1;41m'
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


# Logger Factory
def get_logger(name='default', level=logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True

    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

import sqlite3
import json
from pathlib import Path


class ERA5RequestDatabase:

    def __init__(self, db_path="ERA5_requests.db"):

        self.db_path = Path(db_path)

        self._create_table()


    def _connect(self):

        return sqlite3.connect(self.db_path)


    def _create_table(self):

        with self._connect() as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (

                    request_id TEXT PRIMARY KEY,

                    dataset TEXT NOT NULL,

                    request TEXT NOT NULL,

                    output_file TEXT NOT NULL,

                    status TEXT,

                    created_at TEXT,

                    started_at TEXT,

                    finished_at TEXT,

                    downloaded INTEGER DEFAULT 0,

                    downloaded_at TEXT,

                    error TEXT,

                    request_hash TEXT
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_request_status ON requests(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_request_hash ON requests(request_hash)")



    def add_request(self, request_info):

        with self._connect() as conn:

            conn.execute("""
                INSERT INTO requests (
                    request_id,
                    dataset,
                    request,
                    output_file,
                    status,
                    created_at,
                    started_at,
                    finished_at,
                    downloaded,
                    downloaded_at,
                    error,
                    request_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_info["request_id"],
                request_info["dataset"],
                json.dumps(request_info["request"]),
                request_info["output_file"],
                request_info["status"],
                request_info["created_at"],
                request_info.get("started_at"),
                request_info.get("finished_at"),
                int(request_info.get("downloaded", False)),
                request_info.get("downloaded_at"),
                request_info.get("error"),
                request_info.get("request_hash"),
            ))


    def update_request(self, request_id, **kwargs):

        allowed_fields = {
            "status",
            "started_at",
            "finished_at",
            "downloaded",
            "downloaded_at",
            "error"
        }

        updates = {
            key: value
            for key, value in kwargs.items()
            if key in allowed_fields
        }

        if not updates:
            return

        if "downloaded" in updates:
            updates["downloaded"] = int(updates["downloaded"])

        columns = ", ".join(
            f"{key} = ?" for key in updates
        )

        values = list(updates.values())
        values.append(request_id)

        with self._connect() as conn:

            conn.execute(
                f"UPDATE requests SET {columns} WHERE request_id = ?",
                values
            )

    def get_request_by_hash(self, request_hash):
        """Retrieve a request using its configuration hash."""

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                     SELECT *
                FROM requests
                WHERE request_hash = ?
                AND status NOT IN ('failed', 'deleted')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (request_hash,)
            ).fetchone()

        if row is None:
            return None

        request_info = dict(row)
        request_info["request"] = json.loads(request_info["request"])
        request_info["downloaded"] = bool(request_info["downloaded"])

        return request_info


    def get_request(self, request_id):

        with self._connect() as conn:

            conn.row_factory = sqlite3.Row

            row = conn.execute(
                "SELECT * FROM requests WHERE request_id = ?",
                (request_id,)
            ).fetchone()

            if row is None:
                return None

            result = dict(row)
            result["request"] = json.loads(result["request"])
            result["downloaded"] = bool(result["downloaded"])

            return result


    def list_requests(self, status=None):

        with self._connect() as conn:

            conn.row_factory = sqlite3.Row

            if status is None:
                rows = conn.execute(
                    "SELECT * FROM requests ORDER BY created_at"
                ).fetchall()

            else:
                rows = conn.execute(
                    "SELECT * FROM requests WHERE status = ? ORDER BY created_at",
                    (status,)
                ).fetchall()

            results = []

            for row in rows:
                item = dict(row)
                item["request"] = json.loads(item["request"])
                item["downloaded"] = bool(item["downloaded"])
                results.append(item)

            return results

def submit_era5_data(
            output_dir,
            variable,
            current_date,
            mode="hourly",
            daily_statistic=None,
            frequency="1_hourly",
            time_zone="utc+00:00",
            times=None,
            pressure_levels=None,
            adjust_pressure_levels=False,
            area=None,
            grid_resolution=None,
            file_format="grib",
            logging=True,
        ):
        """
        Submit one ERA5 file for a specified date.

        Parameters
        ----------
        output_dir : str or os.PathLike
            Directory where the downloaded file will be saved.

        variable : str
            ERA5 variable to download (e.g., "2m_temperature").

        current_date : str, datetime or date
            Target date in "DD-MM-YYYY" format, datetime or date object.
            The date represents a single day for hourly and daily modes,
            or a month for monthly mode.

        mode : str, default "hourly"
            Temporal processing mode:
            - "hourly": hourly ERA5 data.
            - "daily": daily statistics derived from hourly data.
            - "monthly": monthly averaged ERA5 data.

        daily_statistic : str, optional
            Daily statistic to retrieve in daily mode.
            Available options depend on the dataset and variable.
            For pressure-level data, daily mean, maximum and minimum
            are available. Daily sum is available only for supported
            accumulated single-level variables.
            If None, the default daily statistic is used.

        frequency : str, default "1_hourly"
            Sub-daily sampling frequency used to calculate daily
            statistics. Used only in daily mode.

        time_zone : str, default "utc+00:00"
            Time zone used for daily aggregation.
            Used only in daily mode.

        times : list of str, optional
            Requested hours in "HH:MM" format (e.g., ["00:00", "06:00"]).
            Used only in hourly mode. If None, all 24 hourly time steps
            are requested.

        pressure_levels : list of str, int or float, optional
            Pressure levels in hPa. Values must be integer levels.
            If None, single-level data are requested.

        adjust_pressure_levels : bool, default False
            Controls how unavailable pressure levels are handled.

            - False: Raise a ValueError if one or more requested pressure
              levels are unavailable. The error message includes the nearest
              available pressure levels as suggestions.
            - True: Automatically replace unavailable pressure levels with
              the nearest available levels.

            Duplicate levels resulting from automatic replacement are removed,
            and the final list is sorted in descending order.
            Used only when pressure_levels is not None.

        area : list of float, optional
            Geographic bounding box in the format
            [North, West, South, East].

        grid_resolution : list of float or str, optional
            Output grid resolution in [dLon, dLat] format.
            Can also be provided as a slash-separated string, e.g. "0.25/0.25".
            If None, the dataset default resolution is used.

        file_format : str, default "grib"
            Output data format: "netcdf" or "grib".
            For daily statistics:
            - GRIB data are downloaded unarchived.
            - NetCDF data are downloaded as ZIP archives.

        logging : bool, default=True
            Enable logging.

        Returns
        -------
        str
            Path to the downloaded file.
        """
        logger = get_logger("download_era5_data")

        # 1. Validate output directory
        if not isinstance(output_dir, (str, os.PathLike)):
            raise TypeError("'output_dir' must be a string or path-like object")

        output_dir = os.fspath(output_dir) or "."

        # 2. Validate variable
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("'variable' must be a non-empty string")

        database = load_era5_database()

        # Select variables according to level type
        if pressure_levels is None:
            expected_level_type = "single_levels"
        else:
            expected_level_type = "pressure_levels"

        valid_variables = database.loc[database["level_type"] == expected_level_type,"cds_variable"].dropna().unique()

        if variable not in valid_variables:
            raise ValueError(f"Variable '{variable}' is not available for '{expected_level_type}'. "
                             f"Valid variables are: {valid_variables}")

        # 3. Validate date
        if isinstance(current_date, datetime):
            pass

        elif isinstance(current_date, date):
            current_date = datetime.combine(current_date, datetime.min.time())

        elif isinstance(current_date, str):
            try:
                current_date = datetime.strptime(current_date, "%d-%m-%Y")
            except ValueError:
                raise ValueError("'current_date' must have format 'DD-MM-YYYY'") from None

        else:
            raise TypeError(
                "'current_date' must be a datetime, date, or string in 'DD-MM-YYYY' format"
            )

        year = str(current_date.year)
        month = f"{current_date.month:02d}"
        day = f"{current_date.day:02d}"

        # 4. Validate mode
        valid_modes = {"hourly", "daily", "monthly"}

        if mode not in valid_modes:
            raise ValueError(f"'mode' must be one of {valid_modes}")

        # 5. Validate file format
        if not isinstance(file_format, str):
            raise TypeError("'file_format' must be a string.")

        file_format = file_format.strip().lower()

        if file_format not in {"netcdf", "grib"}:
            raise ValueError("'file_format' must be 'netcdf' or 'grib'.")

        elif file_format == "netcdf":
            if logging:
                logger.warning("The native format of MARS datasets is GRIB,"
                  " and this format is recommended for any operational use, such as deriving downstream products. "
                  "Please note that to ensure that data is accurate and sufficient metadata is included in the output,"
                  " your request may be split into multiple files when converted to netCDF.")

        # 6. Validate times
        if times is not None:

            if logging:
                logger.info("Sub-daily data for the HRES (stream=oper/wave) the analyses (type=an) are available hourly."
                        " The short forecasts, run twice daily from 06 and 18 UTC, provide hourly output forecast steps "
                        "from 0 to 18 hours (only steps 1 to 12 hours are available on the CDS disks). For the EDA, "
                        "the sub-daily non-wave data (stream=enda) are available every 3 hours but the sub-daily "
                        "wave data (stream=ewda) are available hourly in MARS and 3 hourly on the CDS disks.")

            if not isinstance(times, (list, tuple)) or not times:
                raise ValueError("'times' must be a non-empty list or tuple")

            for t in times:
                if not isinstance(t, str):
                    raise TypeError("Each time must be a string")
                try:
                    datetime.strptime(t, "%H:%M")
                except ValueError:
                    raise ValueError(f"Invalid time: {t}. Expected HH:MM")

                parsed_time = datetime.strptime(t, "%H:%M")

                if parsed_time.minute != 0:
                    raise ValueError(f"Invalid time: {t}. Hourly ERA5 requests require HH:00.")

            if len(times) != len(set(times)):
                raise ValueError("'times' must not contain duplicate values.")

        if mode != "hourly" and times is not None:
            raise ValueError("'times' can only be specified in hourly mode")

        # 7. Validate area
        if area is not None:

            if logging:
                logger.info(
                    "Area input formats:\n"
                    "  1. Predefined region name, e.g. 'NH', 'Europe', 'north_atlantic' (or North Atlantic).\n"
                    "  2. Custom coordinates: [North, West, South, East].\n"
                    "  * Longitude range: -180 to 180 degrees.\n"
                    "  * Latitude range: -90 to 90 degrees."
                )

            if isinstance(area, str):

                region = re.sub(r"[\s-]+", "_", area.strip().lower())

                if region not in REGIONS:
                    raise ValueError(
                        f"Unknown region '{area}'. Available regions: {', '.join(REGIONS)}. "
                        "Alternatively, provide custom coordinates as [North, West, South, East]."
                    )

                area = REGIONS[region]

                if logging:
                    logger.info("Region '%s' selected. Area: %s", region, area)

            else:

                if not isinstance(area, (list, tuple)) or len(area) != 4:
                    raise ValueError("'area' must be a region name or a list/tuple [North, West, South, East].")

                if not all(isinstance(x, Real) and not isinstance(x, bool) for x in area):
                    raise TypeError("'area' coordinates must be numeric.")

            north, west, south, east = map(float, area)

            if not (-90 <= south < north <= 90):
                raise ValueError("Latitude boundaries must satisfy -90 <= South < North <= 90.")

            if not (-180 <= west <= 180 and -180 <= east <= 180):
                raise ValueError("Longitude boundaries must be within -180 and 180 degrees.")

            if west == east:
                raise ValueError("West and East boundaries cannot be equal.")

            area = [north, west, south, east]

        # 8. Validate pressure levels
        if pressure_levels is not None:

            pressure_level_all = [
                1000, 975, 950, 925, 900, 875, 850, 825, 800, 775,
                750, 700, 650, 600, 550, 500, 450, 400, 350, 300,
                250, 225, 200, 175, 150, 125, 100, 70, 50, 30,
                20, 10, 7, 5, 3, 2, 1
            ]

            if not isinstance(pressure_levels, (list, tuple)) or not pressure_levels:
                raise ValueError("'pressure_levels' must be a non-empty list or tuple.")

            if any(isinstance(level, bool) for level in pressure_levels):
                raise TypeError("Boolean values are not valid pressure levels.")

            try:
                pressure_levels = [float(level) for level in pressure_levels]
            except (TypeError, ValueError):
                raise ValueError("Pressure levels must contain numeric values (str, int or float).") from None

            if not all(math.isfinite(level) and level.is_integer() for level in pressure_levels):
                raise ValueError("Pressure levels must be finite integer values in hPa.")

            pressure_levels = [int(level) for level in pressure_levels]

            # Check unavailable levels
            if not isinstance(adjust_pressure_levels, bool):
                raise TypeError("'adjust_pressure_levels' must be a bool.")

            unavailable_levels = [
                level for level in pressure_levels
                if level not in pressure_level_all
            ]

            if unavailable_levels:

                suggestions = {
                    level: min(
                        pressure_level_all,
                        key=lambda x: abs(x - level)
                    )
                    for level in unavailable_levels
                }

                suggestion_text = ", ".join(f"{level} → {nearest}" for level, nearest in suggestions.items())

                if not adjust_pressure_levels:
                    raise ValueError(
                        f"Unavailable pressure levels: {unavailable_levels}. "
                        f"Nearest available levels: {suggestion_text}. "
                        "Set adjust_pressure_levels=True to replace them."
                    )

                if logging:
                    logger.warning("Unavailable pressure levels will be replaced: %s",
                                   suggestion_text)

                pressure_levels = [suggestions.get(level, level) for level in pressure_levels]

            # Remove duplicates and sort
            pressure_levels = sorted(set(pressure_levels), reverse=True)

            if logging:
                logger.info("Selected pressure levels (hPa): %s",pressure_levels)

        # 9. Validate grid resolution
        if grid_resolution is not None:

            if logging:
                logger.info(
                    "The ERA5 reanalysis atmospheric data resolution is 0.25° and"
                    " the ERA5 ensemble atmospheric data resolution is 0.5°."
                    " The ERA5 wave data resolution is 0.5° and the ERA5 ensemble wave data resolution is 1.0°."
                    " The ERA5-Land data resolution is on 0.1°." 
                    " Output grid spacing can be changed using 'grid_resolution'.\n"
                    " Grid resolution input formats:\n"
                    "  1. List or tuple: [dLon, dLat], e.g. [0.25, 0.25].\n"
                    "  2. Slash-separated string: 'dLon/dLat', e.g. '0.25/0.25'.\n"
                    "  Values must be positive finite numbers in degrees."
                    " Note: Values < 0.25° will not add real physical details, "
                    "instead interpolation will be done on the server."
                )

            # Parse string input
            if isinstance(grid_resolution, str):
                try:
                    grid_resolution = [float(value.strip()) for value in grid_resolution.split("/")]
                except ValueError:
                    raise ValueError("'grid_resolution' must have format 'dLon/dLat', e.g. '0.25/0.25'.") from None

            # Validate structure
            if not isinstance(grid_resolution, (list, tuple)) or len(grid_resolution) != 2:
                raise ValueError("'grid_resolution' must be a list/tuple [dLon, dLat] or a string 'dLon/dLat'.")

            # Validate values
            if not all(
                    isinstance(x, Real)
                    and not isinstance(x, bool)
                    and math.isfinite(x)
                    and x > 0
                    for x in grid_resolution
            ):
                raise ValueError(
                    "Grid resolution values must be positive finite numbers."
                )

            grid_resolution = [float(x) for x in grid_resolution]

            if logging:
                logger.info("Selected grid resolution: dLon = %.4f°, dLat = %.4f°",
                            grid_resolution[0], grid_resolution[1])

        # 10. Validate daily statistics
        if mode == "daily":

            if logging:
                logger.info("The data are available from the Climate Data Store (CDS) webforms: \n"
                        " Derived ERA5 daily statistics on single levels from 1940 to present.\n"
                        " Derived ERA5 daily statistics on pressure levels from 1940 to present \n"
                        " Derived ERA5-Land daily statistics from 1950 to present.")
                logger.info("Users can select to calculate daily statistics from 1 hour, 3 hours and 6 hours data. ")

            valid_statistics = { "mean", "maximum", "minimum", "sum"}

            valid_frequencies = {"1_hourly", "3_hourly", "6_hourly"}

            valid_time_zones = {
                f"utc{sign}{hour:02d}:00"
                for sign, hours in [("-", range(1, 13)), ("+", range(0, 15))]
                for hour in hours
            }

            if daily_statistic is None:
                daily_statistic = "mean"

            if not isinstance(daily_statistic, str):
                raise TypeError("'daily_statistic' must be a string or None")

            daily_statistic = daily_statistic.strip().lower()

            if daily_statistic not in valid_statistics:
                raise ValueError(f"'daily_statistic' must be one of: "
                                 f"{', '.join(sorted(valid_statistics))}")

            # Validate daily sum
            if daily_statistic == "sum":

                if pressure_levels is not None:
                    raise ValueError(
                        "'daily_sum' is available only for single-level data, "
                        "not pressure-level data."
                    )

                variable_info = database.loc[
                    (database["cds_variable"] == variable)
                    & (database["level_type"] == "single_levels")
                    ]

                if not variable_info["parameter_type"].isin(["accumulations"]).any():
                    raise ValueError(
                        f"'daily_sum' is not available for variable '{variable}'. "
                        "Only supported accumulated single-level variables can be used."
                    )

            daily_statistic = f"daily_{daily_statistic}"

            if logging:
                logger.info("Selected daily statistic: %s", daily_statistic)

            # Validate frequency
            if not isinstance(frequency, str):
                raise TypeError("'frequency' must be a string")

            frequency = frequency.strip().lower()

            if frequency not in valid_frequencies:
                raise ValueError(f"'frequency' must be one of: {', '.join(sorted(valid_frequencies))}")

            if logging:
                logger.info("Selected sampling frequency: %s", frequency)

            # Validate time zone
            if not isinstance(time_zone, str):
                raise TypeError("'time_zone' must be a string")

            time_zone = time_zone.strip().lower()

            if time_zone not in valid_time_zones:
                raise ValueError("'time_zone' must be between UTC-12:00 and UTC+14:00. "
                                "Example: 'utc+00:00', 'utc+01:00', 'utc-05:00'.")

            if logging:
                logger.info("Selected time zone: %s",time_zone.upper())

        else:
            if daily_statistic is not None:
                raise ValueError("'daily_statistic' can only be specified when mode='daily'.")

        # 11. Select dataset
        is_pressure = pressure_levels is not None

        if mode == "hourly":
            dataset = (
                "reanalysis-era5-pressure-levels"
                if is_pressure
                else "reanalysis-era5-single-levels"
            )

        elif mode == "daily":
            dataset = (
                "derived-era5-pressure-levels-daily-statistics"
                if is_pressure
                else "derived-era5-single-levels-daily-statistics"
            )

        else:  # monthly
            dataset = (
                "reanalysis-era5-pressure-levels-monthly-means"
                if is_pressure
                else "reanalysis-era5-single-levels-monthly-means"
            )
            if logging:
                logger.info("Monthly averaged reanalysis and Monthly averaged ensemble members data "
                        "are produced by averaging all daily data. Monthly averages by hour of day "
                        "constitute the average over all data within the calendar month for every hour (UTC) "
                        "of the day in case of reanalysis or every third hour (UTC) of the day for ensemble members.")


        # 12. Define output file
        request_date = (
            current_date.strftime("%Y-%m")
            if mode == "monthly"
            else current_date.strftime("%Y-%m-%d")
        )
        # Define request configuration for unique filename
        request_config = {
            "variable": variable,
            "mode": mode,
            "date": request_date,
            "pressure_levels": pressure_levels,
            "times": sorted(times) if times is not None else None,
            "area": area,
            "grid_resolution": grid_resolution,
            "file_format": file_format,
            "download_format": (
                "unarchived" if mode == "daily" and file_format == "grib"
                else "zip" if mode == "daily" and file_format == "netcdf"
                else None
            ),
        }

        if mode == "daily":
            request_config.update({
                "daily_statistic": daily_statistic,
                "frequency": frequency,
                "time_zone": time_zone,
            })

        # Generate short hash
        config_string = json.dumps(
            request_config,
            sort_keys=True,
            separators=(",", ":")
        )

        request_hash = hashlib.sha256(config_string.encode("utf-8")).hexdigest()


        # Check whether an identical request already exists
        request_db = ERA5RequestDatabase(db_path=DATABASE_PATH)

        existing_request = request_db.get_request_by_hash(request_hash)

        if existing_request is not None:

            if existing_request["status"] not in {"failed", "deleted"}:

                existing_request["existing"] = True

                if logging:
                    logger.info(
                        f"Request already exists: {existing_request['request_id']} "
                        f"(status: {existing_request['status']}). "
                        "No new request submitted."
                    )

                return existing_request

        level_suffix = "_pressure" if is_pressure else "_single"

        if mode == "hourly":
            date_suffix = f"{year}-{month}-{day}"
            mode_suffix = "hourly"

        elif mode == "daily":
            date_suffix = f"{year}-{month}-{day}"
            mode_suffix = f"daily_{daily_statistic}"

        else:  # monthly
            date_suffix = f"{year}-{month}"
            mode_suffix = "monthly"

        # Determine file extension
        if mode == "daily":
            extension = ".grib" if file_format == "grib" else ".zip"
        else:
            extension = ".grib" if file_format == "grib" else ".nc"

        filename = (
            f"{variable}{level_suffix}_"
            f"{mode_suffix}_"
            f"{date_suffix}_"
            f"{request_hash[:8]}"
            f"{extension}"
        )

        output_file = os.path.join(output_dir, filename)

        # 13. Check existing file
        if os.path.exists(output_file):
            print(f"File already exists: {output_file}")

            return {
                "request_id": None,
                "dataset": dataset,
                "request": None,
                "output_file": output_file,
                "status": "already_downloaded",
                "created_at": None,
                "downloaded": True,
                "request_hash": request_hash,
                "existing": True,
            }

        os.makedirs(output_dir, exist_ok=True)

        # 14. Build request
        request_params: dict[str, Any] = {
            "variable": [variable],
            "year": [year],
            "month": [month],
        }

        if area is not None:
            request_params["area"] = list(area)

        if grid_resolution is not None:
            request_params["grid"] = list(grid_resolution)

        if mode == "hourly":

            request_params.update({
                "product_type": ["reanalysis"],
                "day": [day],
                "time": (
                    list(times)
                    if times is not None
                    else [f"{hour:02d}:00" for hour in range(24)]
                ),
                "data_format": file_format
            })

        elif mode == "daily":

            request_params.update({
                "product_type": ["reanalysis"],
                "day": [day],
                "daily_statistic": daily_statistic,
                "time_zone": time_zone,
                "frequency": frequency,
                "data_format": file_format,
                "download_format": (
                    "unarchived" if file_format == "grib" else "zip"
                ),
            })

            if pressure_levels is not None:
                request_params["pressure_level"] = pressure_levels

        else:  # monthly

            request_params.update({
                "product_type": ["monthly_averaged_reanalysis"],
                "data_format": file_format
            })

        if mode == "hourly" and pressure_levels is not None:
            request_params["pressure_level"] = pressure_levels

        if mode == "monthly" and pressure_levels is not None:
            request_params["pressure_level"] = pressure_levels

        # Submit a new request
        remote = None

        try:
            print(f"Submitting ERA5 {mode} data: {output_file}")

            client = Client()
            remote = client.submit(dataset, request_params)

        except Exception as e:
            if logging:
                logger.error("Request submission failed: %s", e)
            return None

        request_info = {
            "request_id": remote.request_id,
            "dataset": dataset,
            "request": request_params,
            "output_file": output_file,
            "status": remote.status,
            "created_at": str(remote.created_at),
            "downloaded": False,
            "request_hash": request_hash,
            "existing": False,
        }

        try:
            request_db.add_request(request_info)
        except Exception as e:
            if logging:
                logger.error(
                    "Request was submitted, but database operation failed. "
                    "Request ID: %s. Error: %s",
                    remote.request_id,
                    e,
                )
            raise

        if logging:
            logger.info("Request submitted successfully.")
            logger.info("Request ID: %s", request_info["request_id"])
            logger.info("Status: %s", request_info["status"])

        return request_info


def submit_era5_data_for_period(
        output_dir,
        variable,
        date_from,
        date_to,
        mode="hourly",
        daily_statistic=None,
        frequency="1_hourly",
        time_zone="utc+00:00",
        times=None,
        pressure_levels=None,
        adjust_pressure_levels=False,
        area=None,
        grid_resolution=None,
        file_format="grib",
        logging=True,
    ):
        """
        Submit ERA5 data for a specified period.

        The function generates a sequence of dates based on the selected
        mode and submits one file for each date or month using
        submit_era5_data().

        Downloads are performed sequentially.

        Parameters
        ----------
        output_dir : str or os.PathLike
            Directory where downloaded files will be saved.

        variable : str
            ERA5 variable to download (e.g., "2m_temperature").

        date_from : str
            Start date in "DD-MM-YYYY" format.

        date_to : str
            End date in "DD-MM-YYYY" format.

        mode : str, default "hourly"
            Temporal processing mode:
            - "hourly": hourly ERA5 data, one file per day.
            - "daily": daily statistics, one file per day.
            - "monthly": monthly averaged data, one file per month.

        daily_statistic : str, optional
            Daily statistic to retrieve in daily mode.
            Available options depend on the dataset and variable.
            For pressure-level data, daily mean, maximum and minimum
            are available. Daily sum is available only for supported
            accumulated single-level variables.
            If None, the default daily statistic is used.

        frequency : str, default "1_hourly"
            Sub-daily sampling frequency used to calculate daily
            statistics. Used only in daily mode.

        time_zone : str, default "utc+00:00"
            Time zone used for daily aggregation.
            Used only in daily mode.

        times : list of str, optional
            Requested hours in "HH:MM" format.
            Used only in hourly mode. If None, all 24 hourly time steps
            are requested.

        pressure_levels : list of str or int, optional
            Pressure levels in hPa.
            If None, single-level data are requested.

        adjust_pressure_levels : bool, default False
            Controls how unavailable pressure levels are handled.

            - False: Raise a ValueError if one or more requested pressure
              levels are unavailable. The error message includes the nearest
              available pressure levels as suggestions.
            - True: Automatically replace unavailable pressure levels with
              the nearest available levels.

            Duplicate levels resulting from automatic replacement are removed,
            and the final list is sorted in descending order.
            Used only when pressure_levels is not None.

        area : list of float, optional
            Geographic bounding box in the format
            [North, West, South, East].

        grid_resolution : list of float or str, optional
            Output grid resolution in [dLon, dLat] format.
            Can also be provided as a slash-separated string, e.g. "0.25/0.25".
            If None, the dataset default resolution is used.

        file_format : str, default "grib"
            Output data format: "netcdf" or "grib".
            For daily statistics:
            - GRIB data are downloaded unarchived.
            - NetCDF data are downloaded as ZIP archives.

        logging : bool, default=True
            Enable logging.

        Returns
        -------
        list of str
            Paths to successfully downloaded files, ordered
            chronologically.
        """
        logger = get_logger("download_era5_data_for_period")

        request_infos = {}

        valid_modes = {"hourly", "daily", "monthly"}

        if mode not in valid_modes:
            raise ValueError(f"'mode' must be one of {valid_modes}")

        # Generate dates based on the selected mode

        # Parse dates
        try:
            start_date = datetime.strptime(date_from, "%d-%m-%Y")
            end_date = datetime.strptime(date_to, "%d-%m-%Y")

        except (TypeError, ValueError):
            raise ValueError("'date_from' and 'date_to' must have format 'DD-MM-YYYY'")

        # Validate date range
        if start_date > end_date:
            raise ValueError("'date_from' must not be later than 'date_to'")

        # Generate dates
        if mode in {"hourly", "daily"}:

            dates = pd.date_range(
                start=start_date,
                end=end_date,
                freq="D"
            )

        elif mode == "monthly":

            dates = pd.date_range(
                start=start_date.replace(day=1),
                end=end_date.replace(day=1),
                freq="MS"
            )

        for i, dd in enumerate(dates):

            try:
                request_info = submit_era5_data(
                    output_dir=output_dir,
                    variable=variable,
                    current_date=dd.strftime("%d-%m-%Y"),
                    times=times,
                    mode=mode,
                    daily_statistic=daily_statistic,
                    frequency=frequency,
                    time_zone=time_zone,
                    area=area,
                    grid_resolution=grid_resolution,
                    pressure_levels=pressure_levels,
                    adjust_pressure_levels=adjust_pressure_levels,
                    file_format=file_format,
                    logging=logging if i==0 else False,
                )

                if logging and i != 0 and request_info is not None:

                    if request_info.get("existing", False):
                        logger.info("Existing request reused. No new submission.")
                    else:
                        logger.info("New request submitted successfully.")

                    logger.info("Request ID: %s", request_info["request_id"])
                    logger.info("Status: %s", request_info["status"])

                if request_info:
                    request_infos[dd] = request_info

            except Exception as e:
                logger.error(f"Submitng failed for {dd.strftime('%Y-%m-%d')}: {e}")

        return request_infos

def check_era5_status(request_id, request_db):

    client = Client(cleanup=False)

    remote = client.get_remote(request_id)

    request_db.update_request(
        request_id,
        status=remote.status,
        started_at=(
            str(remote.started_at)
            if remote.started_at else None
        ),
        finished_at=(
            str(remote.finished_at)
            if remote.finished_at else None
        )
    )

    return request_db.get_request(request_id)

def download_era5_results(request_db, logging=True):
    """Download all completed ERA5 requests stored in the request database."""

    logger = get_logger("download_era5_results")

    client = Client(cleanup=False)

    requests = request_db.list_requests()

    downloaded_results = []

    for request_info in requests:

        request_id = request_info.get("request_id")
        output_file = request_info.get("output_file")

        # Skip requests that have already been downloaded
        if request_info.get("downloaded", False):
            continue

        if not request_id or not output_file:
            continue

        try:
            # Check the current status on CDS
            remote = client.get_remote(request_id)

            # Update the current request status in the database
            request_db.update_request(
                request_id,
                status=remote.status
            )

            # Download only completed requests
            if remote.status != "successful" or not remote.results_ready:

                if logging:
                    logger.info(
                        "Request %s is not ready. Current status: %s",
                        request_id,
                        remote.status
                    )

                continue

            output_file = os.fspath(output_file)

            os.makedirs(
                os.path.dirname(output_file) or ".",
                exist_ok=True
            )

            # Download the result
            result = remote.download(output_file)

            # Update database after successful download
            request_db.update_request(
                request_id,
                downloaded=True,
                downloaded_at=datetime.now().isoformat()
            )

            downloaded_results.append({
                "request_id": request_id,
                "output_file": output_file,
                "result": result,
                "status": "downloaded"
            })

            if logging:
                logger.info(
                    "Request %s downloaded: %s",
                    request_id,
                    output_file
                )

        except Exception as e:

            if logging:
                logger.error(
                    "Download failed for request %s: %s",
                    request_id,
                    e
                )

            # Remove incomplete output file
            if os.path.exists(output_file):
                os.remove(output_file)

            request_db.update_request(
                request_id,
                error=str(e)
            )

            downloaded_results.append({
                "request_id": request_id,
                "output_file": output_file,
                "status": "failed",
                "error": str(e)
            })

    if logging:
        logger.info(
            "Download process completed. Downloaded %d of %d requests.",
            sum(r["status"] == "downloaded" for r in downloaded_results),
            len(requests)
        )
    return downloaded_results