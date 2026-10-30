"""Segment the Swat main stem into fixed-length reaches with corridors and slope.

HydroRIVERS gives the topology but comes from 15 arc-second data, so its line is
snapped to the valley floor on GLO-30 before segmenting. Corridor polygons are the
DEM valley floor around that line: a first estimate, to be replaced by SAR-derived
active channel extents.
"""
import glob

import click
import geopandas as gpd
import numpy as np
import rasterio
import shapely
import rasterio.features
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from scipy.ndimage import (
    map_coordinates, maximum_filter1d, median_filter, minimum_filter, uniform_filter1d,
)
from shapely import make_valid
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import linemerge, substring, unary_union
from skimage.graph import route_through_array
from sqlalchemy import create_engine, text

from .config import DATA_DIR, DB_URL, METRIC_EPSG

RIVERS_SHP = f"{DATA_DIR}/raw/hydrorivers/HydroRIVERS_v10_as_shp/HydroRIVERS_v10_as.shp"
DEM_TILES = f"{DATA_DIR}/raw/dem/*.tif"
CELL_M = 30
TRANSECT_STEP_M = 50
SNAP_SEARCH_M = 1000
MAX_HALF_WIDTH_M = 1000
MIN_HALF_WIDTH_M = 50


def trace_main_stem(tehsils, min_upland):
    """Walk upstream from the district outlet along the largest tributary."""
    w, s, e, n = tehsils.total_bounds
    rivers = gpd.read_file(RIVERS_SHP, bbox=(w - 1, s - 1, e + 1, n + 1))
    inside = rivers[rivers.intersects(tehsils.union_all())]
    current = inside.loc[inside.UPLAND_SKM.idxmax()]

    segments = [current]
    while True:
        upstream = rivers[rivers.NEXT_DOWN == current.HYRIV_ID]
        if upstream.empty:
            break
        current = upstream.loc[upstream.UPLAND_SKM.idxmax()]
        if current.UPLAND_SKM < min_upland:
            break
        segments.append(current)

    line = linemerge(unary_union([s.geometry for s in segments]))
    head = Point(segments[-1].geometry.coords[0])
    if Point(line.coords[-1]).distance(head) < Point(line.coords[0]).distance(head):
        line = LineString(line.coords[::-1])
    return gpd.GeoSeries([line], crs=4326)


def load_dem(bounds_4326, epsg):
    """Mosaic GLO-30 tiles and warp them to a metric grid."""
    w, s, e, n = bounds_4326
    sources = [rasterio.open(p) for p in sorted(glob.glob(DEM_TILES))]
    mosaic, src_transform = merge(sources, bounds=(w, s, e, n))
    src_crs = sources[0].crs
    for src in sources:
        src.close()

    height, width = mosaic.shape[1:]
    dst_crs = f"EPSG:{epsg}"
    dst_transform, dst_w, dst_h = calculate_default_transform(
        src_crs, dst_crs, width, height, w, s, e, n, resolution=CELL_M
    )
    dem = np.empty((dst_h, dst_w), dtype="float32")
    reproject(
        mosaic[0], dem, src_transform=src_transform, src_crs=src_crs,
        dst_transform=dst_transform, dst_crs=dst_crs, resampling=Resampling.bilinear,
    )
    return dem, dst_transform


def to_rowcol(affine, xs, ys):
    cols, rows = ~affine * (np.asarray(xs), np.asarray(ys))
    return rows - 0.5, cols - 0.5


def to_xy(affine, rows, cols):
    return affine * (np.asarray(cols) + 0.5, np.asarray(rows) + 0.5)


def sample(dem, affine, xs, ys):
    rows, cols = to_rowcol(affine, xs, ys)
    return map_coordinates(dem, [rows, cols], order=1, mode="nearest")


def snap_to_valley_floor(line, dem, affine):
    """Least-cost path along the valley floor, kept near the HydroRIVERS line."""
    relief = dem - minimum_filter(dem, size=int(SNAP_SEARCH_M / CELL_M) | 1)
    cost = 1.0 + relief.astype("float64") ** 2

    corridor = rasterio.features.geometry_mask(
        [line.buffer(SNAP_SEARCH_M)], dem.shape, affine, invert=True
    )
    cost[~corridor] = -1

    def lowest_near(point):
        r, c = (int(round(float(v))) for v in to_rowcol(affine, point[0], point[1]))
        span = int(300 / CELL_M)
        window = dem[r - span : r + span + 1, c - span : c + span + 1]
        dr, dc = np.unravel_index(np.argmin(window), window.shape)
        return r - span + dr, c - span + dc

    path, _ = route_through_array(
        cost, lowest_near(line.coords[0]), lowest_near(line.coords[-1]),
        fully_connected=True, geometric=True,
    )
    rows, cols = np.array(path).T
    xs, ys = to_xy(affine, rows, cols)
    # Smooth out the grid staircase; ends stay fixed.
    smooth = lambda v: np.r_[v[0], uniform_filter1d(v.astype(float), 7, mode="nearest")[1:-1], v[-1]]
    return LineString(np.c_[smooth(np.asarray(xs)), smooth(np.asarray(ys))])


def channel_profile(line, dem, affine):
    """Local surface and a bed forced never to rise downstream, every transect."""
    distance = np.arange(0, line.length + TRANSECT_STEP_M, TRANSECT_STEP_M)
    distance[-1] = line.length
    points = [line.interpolate(d) for d in distance]
    xs = np.array([p.x for p in points])
    ys = np.array([p.y for p in points])
    raw = sample(dem, affine, xs, ys)
    surface = median_filter(raw, size=7, mode="nearest")
    return distance, xs, ys, surface, np.minimum.accumulate(raw)


def corridor_offsets(distance, xs, ys, surface, dem, affine, bank_height):
    """Left and right distance to where ground rises bank_height above the channel.

    Uses the local surface, not the monotonic bed: DEM noise pulls that bed below
    the ground, which would read as a bank at the first step on steep reaches.
    """
    dx, dy = np.gradient(xs, distance), np.gradient(ys, distance)
    norm = np.hypot(dx, dy)
    nx, ny = -dy / norm, dx / norm
    steps = np.arange(CELL_M, MAX_HALF_WIDTH_M + CELL_M, CELL_M)

    def side(sign):
        px = xs[:, None] + sign * nx[:, None] * steps
        py = ys[:, None] + sign * ny[:, None] * steps
        ground = sample(dem, affine, px.ravel(), py.ravel()).reshape(px.shape)
        above = ground > surface[:, None] + bank_height
        # Three cells in a row, so a lone tree on a gravel bar is not a bank.
        bank = above[:, :-2] & above[:, 1:-1] & above[:, 2:]
        first = np.where(bank.any(axis=1), bank.argmax(axis=1), len(steps) - 1)
        return np.maximum(steps[first] - CELL_M, MIN_HALF_WIDTH_M).astype(float)

    # Running max keeps bars inside; the mean takes the steps out of the outline.
    window = int(300 / TRANSECT_STEP_M) | 1
    smooth = lambda v: uniform_filter1d(maximum_filter1d(v, window, mode="nearest"), window, mode="nearest")
    return nx, ny, smooth(side(1)), smooth(side(-1))


def corridor_polygon(xs, ys, nx, ny, left, right):
    lx, ly = xs + nx * left, ys + ny * left
    rx, ry = xs - nx * right, ys - ny * right
    quads = [
        make_valid(Polygon([(lx[i], ly[i]), (lx[i + 1], ly[i + 1]), (rx[i + 1], ry[i + 1]), (rx[i], ry[i])]))
        for i in range(len(xs) - 1)
    ]
    # The buffer pair closes slivers left where quads fold over at bends.
    return unary_union(quads).buffer(15).buffer(-15)


def nearest_reach_cells(river, edges, corridor):
    """Partition the plane by nearest reach, so corridors cannot gap or overlap."""
    distance = np.arange(0, river.length, 25.0)
    sites = MultiPoint([river.interpolate(d) for d in distance])
    cells = shapely.voronoi_polygons(sites, extend_to=corridor, ordered=True)
    owner = np.searchsorted(edges, distance, side="right") - 1
    return [unary_union([c for c, o in zip(cells.geoms, owner) if o == i]) for i in range(len(edges) - 1)]


def largest_polygon(geom):
    parts = getattr(geom, "geoms", [geom])
    return max((p for p in parts if p.geom_type == "Polygon"), key=lambda p: p.area)


@click.command()
@click.option("--reach-length", default=500, show_default=True, help="Target reach length (m)")
@click.option("--min-upland", default=1500.0, show_default=True,
              help="Stop upstream below this drainage area (km2); 1500 ends at the Kalam confluence")
@click.option("--bank-height", default=3.0, show_default=True,
              help="Height above the bed that bounds the corridor (m)")
@click.option("--replace", is_flag=True, help="Delete existing reaches first")
def main(reach_length, min_upland, bank_height, replace):
    eng = create_engine(DB_URL)
    tehsils = gpd.read_postgis("SELECT id, tehsil, geom FROM admin_tehsils", eng, geom_col="geom")

    with eng.begin() as con:
        existing = con.execute(text("SELECT count(*) FROM reaches")).scalar()
        observed = con.execute(text("SELECT count(*) FROM bar_obs")).scalar()
    if existing and not replace:
        raise click.ClickException(f"{existing} reaches exist; pass --replace to rebuild them")
    if observed:
        raise click.ClickException(f"{observed} bar_obs rows depend on the current reaches")

    main_stem = trace_main_stem(tehsils, min_upland)
    click.echo(f"main stem traced, bounds {main_stem.total_bounds.round(3).tolist()}")

    w, s, e, n = main_stem.total_bounds
    dem, affine = load_dem((w - 0.03, s - 0.03, e + 0.03, n + 0.03), METRIC_EPSG)
    click.echo(f"DEM grid {dem.shape}")

    hydro = main_stem.to_crs(METRIC_EPSG).iloc[0]
    snapped = snap_to_valley_floor(hydro, dem, affine)
    drift = np.mean([hydro.distance(snapped.interpolate(d)) for d in np.arange(0, snapped.length, 500)])
    click.echo(f"snapped line {snapped.length / 1000:.1f} km, mean shift from HydroRIVERS {drift:.0f} m")

    # Trim to where the river is last inside the district.
    district = tehsils.to_crs(METRIC_EPSG).union_all()
    inside = snapped.intersection(district)
    stops = [snapped.project(Point(c)) for part in getattr(inside, "geoms", [inside]) for c in part.coords]
    river = substring(snapped, min(stops), max(stops))

    distance, xs, ys, surface, bed = channel_profile(river, dem, affine)
    nx, ny, left, right = corridor_offsets(distance, xs, ys, surface, dem, affine, bank_height)
    corridor = corridor_polygon(xs, ys, nx, ny, left, right)

    count = max(1, round(river.length / reach_length))
    edges = np.linspace(0, river.length, count + 1)
    tehsils_utm = tehsils.to_crs(METRIC_EPSG)
    cells = nearest_reach_cells(river, edges, corridor)
    rows = []

    for seq in range(1, count + 1):
        start, end = edges[seq - 1], edges[seq]
        centerline = substring(river, start, end)
        mask = (distance[:-1] < end) & (distance[1:] > start)
        polygon = largest_polygon(make_valid(corridor.intersection(cells[seq - 1])))

        midpoint = centerline.interpolate(0.5, normalized=True)
        tehsil = tehsils_utm.loc[tehsils_utm.distance(midpoint).idxmin()]
        # A 1 km run-out either side steadies slope against DEM noise.
        low, high = max(start - 1000, 0), min(end + 1000, river.length)
        slope = (np.interp(low, distance, bed) - np.interp(high, distance, bed)) / (high - low)
        widths = (left + right)[:-1][mask]

        wgs = gpd.GeoSeries([centerline, polygon], crs=METRIC_EPSG).to_crs(4326)
        rows.append({
            "river": "Swat", "seq": seq, "tehsil_id": int(tehsil.id),
            "length_m": round(centerline.length, 1), "slope": round(float(slope), 6),
            "width_mean": round(float(widths.mean()), 1),
            "centerline": wgs.iloc[0].wkt, "geom": wgs.iloc[1].wkt,
        })

    sql = text("""
        INSERT INTO reaches (river, seq, tehsil_id, length_m, slope, width_mean, centerline, geom)
        VALUES (:river, :seq, :tehsil_id, :length_m, :slope, :width_mean,
                ST_GeomFromText(:centerline, 4326), ST_GeomFromText(:geom, 4326))
    """)
    with eng.begin() as con:
        if replace:
            con.execute(text("DELETE FROM reaches"))
            con.execute(text("SELECT setval(pg_get_serial_sequence('reaches', 'id'), 1, false)"))
        con.execute(sql, rows)

    widths = [r["width_mean"] for r in rows]
    click.echo(
        f"registered {len(rows)} reaches, {river.length / 1000:.1f} km, "
        f"bed {bed[0]:.0f} to {bed[-1]:.0f} m, width median {np.median(widths):.0f} m"
    )


if __name__ == "__main__":
    main()
