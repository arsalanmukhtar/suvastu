import click
import asf_search as asf

from .config import EARTHDATA_TOKEN, DATA_DIR


@click.command()
@click.argument("granules", nargs=-1, required=True)
def main(granules):
    session = asf.ASFSession().auth_with_token(EARTHDATA_TOKEN)
    results = asf.granule_search(list(granules))
    results.download(path=f"{DATA_DIR}/raw", session=session, processes=4)
    click.echo(f"downloaded {len(results)} files to {DATA_DIR}/raw")


if __name__ == "__main__":
    main()
