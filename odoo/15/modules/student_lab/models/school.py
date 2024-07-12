# See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")


def emailvalidation(email):
    """Check valid email."""
    if email:
        email_regex = re.compile(EM)
        if not email_regex.match(email):
            raise ValidationError(_("Invalid email-id. Please enter correct email-id!"))


class SimulabStateCity(models.Model):
    _name = 'res.city'
    _description = 'City'
    _order = 'name'

    name = fields.Char("Name", required=True, translate=True)
    zipcode = fields.Char("Pin Code")
    state_id = fields.Many2one(
        'res.country.state', 'State', domain="[('country_id', '=', country_id)]", required=True)
    country_id = fields.Many2one('res.country', string='Country')

    @api.model
    def search_records(self, args, offset=0, limit=None, order=None, count=False):
        res = super().search(args, offset, limit, order, count)
        if request.simulab_rest_api:
            other = self.search([('name', '=', 'Other')])
            if other:
                all_ids = []
                for r in res:
                    all_ids = all_ids + [r.id]
                if other[0].id not in all_ids:
                    all_ids = all_ids + [other[0].id]
                    res = self.search([('id', 'in', all_ids)])

            return {'return_data_as_record_set': True, 'records': res, 'model': self}
        return res

    def name_get(self):
        res = []
        for city in self:
            name = city.name if not city.zipcode else '%s (%s)' % (city.name, city.zipcode)
            res.append((city.id, name))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not (name == '' and operator == 'ilike'):
            args += ['|', (self._rec_name, operator, name), ('zipcode', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    _sql_constraints = [
        ('name_pin_uniq', 'unique(name, zipcode)',
         'City and Pin Combination should be unique!')
    ]

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not 'country_id' in res:
            res['country_id'] = 104
        return res

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, zipcode, state_id{id,name}, country_id{id,name}}'
        return fields


class StandardDivision(models.Model):
    '''Defining a division(A, B, C) related to standard'''

    _name = "standard.division"
    _description = "Class Sections"
    _order = "school_id"

    name = fields.Char('Name', required=True,
                       help='Division of the standard')
    description = fields.Text('Description', help='Description')

    school_id = fields.Many2one('simulab.school', 'School', required=True,
                                help='School of the standard')

    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True)

    active = fields.Boolean('Active', default=True)

    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super().search(args, offset, limit, order, count)
        return res

    @api.model
    def default_get(self, fields):
        logged_user = self.env.user
        school_id = self.env['simulab.school'].search(
            [('company_id', '=', int(logged_user.company_id.id))])
        res = super().default_get(fields)
        if school_id:
            school_id = school_id[0].id
        else:
            school_id = False
        res.update({'school_id': school_id})
        return res

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, description, school_id{id,name}}'
        return fields


class StandardStandard(models.Model):
    '''Defining Standard Information.'''

    _name = 'standard.standard'
    _description = 'Standard Information'
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True,
                              help='Sequence of the record')
    name = fields.Char('Name', required=True,
                       help='Standard name')
    code = fields.Char('Code',
                       help='Code of standard')
    description = fields.Text('Description', help='Description')

    @api.model
    def next_standard(self, sequence):
        '''This method check sequence of standard'''
        stand_rec = self.search([('sequence', '>', sequence)], order='id',
                                limit=1)
        return stand_rec.id or False

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id, sequence, name, code, description}'
        return fields


class SchoolStandard(models.Model):
    '''Defining a standard related to school.'''

    _name = 'school.standard'
    _description = 'School Classes'
    _rec_name = "name"

    def compute_teachers(self):
        '''Compute teachers '''
        teacher_obj = self.env['school.teacher']
        for rec in self:
            rec_id = rec._origin.id if isinstance(rec.id, models.NewId) else rec.id
            if not rec_id:
                continue
            query = "select teacher_id from school_class_rel where class_id=%s " % rec_id
            self._cr.execute(query)
            query_res = self._cr.fetchall()
            query_res = [r[0] for r in query_res]
            rec.write({'teacher_ids': [[6, False, query_res]]})

    def enrol_course(self):
        return True

    @api.model
    def get_classIdName(self, *args):
        name = args[0][0][2]
        school_id = args[0][1][2]
        try:
            standard = self.env['school.standard'].search([('name', '=', name), ('school_id', '=', school_id), ('active', '=', True)])
            if standard:
                result = {
                    'standard_id':standard.id,
                    'class_name':name,
                    'message':'success'
                }
            else:
                result = {
                    'standard_id':False,
                    'message':'No record found'
                }
        except Exception as e:
            print(e)
        return {'result':result, 'http':200}

    @api.depends('student_ids')
    def _compute_total_student(self):
        for rec in self:
            rec.total_students = len(rec.student_ids)

    def update_enrollment_for_students(self, vals):
        if not (vals.get('course_lines', False) or vals.get('student_ids', False)):
            return {'https_status': 200, 'message': 'Nothing to update'}

        if vals.get('student_ids', False):
            if not self.student_ids:
                for enrolled_course in self.course_lines:
                    if not enrolled_course.child_ids:
                        continue
                    enrolled_course.child_ids.write({'active', False})
                return {'https_status': 200, 'message': 'Updated sucessfully'}


        super().write({'course_enrollment_update':True})
        return {'https_status': 200, 'message': 'Update for Course Enrollment added successfully.'}

    def update_enrollment_for_students_in_background(self):
        import time
        obj = time.gmtime(0)
        epoch = time.asctime(obj)
        start_time = round(time.time()*1000)

        _logger.info("\nprocess update_enrollment_for_students_in_background startd for: class- "+self.name +" and school- " +self.school_id.name)

        sms_students = []
        super().write({'course_enrollment_update':False})
        self._cr.commit()
        enrolled_object = self.env['enrolled.course']

        for line in self.course_lines:
            if line.student_id:
                continue

            child_enrollment_ids = []
            stu_count=0
            for student in self.student_ids:
                context = {}
                context.update(self.env.context)
                context.update({'active_test': False, 'enrolment_view': False})
                stu_count=stu_count+1

                enrolled_course = enrolled_object.with_context(**context).search(
                    [('student_id', '=', student.id), ('class_id', '=', self.id),
                     ('course_id', '=', line.course_id.id), ('school_id', '=', self.school_id.id)])

                if enrolled_course:
                    enrolled_course = enrolled_course[0]
                    if not enrolled_course.active:
                        sms_students = sms_students + [(enrolled_course.student_id, enrolled_course)]
                    enrolled_course.write({'active': True})
                    child_enrollment_ids = child_enrollment_ids + [enrolled_course]
                    _logger.info(str(stu_count)+"/"+str(len(self.student_ids))+ " Enrollment exists for student: "+ student.name+" for the course: "+enrolled_course.name)
                else:
                    new_enrolment = line.copy()
                    new_enrolment.write({'student_id': student.id, 'active': True})
                    new_enrolment._cr.commit()
                    _logger.info(str(stu_count)+"/"+str(len(self.student_ids))+ " Enrollment created for student: "+ student.name+" for the course: "+new_enrolment.name)
                    child_enrollment_ids = child_enrollment_ids + [new_enrolment]
                    sms_students = sms_students + [(student, new_enrolment)]

            context = {}
            context.update(self.env.context)
            context.update({'active_test': False, 'enrolment_view': False})
            all_enrolments = enrolled_object.with_context(**context).search(
                [('owner_id', '!=', False), ('course_id', '=', line.course_id.id),
                 ('school_id', '=', self.school_id.id), ('class_id', '=', self.id)])

            available_students = [st.student_id for st in child_enrollment_ids]
            child_ids = [course.id for course in child_enrollment_ids]

            for st in all_enrolments:
                if st.student_id not in available_students:
                    st.write({'active': False})
            line.write({'child_ids': [(6, 0, child_ids)]})

            stu_count=0
            student_experiments_obj = self.env['student.experiment']
            for student_line in child_enrollment_ids:
                stu_count=stu_count+1
                res = student_experiments_obj.search(
                    [('student_id', '=', student_line.student_id.id),
                     ('master_experiment', '=', False),
                     ('enrolled_course_id', '=', student_line.id),
                     ('experiment_id', 'in', [exp.id for exp in student_line.course_id.experiment_ids])])
                _logger.info("Processing create_student_experiments for student: "+str(stu_count)+"/"+str(len(child_enrollment_ids))+" Course: "+student_line.course_id.name+", for student"+student_line.student_id.name)
                if res and len(res)==len(student_line.course_id.experiment_ids):
                    _logger.info("Experiments for the student: "+student_line.student_id.name+" aready created: "+student_line.course_id.name)
                    continue
                student_line.create_student_experiments()

            #create experiment for master course
            line.create_student_experiments()

        notification_obj = self.env['simulab.notification']
        stu_count=0
        for stu in sms_students:
            student = stu[0]
            course = stu[1]
            course_name = course.name
            class_name = course.class_id.name
            stu_name = student.name
            notification_obj.create_course_enrolled_by_school_notification_to_student(student, course_name, class_name)
            stu_count=stu_count+1
            _logger.info("Processing create_course_enrolled_by_school_notification_to_student for student: "+str(stu_count)+"/"+str(len(sms_students)))

        _logger.info("\nprocess update_enrollment_for_students_in_background completed for: class- "+self.name +" and school- " +self.school_id.name)
        obj = time.gmtime(0)
        epoch = time.asctime(obj)
        end_time = round(time.time()*1000)

        _logger.info("Processing time(Secs): "+str((end_time-start_time)/1000))
        return {'https_status': 200, 'message': 'Updated successfully'}

    date_start = fields.Date('Start Date', required=True,
                             help='Starting date of academic year')
    date_stop = fields.Date('End Date', required=True,
                            help='Ending of academic year')

    school_id = fields.Many2one('simulab.school', 'School', required=True,
                                help='School of the following standard')
    standard_id = fields.Many2one('standard.standard', 'Class',
                                  required=True, help='Section')
    division_id = fields.Many2one('standard.division', 'Section',
                                  required=True, help='Standard division')
    user_id = fields.Many2one('school.teacher', 'Class Teacher',
                              help='Teacher of the standard')

    student_ids = fields.Many2many('student.student', 'class_student_rel', 'class_id', 'student_id',
                                   'Class Students')

    teacher_ids = fields.Many2many('school.teacher', 'school_class_rel',
                                   'class_id', 'teacher_id',
                                   'Assigned Classes',
                                   help='Standard for which the teacher\
                                  responsible for')

    course_lines = fields.One2many('enrolled.course', 'class_id',
                                   'Enrolled Courses',
                                   help='Class enrolled to courses'
                                   )

    color = fields.Integer('Color Index', help='Index of color')

    name = fields.Char('Name', compute="_compute_name", store=True)
    total_students = fields.Integer("Total Students",
                                    compute="_compute_total_student",
                                    store=True,
                                    help='Total students of the standard')
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this teacher''')

    exams_id = fields.Many2one('student.exams', "Preparing For")
    simulab_id = fields.Char('Simulab Id', readonly=1)
    active = fields.Boolean('Active', default=True)

    course_enrollment_update = fields.Boolean('Course Enrollment Update', default=False)

    @api.depends('standard_id', 'division_id')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.standard_id.name + '[' + rec.division_id.name + ']'

    def write(self, values):

        student_ids = values.get('student_ids', False)
        add_student_ids = []
        if student_ids:
            for student_id in student_ids[0][2]:
                if self.student_ids:
                    # Check is student already present in the class
                    student = next((student for student in self.student_ids if student.id == student_id), None)
                    if not student:
                        new_student = self.env['student.student'].browse(student_id)
                        add_student_ids.append(new_student)
                else:
                    new_student = self.env['student.student'].browse(student_id)
                    add_student_ids.append(new_student)

        teacher_ids = values.get('teacher_ids', False)
        add_teacher_ids = []
        if teacher_ids:
            for teacher_id in teacher_ids[0][2]:
                if self.teacher_ids:
                    # Check is teacher already present in the class
                    teacher = next((teacher for teacher in self.teacher_ids if teacher.id == teacher_id), None)
                    if not teacher:
                        new_teacher = self.env['school.teacher'].browse(teacher_id)
                        add_teacher_ids.append(new_teacher)
                else:
                    new_teacher = self.env['school.teacher'].browse(teacher_id)
                    add_teacher_ids.append(new_teacher)

        course_lines = values.get('course_lines', False)
        if course_lines:
            courses = values.get('course_lines', False)
            for line in courses:
                if isinstance(line[1], str) and 'virtual' in line[1]:
                    line[2]['school_id'] = self.school_id.id

        res = super().write(values)

        if add_student_ids:
            notification_obj = self.env['simulab.notification']
            for student in add_student_ids:
                notification_obj.create_student_class_assignment_notification(student, self)

        self.update_enrollment_for_students(values)

        if add_teacher_ids:
            notification_obj = self.env['simulab.notification']
            for teacher in add_teacher_ids:
                notification_obj.create_teacher_class_assignment_notification(teacher, self)

        return res

    @api.model
    def create(self, vals):
        logged_user = self.env.user
        school_id = vals.get('school_id', False)
        if not school_id:
            school_id = self.env['simulab.school'].search(
                [('company_id', '=', int(logged_user.company_id.id))])
            if school_id:
                school_id = school_id[0].id
                vals['school_id'] = school_id
        if not school_id:
            raise UserError(_("School is required to add an class"))

        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school.class')
        class_id = super().create(vals)
        class_id.update_enrollment_for_students(vals)
        #self.env['simulab.homepage'].refresh_school_dashboard(self.env['simulab.school'].browse(school_id))
        return class_id

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, exams_id{id,name},school_id{id,name}, standard_id{id,name}, division_id{id,name}, user_id{id,name}, total_students, student_ids{id,name,mobile,email},' \
                 'teacher_ids{id,name,mobile,email,department_id{id,name}}, course_lines{enrolled_experiments{id,sequence, exp_id,planned_start_date,planned_end_date,completion_days}, id,enrolled_count,purchased_count,expired,planned_start_date,course_id{experiment_lines{experiment_id, sequence},id,members_count,name,grade_id{id,name},subject_id{id,name},learning_details,trial_package,price,discounted_price,subscription_period,price_valid_date,price_desc,sequence,description, user_id{id,name}, nbr_quiz, total_experiments,total_time,marks_ids{id,name},members_count, image_url, experiment_ids{id,sequence,completion_days,name, simulation_name,image_url,subject_id{id,name}, marks_ids{id,name}, completion_time, description}}, ' \
                 'price,purchased_price,purchased_date,is_purchased,trial_package,price_valid_date},date_start,date_stop}'
        return fields

    @api.constrains('standard_id', 'division_id')
    def check_standard_unique(self):
        """Method to check unique standard."""
        standard_search = self.env['school.standard'].search([
            ('standard_id', '=', self.standard_id.id),
            ('division_id', '=', self.division_id.id),
            ('school_id', '=', self.school_id.id),
            ('id', 'not in', self.ids)])
        if standard_search:
            raise ValidationError(_("Section and class should be unique!"))

    def unlink(self):
        return super().unlink()

    def get_classes(self, params={}):
        context = {}
        context.update(self.env.context)
        context.update({'enrolment_view': 'school_class_view'})
        search_term = []
        if self.id:
            search_term = [('id', '=', self.id)]
        classes = self.with_context(**context).search(search_term)
        return {'return_data_as_record_set': True, 'records': classes, 'model': self.env['school.standard']}


class SubjectSubject(models.Model):
    '''Defining a subject '''
    _name = "subject.subject"
    _description = "Subjects"

    name = fields.Char('Name', required=True, help='Subject name')
    code = fields.Char('Code', help='Subject code')
    description = fields.Char('Description', help='About Subject')

    stream = fields.Selection([
        ('iit_stream', 'IIT Stream'),
        ('neet_stream', 'NEET Stream'),
        ('both', 'IIT/NEET Stream')])

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,code, description, stream}'
        return fields


class Department(models.Model):
    _name = "school.department"
    _description = "Department"
    _order = "name"

    name = fields.Char('Department Name', required=True)
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, note, active, color}'
        return fields


class StudentExams(models.Model):
    _name = "student.exams"
    _description = "Competitive Exams"
    _order = "name"

    name = fields.Char('Exam Name', required=True)
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,note}'
        return fields


class EducationBoards(models.Model):
    _name = "edu.boards"
    _description = "Education Boards"
    _order = "name"

    name = fields.Char('Education Board', required=True)
    active = fields.Boolean('Active', default=True)
    state_id = fields.Many2one(
        'res.country.state', string="State", domain="[('country_id', '=?', country_id)]"
    )
    country_id = fields.Many2one('res.country', string='Country')

    note = fields.Text('Note')
    
    #SUBODH:: add new medium field in the board
    #mediums = fields.One2many('edu.medium', 'board_ids', string="Mediums")
    medium_ids = fields.Many2many(
        'edu.medium', 'board_medium', 'board_id', 'medium_id',
        string="Education Mediums",
        help="Education mediums associated with this board."
    )

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, country_id{id,name}, state_id{id,name}, note}'
        return fields

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not 'country_id' in res:
            res['country_id'] = 104
        return res

    @api.model
    def search_records(self, args, offset=0, limit=None, order=None, count=False):
        res = super().search(args, offset, limit, order, count)
        if request.simulab_rest_api:
            other = self.search([('name', '=', 'Other')])
            if other:
                all_ids = []
                for r in res:
                    all_ids = all_ids + [r.id]
                if other[0].id not in all_ids:
                    all_ids = all_ids + [other[0].id]
                    res = self.search([('id', 'in', all_ids)])

            return {'return_data_as_record_set': True, 'records': res, 'model': self}
        return res


class StudentInstitutions(models.Model):
    _name = "student.institute"
    _description = "Student Institutions"
    _order = "name"

    name = fields.Char('Institute', required=True)
    active = fields.Boolean('Active', default=True)

    state_id = fields.Many2one(
        'res.country.state', string="State",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one('res.country', string='Country', default=104)

    res_city = fields.Many2one("res.city", string="City",
                               domain="[('state_id', '=', state_id)]")

    zipcode = fields.Char("Pin Code")
    address = fields.Char('Address')

    contact_person = fields.Char('Contact Person')
    contact_no = fields.Char('Mobile No')
    note = fields.Text('Note')

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, country_id{id,name}, state_id{id,name}, res_city{id,name}, zipcode, address, contact_person, contact_no, note}'
        return fields

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not 'country_id' in res:
            res['country_id'] = 104
        return res

    @api.model
    def search_records(self, args, offset=0, limit=None, order=None, count=False):
        res = super().search(args, offset, limit, order, count)
        if request.simulab_rest_api:
            other = self.search([('name', '=', 'Other')])
            if other:
                all_ids = []
                for r in res:
                    all_ids = all_ids + [r.id]
                if other[0].id not in all_ids:
                    all_ids = all_ids + [other[0].id]
                    res = self.search([('id', 'in', all_ids)])

            return {'return_data_as_record_set': True, 'records': res, 'model': self}
        return res


class StudentExamMarks(models.Model):
    _name = "student.exams.marks"
    _description = "Competitive Exams Marks"
    _order = "name"

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Note')
    color = fields.Integer('Color Index')
    exam_id = fields.Many2one('student.exams', string='Exam', required=True)

    marks = fields.Integer("Marks")
    year = fields.Integer("Year")

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,marks,year}'
        return fields

class EducationMedium(models.Model):
    _name = "edu.medium"
    _description = "Education Mediums"
    _order = "name"

    name = fields.Char('Medium', required=True)
    active = fields.Boolean('Active', default=True)
    board_ids = fields.Many2many(
        'edu.boards', 'board_medium', 'medium_id', 'board_id',
        string="Education Boards",
        help="Education boards associated with this medium."
    )
    
    _sql_constraints = [
        ('edu_medium_unique_name', 'unique(name)', 'Medium name must be unique!'),
    ]    
    
   
