__artifacts_v2__ = {
    "contactsInfo": {
        "name": "Contacts",
        "description": "Contact records (with phone, email and address) from a vehicle "
                       "infotainment contact.db.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2021-07-19",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Contacts",
        "notes": "Date of Birth is kept as stored (text); its format varies by head unit.",
        "paths": ('*/contact.db*',),
        "output_types": "standard",
        "artifact_icon": "user",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def contactsInfo(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('contact.db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT
            contact_master.first_name, contact_master.middle_name, contact_master.last_name,
            phone_table.phone_number, contact_master.email_personal, contact_master.email_work,
            contact_master.email_organization, contact_master.email_other1,
            contact_master.email_other2, contact_master.org_name, contact_master.position_in_org,
            contact_master.birth_date, contact_master.note, contact_master.url,
            contact_master.category, contact_master.fax_number, address_table.addr_street,
            address_table.addr_city, address_table.addr_state, address_table.addr_zipcode,
            device_contact.device_id
            FROM contact_master
            LEFT JOIN address_table ON address_table.contact_ID = contact_master.contact_ID
            LEFT JOIN phone_table ON phone_table.contact_ID = contact_master.contact_ID
            LEFT JOIN device_contact ON device_contact.contact_ID = contact_master.contact_ID
            ORDER BY device_contact.device_id ASC
        ''')
        for row in cursor.fetchall():
            data_list.append(tuple(row))
        db.close()

    data_headers = ('First Name', 'Middle Name', 'Last Name', ('Phone Number', 'phonenumber'),
                    'Personal Email', 'Work Email', 'Organization Email', 'Other Email 1',
                    'Other Email 2', 'Organization', 'Position in Organization', 'Date of Birth',
                    'Note', 'URL', 'Category', ('Fax', 'phonenumber'), 'Street', 'City', 'State',
                    'Zip Code', 'Source Phone')
    return data_headers, data_list, context.get_relative_path(source_path)
