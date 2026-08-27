__artifacts_v2__ = {
    "ford_installed_software": {
        "name": "Installed Software",
        "description": "Software packages present on the head unit, each with the package "
                       "identifier, the part number, the display name, the version and the "
                       "package type the unit recorded.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the packages table in pacman.db, the unit's own package manager "
                 "store. The table records no install or update time, so this is an "
                 "inventory of what is present rather than a history of when it arrived. "
                 "The type column separates applications from asset packages; on the tested "
                 "image the asset packages were map regions, so the set of regions present "
                 "bounds where the built-in navigation could route without a further "
                 "download. Package identifiers can name the vehicle line the unit was "
                 "built for. state, format and signature type are reported as stored.",
        "paths": ('*/alm/pacman/pacman.db*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 30 rows",
        },
        "output_types": "standard",
        "artifact_icon": "package",
    },
}

from scripts.ilapfuncs import (artifact_processor, get_file_path,
                               open_sqlite_db_readonly)


@artifact_processor
def ford_installed_software(context):
    data_list = []
    source_path = get_file_path(context.get_files_found(), "pacman.db")
    if not source_path:
        return (), [], ''
    db = open_sqlite_db_readonly(source_path)
    if db is None:
        return (), [], context.get_relative_path(source_path)
    cursor = db.cursor()
    cursor.execute('''
        SELECT name, version, type, package_id, ford_part_number,
               old_ford_part_number, state, format, signature_type, description
        FROM packages
        ORDER BY type, name
    ''')
    for row in cursor.fetchall():
        data_list.append(row + (context.get_relative_path(source_path),))
    db.close()

    data_headers = ('Name', 'Version', 'Type', 'Package ID', 'Part Number',
                    'Previous Part Number', 'State (as stored)', 'Format',
                    'Signature Type (as stored)', 'Description', 'Source File')
    return data_headers, data_list, context.get_relative_path(source_path)
