# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from datetime import datetime

class SimulabCourseViews(models.Model):
    _name = 'simulab.course.view'
    _description = 'Course Views'
    _rec_name = 'course_id'
    _order = 'view_count'


    course_id = fields.Many2one('simulab.course', string="Simulab Course", required=True)
    desc = fields.Html('Description')
    view_count = fields.Integer("Views")

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,desc, display_name, parent_id{id,name,desc}}'
        return fields


class SimulabCourseViewLines(models.Model):
    _name = 'simulab.course.view.line'
    _description = 'Course View Lines'
    _rec_name = 'course_id'
    _order = 'course_id, write_date desc'

    @api.depends('student_id', 'teacher_id')
    def _compute_name(self):
        for record in self:
            if record.student_id:
                record.name = record.student_id.name
                record.who_viewed = "Student"
            elif record.teacher_id:
                record.name = record.teacher_id.name
                record.who_viewed = "Teacher"

    student_id = fields.Many2one('student.student', string="Student")
    teacher_id = fields.Many2one('school.teacher', string="Techer")
    name = fields.Char('Viewer', compute='_compute_name', store=True)
    who_viewed = fields.Char('Viewer Type', compute='_compute_name', store=True)

    course_id = fields.Many2one('simulab.course',  string="Course")

    write_date = fields.Datetime("Latest View Date")
    create_date = fields.Datetime(string="View Date")

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,who_viewed,student_id{id,name}, teacher_id{id,name}, course_id{id,name}}'
        return fields

    @api.model
    def create(self, values):
        student_id=values.get('student_id', False)
        teacher_id=values.get('teacher_id', False)
        course_id=values.get('course_id', False)
        if not course_id:
            return

        if not ( student_id or teacher_id ):
            return

        who_viewed= 'student_id' if student_id else 'teacher_id'
        who_viewed_id= student_id if student_id else teacher_id

        #WHERE datetime BETWEEN '2009-10-20 00:00:00' AND '2009-10-20 23:59:59'
        from_date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        to_date=datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

        time_format='%Y-%m-%d %H:%M:%S'
        views = self.search([('course_id','=',course_id),(who_viewed,'=',who_viewed_id),('create_date','>=',from_date.strftime(time_format)),('create_date','<=',to_date.strftime(time_format)) ])
        if views:
            views[0].write({'write_date':datetime.now()})
            return views[0]

        line_view = super().create(values)
        return line_view
