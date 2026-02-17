"""
Seed productions table from existing projects.
Creates one production record per project with project_name = project.name.
"""
import sys
sys.path.insert(0, '.')

from modules.projects_db import get_projects_db
from modules.production_store import get_production_store

def main():
    projects_db = get_projects_db()
    prod_store = get_production_store()

    projects = projects_db.get_all_projects()
    print(f"Found {len(projects)} projects")

    # Check if productions already exist
    existing = prod_store.get_all_productions(limit=500)
    if existing:
        print(f"Productions table already has {len(existing)} records. Skipping seed.")
        return

    created = 0
    for proj in projects:
        proj_name = proj["name"]
        try:
            prod_id = prod_store.create_production(
                title=proj_name,
                project_name=proj_name,
                video_status="draft",
            )
            created += 1
            print(f"  ✓ Created production #{prod_id}: {proj_name}")
        except Exception as e:
            print(f"  ✗ Failed for '{proj_name}': {e}")

    print(f"\nDone! Created {created}/{len(projects)} productions.")

if __name__ == "__main__":
    main()
