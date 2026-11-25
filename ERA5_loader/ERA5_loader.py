from ecmwf.datastores import Client

import pandas as pd
import os
from numbers import Real
from typing import Any
import logging
import sys
from pathlib import Path
import re
import math
import hashlib
import tempfile
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, date, timedelta
import calendar

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

def load_era5_database() -> pd.DataFrame:
    """
    Load the ERA5 parameter database from a CSV file.

    Returns
    -------
    pd.DataFrame
        Database containing ERA5 variable metadata.

    Raises
    ------
    FileNotFoundError
        If the parameter database file does not exist.
    ValueError
        If required columns are missing from the database.
    """
    if not ERA5_PATH.is_file():
        raise FileNotFoundError(f"ERA5 parameter database not found: {ERA5_PATH}")

    database = pd.read_csv(ERA5_PATH, sep=";", encoding="utf-8-sig")

    required_columns = {
        "name",
        "units",
        "cds_variable",
        "short_name",
        "level_type",
        "parameter_type"
    }

    missing_columns = required_columns.difference(database.columns)

    if missing_columns:
        raise ValueError(
            f"ERA5 parameter database is missing required columns: {sorted(missing_columns)}"
        )

    return database

def search_era5_variables(
        keyword: str,
        level_type: str | None = None,
        parameter_type: str | None = None
    ) -> pd.DataFrame:
    """
    Search the ERA5 parameter database by variable name or metadata.

    Parameters
    ----------
    keyword : str
        Search keyword. Matches variable name, CDS variable or short name.
    level_type : str, optional
        Filter by vertical level type (e.g. 'single_levels',
        'pressure_levels').
    parameter_type : str, optional
        Filter by parameter type (e.g. 'dynamics', 'thermodynamics',
        'accumulations').

    Returns
    -------
    pd.DataFrame
        Matching ERA5 variables and their metadata.

    Raises
    ------
    TypeError
        If keyword or an optional filter is not a string.
    ValueError
        If a search argument is empty or no matching variables are found.
    """

    # Validate search arguments
    if not isinstance(keyword, str):
        raise TypeError("'keyword' must be a string.")

    keyword = keyword.strip()

    if not keyword:
        raise ValueError("'keyword' must not be empty.")

    for name, value in [
        ("level_type", level_type),
        ("parameter_type", parameter_type)
    ]:
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"'{name}' must be a string or None.")

            if not value.strip():
                raise ValueError(f"'{name}' must not be empty.")

    if level_type is not None:
        level_type = level_type.strip()

    if parameter_type is not None:
        parameter_type = parameter_type.strip()

    # Load parameter database
    database = load_era5_database()

    # Search variable metadata
    search_columns = ["name", "cds_variable", "short_name"]

    mask = pd.Series(False, index=database.index)

    for column in search_columns:
        mask |= database[column].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False
        )

    result = database[mask].copy()

    # Apply optional filters
    if level_type is not None:
        result = result[
            result["level_type"].str.contains(
                level_type,
                case=False,
                na=False,
                regex=False
            )
        ]

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
            f"with level_type={level_type} and "
            f"parameter_type={parameter_type}."
        )

    # Display matching variables
    print(
        f"Matching ERA5 variables for '{keyword}' "
        f"(level_type={level_type}, parameter_type={parameter_type}):"
    )

    output = result.reset_index(drop=True)[
        ["name", "units", "cds_variable", "level_type", "parameter_type"]
    ].to_string(index=False, max_colwidth=40)

    separator = "-" * max(len(line) for line in output.splitlines())

    print(separator)
    print(output)
    print(separator)

    print("Note: `cds_variable` is used in CDS API download requests.\n")

    return result.reset_index(drop=True)

DATABASE_PATH = Path(__file__).parent / "ERA5_requests.db"

class ERA5RequestDatabase:
    """
    Manage ERA5 request records stored in an SQLite database.

    The database tracks submitted CDS requests, their processing
    status, download information and request configuration hashes.
    """

    def __init__(self, db_path=DATABASE_PATH):

        self.db_path = Path(db_path)

        self._create_table()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)

        try:
            yield conn
            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()


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

        unknown_fields = set(kwargs) - allowed_fields

        if unknown_fields:
            raise ValueError(
                f"Unsupported fields for request update: {sorted(unknown_fields)}"
            )

        updates = kwargs.copy()

        if not updates:
            return

        if "downloaded" in updates:
            if not isinstance(updates["downloaded"], bool):
                raise TypeError("'downloaded' must be a bool.")

            updates["downloaded"] = int(updates["downloaded"])

        columns = ", ".join(f"{key} = ?" for key in updates)

        values = list(updates.values())
        values.append(request_id)

        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE requests SET {columns} WHERE request_id = ?",
                values
            )

            if cursor.rowcount == 0:
                raise KeyError(f"No ERA5 request found with ID: {request_id}")

    def get_request_by_hash(self, request_hash):
        """Retrieve a request using its configuration hash."""

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                     SELECT *
                FROM requests
                WHERE request_hash = ?
                AND COALESCE(status, '') NOT IN ('failed', 'rejected', 'deleted', 'expired')
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

PRESSURE_LEVELS_ALL = [
    1000, 975, 950, 925, 900, 875, 850, 825, 800, 775,
    750, 700, 650, 600, 550, 500, 450, 400, 350, 300,
    250, 225, 200, 175, 150, 125, 100, 70, 50, 30,
    20, 10, 7, 5, 3, 2, 1
] # All available pressure levels in hPa

def _normalize_date(value, name, allow_none=False):
    """Convert a date input to a datetime object."""

    if value is None:
        if allow_none:
            return None
        raise ValueError(f"'{name}' must not be None.")

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%d-%m-%Y")
        except ValueError:
            raise ValueError(f"'{name}' must have format 'DD-MM-YYYY'.") from None

    raise TypeError(
        f"'{name}' must be a datetime, date, or string in 'DD-MM-YYYY' format."
    )

def _build_output_filename(
    request_config,
    request_hash,
):
    """Generate an output filename for an ERA5 request batch."""

    variable = request_config["variable"][0]
    pressure_levels = request_config["pressure_levels"]
    mode = request_config["mode"]
    batch_start = request_config["start_date"]
    batch_end = request_config["end_date"]
    if mode == "daily":
        daily_statistic = request_config["daily_statistic"]

    # Determine vertical level suffix
    level_suffix = "_pressure" if pressure_levels is not None else "_single"

    # Determine mode suffix and date format
    if mode == "hourly":
        mode_suffix = "hourly"
        date_format = "%Y%m%d"

    elif mode == "daily":
        mode_suffix = (
            daily_statistic
            if daily_statistic.startswith("daily_")
            else f"daily_{daily_statistic}"
        )
        date_format = "%Y%m%d"

    elif mode == "monthly":
        mode_suffix = "monthly"
        date_format = "%Y%m"

    else:
        raise ValueError(f"Unsupported mode: {mode}")

    # Define period suffix
    start_label = batch_start.strftime(date_format)
    end_label = batch_end.strftime(date_format)

    period_suffix = (
        start_label
        if start_label == end_label
        else f"{start_label}-{end_label}"
    )

    # Determine file extension
    if mode == "daily":
        extension = ".zip"
    elif request_config["file_format"] == "netcdf":
        extension = ".nc"
    else:
        extension = ".grib"

    # Generate filename
    filename = (
        f"{variable}{level_suffix}_"
        f"{mode_suffix}_"
        f"{period_suffix}_"
        f"{request_hash[:8]}"
        f"{extension}"
    )

    return filename


def _generate_request_batches(
        request_config,
        max_fields_per_batch=50000,
        max_uncompressed_mb_per_batch=30000,
        logging_on=False,
):
    """
    Generate calendar-aware ERA5 request batches based on temporal,
    spatial, and memory constraints.

    Requests are split into calendar-aware batches to limit the estimated
    processing workload and uncompressed output size.

    For Daily Statistics, request workload units account for the selected
    sub-daily frequency (1-, 3-, or 6-hourly). Memory estimates, however,
    are based on the actual daily output fields (one field per day,
    pressure level, and variable).

    RAM estimates represent the theoretical size of uncompressed float32
    arrays. They do not include additional memory overhead from data
    decoding, temporary arrays, or intermediate processing operations.

    Spatial grid-point counts, particularly for cropped areas, are
    approximate and depend on grid alignment and coordinate conventions.

    The function returns batch specifications and estimated memory
    requirements. Actual CDS processing workload and peak memory usage
    may differ from these estimates.

    Parameters
    ----------
    request_config : dict
        ERA5 request configuration. Expected to contain the temporal range,
        data mode, variables, pressure levels, grid resolution, and other
        settings required to estimate the size of each batch.

    max_fields_per_batch : int, default=50000
        Maximum number of workload units allowed in a batch.
        For hourly and monthly modes, one workload unit corresponds
        to one output field.
        For Daily Statistics, workload units account for the
        sub-daily frequency used to calculate daily statistics:
            - 1_hourly: 24 workload units per output field.
            - 3_hourly: 8 workload units per output field.
            - 6_hourly: 4 workload units per output field.

    max_uncompressed_mb_per_batch : int or float, default=30000
        Maximum estimated uncompressed batch size, in decimal megabytes (MB).
        The estimate is based on the number of grid points and assumes
        4 bytes per value. It does not include memory overhead from
        downloading, decoding, or processing the data.

    logging_on : bool, default=False
        If True, log information about the generated batches and their
        estimated sizes.

    Returns
    -------
    list of dict
        Batch specifications. Each dictionary contains the temporal
        parameters needed to build an individual ERA5 request.
    """
    logger = get_logger("generate_request_batches")


    start_date = request_config["start_date"]
    end_date = request_config["end_date"]

    if isinstance(start_date, datetime):
        start_date = start_date.date()

    if isinstance(end_date, datetime):
        end_date = end_date.date()

    mode = request_config["mode"]
    grid_resolution = request_config["grid_resolution"]
    variables = request_config["variable"]
    pressure_levels = request_config["pressure_levels"]
    times = request_config["times"]
    area = request_config["area"]

    # 1. Validate input parameters
    if grid_resolution is None:
        grid_lon = grid_lat = 0.25
    else:
        grid_lon, grid_lat = grid_resolution

    if isinstance(variables, str):
        num_vars = 1
    elif isinstance(variables, (list, tuple)):
        num_vars = len(variables)
    else:
        num_vars = int(variables)

    if num_vars < 1:
        raise ValueError("At least one variable is required")

    # 2. Determine temporal steps
    if mode == "daily":
        frequency = request_config["frequency"]
        freq_steps = {"1_hourly": 24, "3_hourly": 8, "6_hourly": 4}[frequency]
        times_steps = 1
    else:
        freq_steps = 1
        times_steps = (
            len(times)
            if times is not None
            else (24 if mode == "hourly" else 1)
        )

    pressure_steps = len(pressure_levels) if pressure_levels is not None else 1
    day_steps = (end_date - start_date).days + 1
    month_steps = (
            (end_date.year - start_date.year) * 12
            + end_date.month - start_date.month + 1
    )

    # 3. Calculate workload units vs. actual output fields
    if mode == "hourly":
        total_output_fields = day_steps * times_steps * pressure_steps * num_vars
        total_units = total_output_fields
    elif mode == "daily":
        total_output_fields = day_steps * pressure_steps * num_vars
        total_units = total_output_fields * freq_steps
    else:
        total_output_fields = month_steps * times_steps * pressure_steps * num_vars
        total_units = total_output_fields

    # 4. Calculate spatial grid size (approximate when area is cropped)
    if area is None:
        lat_steps = round(180 / grid_lat) + 1
        lon_steps = round(360 / grid_lon)
    else:
        north, west, south, east = area
        if north < south:
            raise ValueError("Area north must be >= south")

        lat_steps = round((north - south) / grid_lat) + 1
        lon_span = (east - west) % 360 if east < west else east - west
        lon_steps = round(lon_span / grid_lon) + 1

    grid_points = lat_steps * lon_steps
    matrix_size_mb = grid_points * 4 / (1000 ** 2)

    # 5. Estimate uncompressed RAM size (float32)
    total_ram_mib = matrix_size_mb * total_output_fields

    # 6. Calculate effective batch limit
    max_output_by_memory = math.floor(max_uncompressed_mb_per_batch / matrix_size_mb)
    if max_output_by_memory < 1:
        raise ValueError("A single float32 matrix exceeds the memory limit.")

    max_units_by_memory = max_output_by_memory * freq_steps
    effective_max_units = min(max_fields_per_batch, max_units_by_memory)

    # 7. Generate calendar-aware batches
    batches = []

    if mode == "monthly":
        units_per_month = num_vars * times_steps * pressure_steps

        if units_per_month > effective_max_units:
            raise ValueError("A single monthly request exceeds the batch limit. "
                             "Split variables, times or pressure levels.")

        units_per_year = units_per_month * 12
        is_full_years = (start_date.month == 1 and end_date.month == 12)

        if is_full_years and units_per_year <= effective_max_units:
            years_per_batch = max(1, effective_max_units // units_per_year)
            years = list(range(start_date.year, end_date.year + 1))
            all_months = [f"{m:02d}" for m in range(1, 13)]

            for i in range(0, len(years), years_per_batch):
                chunk_years = years[i: i + years_per_batch]
                n_units = len(chunk_years) * units_per_year

                batches.append({
                    "year": [str(y) for y in chunk_years],
                    "month": all_months,
                    "units": n_units,
                    "output_fields": n_units,
                })
        else:
            months_per_batch = min(12, effective_max_units // units_per_month)

            for year in range(start_date.year, end_date.year + 1):
                month_start = start_date.month if year == start_date.year else 1
                month_end = end_date.month if year == end_date.year else 12
                year_months = [f"{m:02d}" for m in range(month_start, month_end + 1)]

                for i in range(0, len(year_months), months_per_batch):
                    chunk_months = year_months[i: i + months_per_batch]
                    n_units = len(chunk_months) * units_per_month

                    batches.append({
                        "year": [str(year)],
                        "month": chunk_months,
                        "units": n_units,
                        "output_fields": n_units,
                    })

    else:
        # Hourly and Daily: strictly split within each calendar month
        # to avoid invalid date combinations like Feb 30 or Apr 31.
        output_per_day = num_vars * times_steps * pressure_steps
        units_per_day = output_per_day * freq_steps

        if units_per_day > effective_max_units:
            raise ValueError("A single day exceeds the batch limit. "
                             "Split variables or pressure levels.")

        days_per_batch = min(31, effective_max_units // units_per_day)
        current_month = date(start_date.year, start_date.month, 1)

        while current_month <= end_date:
            next_month = date(
                current_month.year + (current_month.month == 12),
                (current_month.month % 12) + 1,
                1,
            )
            last_day = next_month - timedelta(days=1)

            d_start = max(start_date, current_month)
            d_end = min(end_date, last_day)
            month_days = [f"{d:02d}" for d in range(d_start.day, d_end.day + 1)]

            for i in range(0, len(month_days), days_per_batch):
                chunk_days = month_days[i: i + days_per_batch]
                n_days = len(chunk_days)

                batches.append({
                    "year": [str(current_month.year)],
                    "month": [f"{current_month.month:02d}"],
                    "day": chunk_days,
                    "units": n_days * units_per_day,
                    "output_fields": n_days * output_per_day,
                })

            current_month = next_month

    # 8. Estimate each batch size (empirical approximations)
    for batch in batches:
        batch_ram_mib = batch["output_fields"] * matrix_size_mb
        batch["est_ram_mb"] = round(batch_ram_mib, 2)

    # 9. Summary & Sanity Check
    actual_units = sum(b["units"] for b in batches)
    actual_output_fields = sum(b["output_fields"] for b in batches)
    assert actual_output_fields == total_output_fields, (f"Output field mismatch: "
                                                         f"{actual_output_fields} != {total_output_fields}")

    assert actual_units == total_units, f"Batch unit mismatch: {actual_units} != {total_units}"

    num_batches = len(batches)
    max_batch_ram = max(b["est_ram_mb"] for b in batches)

    def _format_size_mb(size_mb: float) -> str:
        if size_mb < 1:
            return f"{size_mb * 1000:.2f} KB"
        if size_mb < 1000:
            return f"{size_mb:.2f} MB"
        return f"{size_mb / 1000:.2f} GB"

    if logging_on:
        logger.info(
            f"Total output fields: {actual_output_fields:,}\n"
            f"Number of batches: {num_batches}\n"
            f"Effective batch limit (units): {effective_max_units:,}\n"
            f"Estimated total RAM (float32): {_format_size_mb(total_ram_mib)}\n"
            f"Maximum batch RAM (float32): {_format_size_mb(max_batch_ram)}\n"
            f"Note: Estimates reflect uncompressed float32 arrays in memory; "
            f"actual file size on disk depends on variable, encoding, and compression."
        )
        logger.warning(
            "\n⚠️: Memory usage estimates are theoretical.\n"
            "They represent uncompressed float32 arrays only and do not "
            "include additional processing overhead.\n"
            "Actual RAM usage may be higher due to data decoding, "
            "temporary arrays and intermediate operations.\n"
            "The maximum batch size is an estimate, not a guarantee "
            "of actual peak memory usage.\n"
        )


    return batches


def _build_request_parameters(
                request_config,
                batch
            ):
    """
    Build CDS API request parameters for a single ERA5 batch.

    Combines the ERA5 request configuration with the temporal parameters
    of a batch generated by `generate_request_batches()`.

    The function selects the appropriate CDS product type and constructs
    the request parameters for Hourly, Daily Statistics, or Monthly data.
    It also creates a copy of the request configuration with the start
    and end dates corresponding to the batch.

    For Monthly data, the standard monthly-averaged product is used when
    `times` is None or contains only "00:00". Otherwise, the
    monthly-averaged-by-hour-of-day product is selected.

    Parameters
    ----------
    request_config : dict
        ERA5 request configuration. Expected keys include `variable`,
        `area`, `grid_resolution`, `mode`, `times`, `file_format`,
        and `pressure_levels`. Daily Statistics additionally requires
        `daily_statistic`, `frequency`, and `time_zone`.

    batch : dict
        A single batch specification returned by
        `generate_request_batches()`. Expected keys include `year`,
        `month`, and, for Hourly and Daily batches, `day`.

    Returns
    -------
    tuple[dict, dict]
        A tuple containing:

        - A copy of `request_config` with `start_date` and `end_date`
          set to the temporal boundaries of the batch.
        - A dictionary of CDS API request parameters.

    Notes
    -----
    Monthly batch dates span the first day of the first month through
    the last day of the last month in the batch.

    Hourly and Daily batch dates are determined by the first and last
    days listed in the batch.

    The input `request_config` is not modified.
    """
    years = batch["year"]
    months = batch["month"]

    if "day" in batch:
        days = batch["day"]
    else:
        days = ["01"]

    variable = request_config["variable"]
    area = request_config["area"]
    mode = request_config["mode"]
    times = request_config["times"]
    file_format = request_config["file_format"]
    pressure_levels = request_config["pressure_levels"]

    request_params: dict[str, Any] = {
        "variable": variable,
        # The daily-statistics CDS schema accepts a single year string;
        # hourly and monthly schemas accept a list of years.
        "year": years[0] if mode == "daily" else years,
        "month": months,
    }
    if area is not None:
        request_params["area"] = area

    if mode == "hourly":

        request_params.update({
            "product_type": ["reanalysis"],
            "day": days,
            "time": (times
                if times is not None
                else [f"{hour:02d}:00" for hour in range(24)]
            ),
            "data_format": file_format,
            "download_format": "unarchived",
        })

    elif mode == "daily":

        daily_statistic = request_config["daily_statistic"]
        frequency = request_config["frequency"]
        time_zone = request_config["time_zone"]

        request_params.update({
            # Daily-statistics schema defines product_type as a string.
            "product_type": "reanalysis",
            "day": days,
            "daily_statistic": daily_statistic,
            "time_zone": time_zone,
            "frequency": frequency,
        })
        # Daily statistics are returned as NetCDF files in a ZIP archive.
        # The current dataset schema does not accept download_format.

        if pressure_levels is not None:
            request_params["pressure_level"] = pressure_levels


    elif mode == "monthly":

        if times is None or list(times) == ["00:00"]:
            request_params.update({
                "product_type": ["monthly_averaged_reanalysis"],
                "data_format": file_format,
                "download_format": "unarchived",
                "time": ["00:00"],
            })
        else:
            request_params.update({
                "product_type": ["monthly_averaged_reanalysis_by_hour_of_day"],
                "data_format": file_format,
                "download_format": "unarchived",
                "time": list(times),
            })

    if mode == "hourly" and pressure_levels is not None:
        request_params["pressure_level"] = pressure_levels

    if mode == "monthly" and pressure_levels is not None:
        request_params["pressure_level"] = pressure_levels

    request_config_per_batch = request_config.copy()

    if mode == "monthly":
        start_date = date( int(years[0]),int(months[0]),1)

        end_date = date(int(years[-1]),int(months[-1]),
                calendar.monthrange(int(years[-1]), int(months[-1]))[1])
    else:
        start_date = date(int(years[0]),int(months[0]),int(days[0]))

        end_date = date(int(years[-1]),int(months[-1]),int(days[-1]))

    request_config_per_batch["start_date"] = start_date
    request_config_per_batch["end_date"] = end_date

    return request_config_per_batch, request_params

def submit_era5_data(
            output_dir,
            variable,
            start_date,
            end_date=None,
            mode="hourly",
            frequency="6_hourly",
            time_zone="utc+00:00",
            times=None,
            daily_statistic=None,
            pressure_levels=None,
            adjust_pressure_levels=False,
            area=None,
            grid_resolution=None,
            file_format=None,
            logging_on=True,
        ):
        """
        Submit one ERA5 data for a specified date or time period.

        Parameters
        ----------
        output_dir : str or os.PathLike
            Directory where the downloaded file will be saved.

        variable : str
            ERA5 variable to download (e.g., "2m_temperature").

        start_date : str
            Start date in "DD-MM-YYYY" format, datetime or date object.

        end_date : str
            End date in "DD-MM-YYYY" format, datetime or date object.

        mode : str, default "hourly"
            Temporal processing mode:
            - "hourly": hourly ERA5 data.
            - "daily": daily statistics derived from hourly data.
            - "monthly": monthly averaged ERA5 data.

        frequency : str, default "6_hourly"
            Sub-daily sampling frequency used to calculate daily
            statistics. Used only in daily mode.

        time_zone : str, default "utc+00:00"
            Time zone used for daily aggregation.
            Used only in daily mode.

        times : list of str, optional
            Requested hours in "HH:MM" format (e.g., ["00:00", "06:00"]).
            Used in hourly mode and in monthly averaged reanalysis by hour of day .
            If None, all 24 hourly time steps
            are requested.

        daily_statistic : str, optional
            Daily statistic to retrieve in daily mode.
            Available options depend on the dataset and variable.
            For pressure-level data, daily mean, maximum and minimum
            are available. Daily sum is available only for supported
            accumulated single-level variables.
            If None, the default daily statistic is used.

        pressure_levels : str, list of str, int or float, optional
            Pressure levels in hPa. Values must be integer levels.
            If None, single-level data are requested.
            If 'all', all available pressure level will be used

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

        grid_resolution : None, optional
            Custom grid resolution is not supported by the current CDS
            Data Stores request schemas used by this function. The native
            dataset resolution is used. Any non-None value raises ValueError.

        file_format : str, optional
            Output data format: "netcdf" or "grib".

            If None:
            - "hourly": defaults to "grib".
            - "daily": defaults to "netcdf".
            - "monthly": defaults to "grib".

            Daily statistics are provided as NetCDF files
            inside ZIP archives.

        logging_on : bool, default=True
            Enable logging.

        Returns
        -------
        list of dict
            Information about each ERA5 request batch processed.
            Each dictionary may contain the following fields:

            - request_id : str or None
                CDS request identifier. None if the request was not submitted
                or the output file already existed.
            - dataset : str
                CDS dataset identifier.
            - request : dict or None
                Parameters used to submit the CDS request.
                None if the output file already existed.
            - output_file : str
                Expected path of the output file.
            - status : str
                CDS request status or local processing status, such as
                "already_downloaded" or "submission_failed".
            - created_at : str or None
                CDS request creation timestamp.
            - downloaded : bool
                Whether the output file is marked as downloaded.
            - request_hash : str
                SHA-256 hash identifying the request configuration.
            - existing : bool
                Whether the request or output file already existed.
            - error : str, optional
                Error description if request submission failed.
        """
        logger = get_logger("download_era5_data")

        # 1. Validate output directory
        if not isinstance(output_dir, (str, os.PathLike)):
            raise TypeError("'output_dir' must be a string or path-like object")

        output_dir = os.fspath(output_dir) or "."

        # 2. Validate variable
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("'variable' must be a non-empty string")

        database_era5 = load_era5_database()

        # 2.1 Select variables according to level type
        if pressure_levels is None:
            expected_level_type = "single_levels"
        else:
            expected_level_type = "pressure_levels"

        valid_variables = database_era5.loc[database_era5["level_type"] ==
                        expected_level_type,"cds_variable"].dropna().unique()

        if variable not in valid_variables:
            raise ValueError(f"Variable '{variable}' is not available for '{expected_level_type}'. "
                             f"Valid variables are: {valid_variables}")

        # 3. Validate dates
        start_date = _normalize_date(start_date, "start_date")
        end_date = _normalize_date(end_date, "end_date", allow_none=True)

        if end_date is None:
            end_date = start_date

        if start_date > end_date:
            raise ValueError("'start_date' must not be later than 'end_date'.")

        # 4. Validate mode
        valid_modes = {"hourly", "daily", "monthly"}

        if mode not in valid_modes:
            raise ValueError(f"'mode' must be one of {valid_modes}")

        if mode == "daily":
            # 5. Validate frequency
            if not isinstance(frequency, str):
                raise TypeError("'frequency' must be a string")

            frequency = frequency.strip().lower()
            valid_frequencies = {"1_hourly", "3_hourly", "6_hourly"}

            if frequency not in valid_frequencies:
                raise ValueError(f"'frequency' must be one of: {', '.join(sorted(valid_frequencies))}")

            if logging_on:
                logger.info("Selected sampling frequency: %s", frequency)

            # 6. Validate time zone
            if not isinstance(time_zone, str):
                raise TypeError("'time_zone' must be a string")

            time_zone = time_zone.strip().lower()

            valid_time_zones = {
                f"utc{sign}{hour:02d}:00"
                for sign, hours in [("-", range(1, 13)), ("+", range(0, 15))]
                for hour in hours
            }

            if time_zone not in valid_time_zones:
                raise ValueError("'time_zone' must be between UTC-12:00 and UTC+14:00. "
                                 "Example: 'utc+00:00', 'utc+01:00', 'utc-05:00'.")

            if logging_on:
                logger.info("Selected time zone: %s", time_zone.upper())

        # 7. Validate times
        if times is not None:

            if logging_on:
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

        if mode not in ["hourly", "monthly"] and times is not None:
            raise ValueError("'times' can only be specified when mode is 'hourly' or 'monthly'.")

        # 8. Validate daily statistics
        if mode == "daily":

            if logging_on:

                logger.info("Users can select to calculate daily statistics from 1 hour, "
                            "3 hours and 6 hours data. ")

            valid_statistics = {"mean", "maximum", "minimum", "sum"}

            if daily_statistic is None:
                daily_statistic = "mean"

            if not isinstance(daily_statistic, str):
                raise TypeError("'daily_statistic' must be a string or None")

            daily_statistic = daily_statistic.strip().lower()

            if daily_statistic not in valid_statistics:
                raise ValueError(f"'daily_statistic' must be one of: {', '.join(sorted(valid_statistics))}")

            # Validate daily sum
            if daily_statistic == "sum":

                if pressure_levels is not None:
                    raise ValueError(
                        "'daily_sum' is available only for single-level data, not pressure-level data."
                    )

                variable_info = database_era5.loc[
                    (database_era5["cds_variable"] == variable)
                    & (database_era5["level_type"] == "single_levels")
                    ]

                if not variable_info["parameter_type"].isin(["accumulations"]).any():
                    raise ValueError(f"'daily_sum' is not available for variable '{variable}'. "
                                     "Only supported accumulated single-level variables can be used.")

            daily_statistic = f"daily_{daily_statistic}"

        else:
            if daily_statistic is not None:
                raise ValueError("'daily_statistic' can only be specified when mode='daily'.")

        # 9. Validate pressure levels
        if pressure_levels == 'all':
            pressure_levels = PRESSURE_LEVELS_ALL

        if pressure_levels is not None:

            if not isinstance(pressure_levels, (list, tuple)):
                raise ValueError("'pressure_levels' must be a non-empty list or tuple.")
            if not pressure_levels:
                raise ValueError("'pressure_levels' must not be empty.")

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
                if level not in PRESSURE_LEVELS_ALL
            ]

            if unavailable_levels:

                suggestions = {
                    level: min(
                        PRESSURE_LEVELS_ALL,
                        key=lambda x: abs(x - level)
                    )
                    for level in unavailable_levels
                }

                suggestion_text = ", ".join(f"{level} → {nearest}" for level, nearest in suggestions.items())

                if not adjust_pressure_levels:
                    raise ValueError(
                        f"Unavailable pressure levels: {unavailable_levels}. "
                        f"Nearest available levels: {suggestion_text}. "
                        "Set adjust_pressure_levels=True to replace them or"
                        " use only available pressure levels."
                    )

                if logging_on:
                    logger.warning("Unavailable pressure levels will be replaced: %s",
                                   suggestion_text)

                pressure_levels = [suggestions.get(level, level) for level in pressure_levels]

            # Remove duplicates and sort
            pressure_levels = sorted(set(pressure_levels), reverse=True)

            pressure_levels = [str(level) for level in pressure_levels]

            if logging_on:
                logger.info("Selected pressure levels (hPa): %s",pressure_levels)

        # 10. Validate area
        if area is not None:

            if logging_on:
                logger.info(
                    "Area input formats:\n"
                    "  1. Predefined region name, e.g. 'NH' (or 'northern_hemisphere'), "
                    "'Europe' (or 'europe'), 'north_atlantic' (or North Atlantic).\n"
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

                if logging_on:
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

        # 11. Validate grid resolution
        # The current CDS Data Stores process schemas for the ERA5
        # hourly, daily-statistics and monthly datasets do not expose
        # a custom 'grid' request parameter.
        if grid_resolution is not None:
            raise ValueError(
                "Custom 'grid_resolution' is not supported by the current "
                "CDS Data Stores API for these ERA5 datasets. Use the "
                "native dataset resolution by setting grid_resolution=None."
            )

        # 12. Validate file format
        if file_format is None:
            file_format = "netcdf" if mode == "daily" else "grib"

        if not isinstance(file_format, str):
            raise TypeError("'file_format' must be a string or None.")

        file_format = file_format.strip().lower()

        if file_format not in {"netcdf", "grib"}:
            raise ValueError("'file_format' must be 'netcdf' or 'grib'.")

        if mode == "daily" and file_format == "grib":
            raise ValueError(
                "Daily statistics support only NetCDF format. Use file_format='netcdf'."
            )
        if file_format == "netcdf" and mode != "daily":
            if logging_on:
                logger.warning(
                    "The native format of MARS datasets is GRIB, "
                    "and this format is recommended for operational use. "
                    "When converted to NetCDF, a request may be split "
                    "into multiple files to preserve data accuracy "
                    "and sufficient metadata."
                )

        # 13. Select dataset
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
            if logging_on:
                logger.info("Monthly averaged reanalysis and Monthly averaged ensemble members data "
                        "are produced by averaging all daily data. Monthly averages by hour of day "
                        "constitute the average over all data within the calendar month for every hour (UTC) "
                        "of the day in case of reanalysis or every third hour (UTC) of the day for ensemble members.")

        client = Client()
        authentication = client.check_authentication()

        if logging_on:
            logger.info("Dataset authentication: %s", authentication)

        collection = client.get_collection(dataset)

        if logging_on:
            logger.info("Dataset: %s", collection.title)
            logger.info("Dataset ID: %s", collection.id)
            logger.info("Available period: %s – %s",
                collection.begin_datetime,collection.end_datetime)

        # 14. Check whether requested dates are within dataset availability
        available_start = collection.begin_datetime.date()
        available_end = collection.end_datetime.date()

        if start_date.date() < available_start:
            raise ValueError(f"Start date is earlier than dataset availability ({available_start}).")

        if end_date.date() > available_end:
            raise ValueError( f"End date is later than dataset availability ({available_end}).")

        # 15. Define request configuration
        request_config = {
            "variable": [variable],
            "mode": mode,
            "start_date": start_date,
            "end_date": end_date,
            "pressure_levels": pressure_levels,
            "times": sorted(times) if times is not None else None,
            "area": area,
            "grid_resolution": grid_resolution,
            "file_format": file_format,
            "download_format": "zip" if mode == "daily" else None,
        }

        if mode == "daily":
            request_config.update({
                "daily_statistic": daily_statistic,
                "frequency": frequency,
                "time_zone": time_zone,
            })

        request_infos = []

        batches = _generate_request_batches(request_config, logging_on=logging_on)
        request_db = ERA5RequestDatabase(db_path=DATABASE_PATH)

        for batch in batches:

            request_config_per_batch, request_params_per_batch = _build_request_parameters(
                request_config=request_config,
                batch=batch
            )

            # Generate short hash
            config_for_hash = request_config_per_batch.copy()
            config_for_hash["start_date"] = request_config_per_batch["start_date"].isoformat()
            config_for_hash["end_date"] = request_config_per_batch["end_date"].isoformat()

            config_string = json.dumps(
                config_for_hash,
                sort_keys=True,
                separators=(",", ":"),
            )

            request_hash = hashlib.sha256(config_string.encode("utf-8")).hexdigest()

            # 16. Check whether an identical request already exists
            existing_request = request_db.get_request_by_hash(request_hash)

            if existing_request is not None:
                existing_request = check_era5_status(
                    client,
                    existing_request["request_id"],
                    request_db,
                    logging_on=logging_on
                )

                if existing_request is None:
                    if logging_on:
                        logger.error(
                            "Could not refresh existing request with hash %s. "
                            "Skipping to avoid submitting a duplicate.",
                            request_hash,
                        )
                    continue

                status = existing_request["status"]

                if status not in {"failed", "deleted", "expired", "rejected"}:
                    existing_request["existing"] = True
                    request_infos.append(existing_request)

                    if logging_on:
                        logger.info(
                            "Request already exists: %s (status: %s). "
                            "No new request submitted.",
                            existing_request["request_id"],
                            status,
                        )

                    continue

            # 17. Define files names
            filename = _build_output_filename(
                request_config=request_config_per_batch,
                request_hash=request_hash
            )

            output_file = os.path.join(output_dir, filename)

            # 13. Check existing file
            if os.path.isfile(output_file) and os.path.getsize(output_file) > 0:
                print(f"File already exists: {output_file}")

                request_info = {
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
                request_infos.append(request_info)
                continue

            os.makedirs(output_dir, exist_ok=True)

            try:
                print(f"Submitting ERA5 {mode} data: {output_file}")
                remote = client.submit(dataset, request_params_per_batch)

            except Exception as e:
                if logging_on:
                    logger.error("Request submission failed: %s", e)

                request_infos.append({
                    "request_id": None,
                    "dataset": dataset,
                    "request": request_params_per_batch,
                    "output_file": output_file,
                    "status": "submission_failed",
                    "created_at": None,
                    "downloaded": False,
                    "request_hash": request_hash,
                    "existing": False,
                    "error": str(e),
                })
                continue

            request_info = {
                "request_id": remote.request_id,
                "dataset": dataset,
                "request": request_params_per_batch,
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
                if logging_on:
                    logger.error(
                        "Request was submitted, but database_era5 operation failed. "
                        "Request ID: %s. Error: %s",
                        remote.request_id,
                        e,
                    )
                raise

            if logging_on:
                logger.info("Request submitted successfully.")
                logger.info("Request ID: %s", request_info["request_id"])
                logger.info("Status: %s", request_info["status"])

            request_infos.append(request_info)

        return request_infos

def check_era5_status(client, request_id, request_db, logging_on=True):
    """Refresh a CDS request's status in the local database.

    Return the updated database record, or None if the status check fails.
    """
    logger = get_logger("check_era5_status")
    try:
        remote = client.get_remote(request_id)
        status = getattr(remote, "status", None)
        results_ready = getattr(remote, "results_ready", True)

        if status == "successful" and not results_ready:
            status = "expired"

        if status is None:
            print(f"CDS returned no status for request {request_id!r}")
            return None

        def to_db_timestamp(value):
            if value is None:
                return None
            return value.isoformat() if hasattr(value, "isoformat") else str(value)

        request_db.update_request(
            request_id,
            status=status,
            started_at=to_db_timestamp(getattr(remote, "started_at", None)),
            finished_at=to_db_timestamp(getattr(remote, "finished_at", None)),
        )

        return request_db.get_request(request_id)


    except Exception as exc:

        err_msg = str(exc).lower()

        if "404" in err_msg or "not found" in err_msg:

            if logging_on:
                logger.warning("Request %s no longer exists on CDS (404). Marking as 'deleted'.", request_id)

            request_db.update_request(
                request_id,
                status="deleted",
                error=str(exc),
            )

            return request_db.get_request(request_id)

        print(f"Could not refresh CDS request {request_id!r}: {exc}")

        return None

def download_era5_results(request_db=None, logging_on=True):
    """
    Download completed ERA5 requests stored in the request database.

    The function checks the status of each submitted CDS request and
    downloads the results when they become available.

    Files are downloaded to temporary directories located inside their
    respective output directories. After a successful download, the
    temporary file is moved to its final destination.

    Parameters
    ----------
    request_db : ERA5RequestDatabase
        Database instance containing information about submitted ERA5
        requests, including their IDs, statuses and output file paths.

    logging_on : bool, default=True
        Enable logging of download progress, status information and errors.

    Returns
    -------
    list of dict
        Results of requests processed during the current execution.

        Each dictionary contains:
        - request_id : str
            CDS request identifier.
        - output_file : str
            Path to the output file.
        - result : str, optional
            Path to the successfully downloaded file.
        - status : str
            Processing status. Possible values include:
            - "downloaded"
            - "file_already_exists"
            - "downloaded_db_update_failed"
            - "file_exists_db_update_failed"
            - "database_sync_failed"
            - "failed"
        - error : str, optional
            Error description when a download or database operation fails.

    Notes
    -----
    - Non-empty existing output files are treated as downloaded, and the
      corresponding database record is synchronized when necessary.
    - If a request is marked as downloaded but its output file is missing
      or empty, the database flag is reset and the CDS request is checked
      again for download readiness.
    - Requests that are not yet completed or whose results are not
      available are skipped.
    - Downloaded files are stored in the output paths recorded in
      the request database.
    - Temporary files are automatically removed after processing.
    - Existing final output files are not overwritten unless a new
      temporary download has completed successfully.
    """

    logger = get_logger("download_era5_results")

    if request_db is None:
        request_db = ERA5RequestDatabase()

    client = Client(cleanup=False)

    requests = request_db.list_requests()

    downloaded_results = []

    for request_info in requests:

        request_id = request_info.get("request_id")
        output_file = request_info.get("output_file")

        if not request_id or not output_file:
            continue

        if request_info.get("status") in {"expired", "failed", "rejected", "deleted"}:
            continue

        output_file = os.fspath(output_file)

        # Check whether a non-empty output file already exists
        file_exists = (
                os.path.isfile(output_file)
                and os.path.getsize(output_file) > 0
        )

        if file_exists:
            # Synchronize the database if the file exists
            # but is not marked as downloaded.
            if not request_info.get("downloaded", False):

                try:
                    request_db.update_request(
                        request_id,
                        downloaded=True,
                        downloaded_at=datetime.now().isoformat(),
                        error=None
                    )

                except Exception as db_error:

                    if logging_on:
                        logger.error(
                            "File exists, but database update failed "
                            "for request %s: %s",
                            request_id,
                            db_error
                        )

                    downloaded_results.append({
                        "request_id": request_id,
                        "output_file": output_file,
                        "status": "file_exists_db_update_failed",
                        "error": str(db_error)
                    })

                    continue

            if logging_on:
                logger.info(
                    "Output file already exists. Skipping download: %s",
                    output_file
                )

            downloaded_results.append({
                "request_id": request_id,
                "output_file": output_file,
                "status": "file_already_exists"
            })

            continue

        # Database says downloaded, but the file is missing or empty.
        # Reset the database flag and allow the request to be downloaded again.
        if request_info.get("downloaded", False):

            if logging_on:
                logger.warning(
                    "Request %s is marked as downloaded, "
                    "but the output file is missing or empty. "
                    "Attempting to download it again.",
                    request_id
                )

            try:
                request_db.update_request(
                    request_id,
                    downloaded=False,
                    downloaded_at=None
                )

            except Exception as db_error:

                if logging_on:
                    logger.error(
                        "Could not reset download status for request %s: %s",
                        request_id,
                        db_error
                    )

                downloaded_results.append({
                    "request_id": request_id,
                    "output_file": output_file,
                    "status": "database_sync_failed",
                    "error": str(db_error)
                })
                continue
        try:
            # Check the current status on CDS
            remote = client.get_remote(request_id)
            status = getattr(remote, "status", None)
            results_ready = getattr(remote, "results_ready", True)

            if status == "successful" and not results_ready:
                status = "expired"

            # Update the current request status in the database
            request_db.update_request(request_id, status=status)

            # Download only completed requests whose results have not expired
            if status != "successful" or not results_ready:

                if logging_on:
                    logger.info(
                        "Request %s is not ready. Current status: %s",
                        request_id,
                        status
                    )

                continue

            output_dir = os.path.dirname(output_file) or "."
            os.makedirs(output_dir, exist_ok=True)

            # Download to a temporary directory first
            with tempfile.TemporaryDirectory(
                    prefix=".era5_download_", dir=output_dir
            ) as temp_dir:

                temp_output_file = os.path.join(temp_dir, os.path.basename(output_file))

                remote.download(temp_output_file)

                # Verify downloaded file
                if not os.path.isfile(temp_output_file):
                    raise RuntimeError(
                        f"CDS download did not create expected file: {temp_output_file}"
                    )

                if os.path.getsize(temp_output_file) == 0:
                    raise RuntimeError(f"Downloaded file is empty: {temp_output_file}")

                # Move completed file to its final destination
                os.replace(temp_output_file, output_file)

            result = output_file

            # Update database after successful download
            try:
                request_db.update_request(
                    request_id,
                    downloaded=True,
                    downloaded_at=datetime.now().isoformat(),
                    error=None
                )

            except Exception as db_error:

                if logging_on:
                    logger.error(
                        "File downloaded, but database update failed "
                        "for request %s: %s",
                        request_id,
                        db_error
                    )

                downloaded_results.append({
                    "request_id": request_id,
                    "output_file": output_file,
                    "result": result,
                    "status": "downloaded_db_update_failed",
                    "error": str(db_error)
                })

                continue

            downloaded_results.append({
                "request_id": request_id,
                "output_file": output_file,
                "result": result,
                "status": "downloaded"
            })

            if logging_on:
                logger.info("Request %s downloaded: %s", request_id, output_file)

        # ---> ОСЬ ЦЕЙ ОСТАННІЙ БЛОК EXCEPT ДЛЯ ПОМИЛОК CDS API <---
        except Exception as e:
            err_msg = str(e).lower()
            is_not_found = "404" in err_msg or "not found" in err_msg

            if logging_on:
                if is_not_found:
                    logger.warning(
                        "Request %s not found on CDS (404). Marking as 'deleted' in database.",
                        request_id
                    )
                else:
                    logger.error("Download failed for request %s: %s", request_id, e)

            # Record download error (and mark as deleted if 404) without deleting local files
            try:
                update_kwargs = {"error": str(e)}
                if is_not_found:
                    update_kwargs["status"] = "deleted"

                request_db.update_request(request_id, **update_kwargs)

            except Exception as db_error:

                if logging_on:
                    logger.error(
                        "Could not save download error to database "
                        "for request %s: %s",
                        request_id,
                        db_error
                    )

            downloaded_results.append({
                "request_id": request_id,
                "output_file": output_file,
                "status": "deleted" if is_not_found else "failed",
                "error": str(e)
            })

    if logging_on:
        logger.info(
            "Download process completed. Downloaded %d of %d requests.",
            sum(r["status"] in ("downloaded", "file_already_exists")
                for r in downloaded_results),
            len(requests)
        )
    return downloaded_results