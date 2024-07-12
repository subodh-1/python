# -*- coding: utf-8 -*-
{
    'name': "immersive_hr_emails",

    'summary': """
        Employee module relevant to immersive labz HR emails""",

    'description': """
        Employee module relevant to immersive labz HR emails
    """,

    'author': "ImmersiveVision Pvt Ltd",
    'website': "http://www.immerisvelabz.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Employees',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/immersive_employee_views.xml',
        'data/employee_mail_template.xml',
        'data/ir_cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "images": ["images/immersive_hr.png"],
    "license": "OPL-1",
    "installable": True,
}
