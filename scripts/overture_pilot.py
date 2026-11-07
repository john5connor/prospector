"""Overture Places pilot: Oakland/Wayne/Genesee/Livingston counties, MI.
Run: .venv-pilot/bin/python scripts/overture_pilot.py   (uv venv .venv-pilot && uv pip install duckdb)
Writes data/pilot.duckdb (gitignored). Read-only against public S3; no accounts, no n8n.
Afterwards the 'pilot' table is derived with:
  CREATE TABLE pilot AS SELECT * FROM places_raw WHERE tax_primary IN ('hvac_service','roofing','plumbing')
"""
import duckdb, time
c=duckdb.connect('data/pilot.duckdb')
c.sql("INSTALL spatial; INSTALL httpfs; LOAD spatial; LOAD httpfs; SET s3_region='us-west-2';")
R='2026-10-21.0'
# county polygons
c.sql(f"""CREATE OR REPLACE TABLE counties AS
SELECT names.primary AS name, region, geometry FROM read_parquet('s3://overturemaps-us-west-2/release/{R}/theme=divisions/type=division_area/*')
WHERE subtype='county' AND country='US' AND region='US-MI' AND names.primary IN ('Oakland County','Wayne County','Genesee County','Livingston County')""")
print(c.sql("select name, ST_XMin(geometry),ST_XMax(geometry),ST_YMin(geometry),ST_YMax(geometry) from counties").fetchall())

# --- places in the four counties (bbox prefilter + point-in-polygon) ---
c.sql("LOAD spatial; LOAD httpfs; SET s3_region='us-west-2';")
R='2026-10-21.0'
t=time.time()
c.sql(f"""CREATE OR REPLACE TABLE places_raw AS
SELECT p.id, p.names.primary AS name, p.basic_category, p.taxonomy.primary AS tax_primary, p.taxonomy.hierarchy AS tax_hier,
 p.confidence, p.operating_status, p.websites, p.socials, p.emails, p.phones, p.addresses, p.brand.names.primary AS brand,
 [s.dataset for s in p.sources] AS datasets, ST_X(p.geometry) AS lon, ST_Y(p.geometry) AS lat, k.name AS county
FROM read_parquet('s3://overturemaps-us-west-2/release/{R}/theme=places/type=place/*') p
JOIN counties k ON ST_Within(p.geometry, k.geometry)
WHERE p.bbox.xmin BETWEEN -84.17 AND -82.74 AND p.bbox.ymin BETWEEN 42.02 AND 43.23""")
print(time.time()-t)
print(c.sql("select county,count(*) from places_raw group by 1").fetchall())

c.sql("CREATE OR REPLACE TABLE pilot AS SELECT * FROM places_raw WHERE tax_primary IN ('hvac_service','roofing','plumbing')")
