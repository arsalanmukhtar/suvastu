import click
import hyp3_sdk as sdk

from .config import EARTHDATA_USERNAME, EARTHDATA_PASSWORD, DATA_DIR


def client():
    return sdk.HyP3(username=EARTHDATA_USERNAME, password=EARTHDATA_PASSWORD)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("granules", nargs=-1, required=True)
@click.option("--name", default="suvastu-rtc")
def rtc(granules, name):
    """Radiometric terrain correction (gamma0, dB, 10 m) with layover/shadow mask."""
    h = client()
    jobs = sdk.Batch()
    for g in granules:
        jobs += h.submit_rtc_job(
            g, name=name, resolution=10, scale="decibel",
            include_ls_map=True, include_dem=False, dem_matching=True,
        )
    click.echo(f"submitted {len(jobs)} RTC jobs")


@cli.command()
@click.argument("reference")
@click.argument("secondary")
@click.option("--name", default="suvastu-insar")
def insar(reference, secondary, name):
    """Interferogram pair; coherence used for change detection on gravel bars."""
    h = client()
    job = h.submit_insar_job(reference, secondary, name=name, looks="10x2", include_inc_map=True)
    click.echo(f"submitted {job.job_id}")


@cli.command()
def credits():
    """Verify Earthdata login against HyP3 and show remaining processing credits."""
    h = client()
    click.echo(f"HyP3 login OK, credits remaining: {h.check_credits()}")


@cli.command()
@click.option("--name", required=True)
def download(name):
    h = client()
    batch = h.find_jobs(name=name)
    batch = h.watch(batch)
    batch.download_files(f"{DATA_DIR}/raw")
    click.echo(f"downloaded {len(batch)} products to {DATA_DIR}/raw")


if __name__ == "__main__":
    cli()
