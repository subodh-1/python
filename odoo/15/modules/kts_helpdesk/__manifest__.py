# Copyright 2017-2019 MuK IT GmbH
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "IT HelpDesk",
    "summary": """HelpDesk Incident Reporting,Site Package, FTP and CD/DVD""",
    "version": "14.0.1.0.0",
    "sequence": -100,
    "category": "Document Management",
    "license": "LGPL-3",
    "website": "http://www.kreativtech.com/",
    "author": "Laxman Kalewar",
    "depends": ["mail", "kts_workflow", 'board'],
    "data": [

        'security/kts_helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/ftp_sequence.xml',
        'data/helpdesk_mail.xml',
        'views/kts_incident/helpdesk_ticket_category_views.xml',
        'views/kts_incident/helpdesk_ticket_channel_views.xml',
        'views/kts_incident/helpdesk_incident_views.xml',
        'views/dashboard_views.xml',
        'views/kts_helpdesk_menu.xml',
    ],
    "demo": [],
    "application": True,
}
