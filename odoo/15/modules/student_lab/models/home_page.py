# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SimulabHomePage(models.Model):

    _name = 'simulab.homepage'
    _description = 'Home Page'
    _rec_name = "school_id"

    name = fields.Char(string="Name")
    description = fields.Char(string="Desc")

    active_teachers= fields.Integer(string="Active Teachers", store=True, readonly=True)
    active_classes= fields.Integer(string="Active Classes", store=True, readonly=True)
    student_count= fields.Integer(string="Total Students", store=True, readonly=True)
    quizes_count= fields.Integer(string="Quizes", store=True, readonly=True)

    school_id = fields.Many2one('simulab.school', 'School', required=True,
                                help='School of the dashboard')
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True)

    simulab_course_count = fields.Integer(string="Simulab Course Count", store=True, readonly=True)
    simulab_experiment_count = fields.Integer(string="Simulab Experiments Count", store=True, readonly=True)
    simulab_quizes_count = fields.Integer(string="Simulab Quizes Count", store=True, readonly=True)

    def school_dashboard(self, params={}):
        school_dashboard = self.env['simulab.homepage'].search([])
        return {'return_data_as_record_set': True, 'records': school_dashboard,
                'model': self.env['simulab.homepage']}

    @api.model
    def fields_get_queried_keys(self):
        fields = '{active_teachers, active_classes, student_count, quizes_count, school_id{}, ' \
                 'simulab_course_count, simulab_experiment_count, simulab_quizes_count}'
        return fields

    @api.model
    def update_school_dashboard(self):
        schools = self.env['simulab.school'].sudo().search([])
        for school in schools:
            self.refresh_school_dashboard(school)
        return True

    @api.model
    def refresh_school_dashboard(self, school):
        active_teachers = self.env['school.teacher'].sudo().search_count([('school_id', '=',school.id)])
        active_classes = self.env['school.standard'].sudo().search_count([('school_id', '=',school.id)])
        student_count = self.env['student.student'].sudo().search_count([('school_id', '=',school.id)])
        enrolled_courses = self.env['enrolled.course'].sudo().search([('school_id', '=',school.id)])
        quizes_list=[]
        for enrolled_course in enrolled_courses:
            for exp in enrolled_course.course_id.experiment_ids:
                for quiz in exp.quiz_ids:
                    if quiz not in quizes_list:
                        quizes_list = quizes_list+[quiz]

        school_dashboard = self.env['simulab.homepage'].sudo().search([('school_id', '=',school.id)])

        simulab_course_count = self.env['simulab.course'].sudo().search_count([])
        simulab_experiment_count = self.env['simulab.experiment'].sudo().search_count([])
        simulab_quizes_count = self.env['experiment.quiz'].sudo().search_count([('school_id', '=',None)])

        values={'active_teachers':active_teachers, 'active_classes':active_classes,'simulab_course_count':simulab_course_count,
                'simulab_experiment_count':simulab_experiment_count,'simulab_quizes_count':simulab_quizes_count,
                'student_count':student_count,'quizes_count':len(quizes_list), 'school_id':school.id}

        if school_dashboard:
            school_dashboard.write(values)
        else:
            self.env['simulab.homepage'].create(values)

        return True

    def teacher_dashboard_count(self, active_c, student_c):
        logged_user = self.env.user
        teacher_ids = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
        teacher_id = teacher_ids.id
        active_classes = active_c
        student_count = student_c
        
        if teacher_id and logged_user.simulab_user=='teacher':
            query = "SELECT class_id FROM school_class_rel WHERE teacher_id = %s"
        
            self._cr.execute(query, (teacher_id,))
        
            result = self._cr.fetchall()
        
            class_ids = [row[0] for row in result]
            
            class_idss = self.env['school.standard'].search([
                            ('id', 'in', class_ids),
                            ('active', '=', True)])
                            
            active_class_ids = class_idss.ids
            
            query = "SELECT student_id FROM class_student_rel WHERE class_id IN %s"
                   
            self._cr.execute(query, (tuple(active_class_ids),))
            result = self._cr.fetchall()
            student_ids = [row[0] for row in result]

    
        return {'active_classes':len(class_idss), 'student_count':len(student_ids)}

