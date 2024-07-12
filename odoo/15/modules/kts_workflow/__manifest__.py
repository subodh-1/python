# -*- coding: utf-8 -*-
{
    'name': 'Workflow Design',
    'version': '1.0',
    'summary': 'Workflow Management',
    'sequence': -10,
    'description': """Workflow Management""",
    "depends": ["mail", 'base'],
    'data': [
        'security/kts_workflow_security.xml',
        'views/workflow_views.xml',
        'views/workflow_team_views.xml',
        'security/ir.model.access.csv',
        'views/workflow_menu_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
