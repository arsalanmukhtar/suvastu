import click
import asf_search as asf
from shapely.geometry import shape
from sqlalchemy import create_engine, text

from .config import AOI_WKT, DB_URL


@click.command()
@click.option("--start", default="2019-03-01", help="YYYY-MM-DD")
@click.option("--end", default="2026-11-30", help="YYYY-MM-DD")
@click.option("--level", default="SLC", type=click.Choice(["SLC", "GRD_HD"]))
def main(start, end, level):
    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=level,
        beamMode="IW",
        intersectsWith=AOI_WKT,
        start=start,
        end=end,
    )
    click.echo(f"found {len(results)} granules")

    eng = create_engine(DB_URL)
    sql = text("""
        INSERT INTO sar_scenes (granule, platform, orbit_rel, direction, acq_time, footprint)
        VALUES (:g, :p, :o, :d, :t, ST_GeomFromText(:fp, 4326))
        ON CONFLICT (granule) DO NOTHING
    """)
    with eng.begin() as con:
        for r in results:
            p = r.properties
            geom = r.geometry
            fp = shape(geom).wkt
            con.execute(sql, {
                "g": p["sceneName"],
                "p": p["platform"],
                "o": p.get("pathNumber"),
                "d": p.get("flightDirection"),
                "t": p["startTime"],
                "fp": fp,
            })
    click.echo("registered in sar_scenes")


if __name__ == "__main__":
    main()
