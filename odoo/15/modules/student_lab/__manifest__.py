# See LICENSE file for full copyright and licensing details.

{
    'name': 'Simulab',
    'version': '14.0.1.0.0',
    'author': 'Immersive Labz Pvt. Ltd',
    'website': 'http://www.immersivelabz.com',
    'category': 'Education',
    'license': "AGPL-3",
    'complexity': 'easy',
    'Summary': 'A Module For Simulab Product management',
    'images': ['static/description/EMS.jpg'],
    'depends': ['base','web', 'auth_signup', 'dms'],
    'data': ['security/school_security.xml',
             'security/ir.model.access.csv',
             'views/student_view.xml',
             'views/school_view.xml',
             'views/teacher_view.xml',
             'views/user_otp_view.xml',
             'views/home_page_view.xml',
             'views/simulab_course_tag_views.xml',
             'views/simulab_experiment_views.xml',
             'views/simulab_course_view.xml',
             'views/simulab_experiment_quiz_views.xml',
              'views/simulab_enrolled_courses_views.xml',
             #'views/firebase_push_view.xml',
             'views/simulab_faq_view.xml',
             'views/course_views_view.xml',
             'views/notification_template_view.xml',
             'views/simulab_notification_view.xml',
             'views/simulab_menuitem.xml',
             'data/data.xml',
             ],
    'assets': {
        'web.assets_backend': [
            "/simulab/static/src/scss/schoolcss.scss"
        ],
    },
    'demo': [],
    'installable': True,
    'application': True
}