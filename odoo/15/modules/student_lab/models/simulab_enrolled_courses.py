# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,  _
from datetime import date, timedelta, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError

EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")
import logging
_logger = logging.getLogger(__name__)

class StudentExperimentMileStone(models.Model):
    _name = 'experiment.milestone'
    _description = 'Experiments MileStone'
    _rec_name = "name"

    name = fields.Char('Name')
    description = fields.Char('Description')
    sequence = fields.Integer('Sequence')


class SimulabEnrolledCourses(models.Model):
    _name = 'enrolled.course'
    _description = 'Simulab Enrollment Courses'
    _rec_name = "name"
    _order = 'write_date desc'

    @api.onchange('course_id')
    def _compute_speical_price(self):
        for rec in self:
            if not rec.course_id:
                continue
            rec.purchased_price = rec.discounted_price
            rec.special_price_desc = False
            school_id = self.env.context.get('school_id', False)
            class_id = self.env.context.get('class_id', False)
            if not school_id:
                continue
            res = self.env['school.course.price'].search(
                [('school_id', '=', school_id),
                 ('course_id', '=', rec.course_id.id)])
            if res:
                rec.purchased_price = res[0].school_price
                rec.special_price_desc = 'Special Price for ' + res.school_id.name

    @api.depends('purchased_date')
    def _compute_subscription(self):
        for record in self:
            record.price_valid_date = ''
            if not record.course_id.price_valid_date and not record.course_id.validity_days > 0:
                continue
            expiry_date = False
            if record.course_id.validity_days > 0 and record.purchased_date:
                expiry_date = record.purchased_date + timedelta(days=record.course_id.validity_days)
            elif record.purchased_date:
                expiry_date = record.course_id.price_valid_date
            record.price_valid_date = expiry_date

    name = fields.Char('Name', related='course_id.name', store=True)
    course_id = fields.Many2one('simulab.course', 'Course', required=True)
    class_id = fields.Many2one('school.standard', string="Class", store=True)
    trial_package = fields.Boolean(readonly=1, related='course_id.trial_package', store=True)

    school_id = fields.Many2one('simulab.school', 'School',
                                help='School which enrolled this package')
    student_id = fields.Many2one('student.student', help='Student which enrolled this package')
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this Student''')

    owner = fields.Char('Owner', compute='_compute_owner_string', store=True)
    owner_id = fields.Many2one('enrolled.course', string='School Enrolled Course', index=True,
                               copy=False, ondelete='cascade')
    child_ids = fields.One2many('enrolled.course', 'owner_id', string='Student Enrolled Course',
                                help="Student Enrolled courses provided by School", copy=False)

    enrolled_experiments = fields.One2many('student.experiment', 'enrolled_course_id',
                                           string='Student Enrolled Experiments',
                                           help="Student Enrolled Experiments", copy=False)

    purchased_date = fields.Date("Purchased Date")
    is_purchased = fields.Boolean(default=False, string="Is Purchased", copy=False)

    price_valid_date = fields.Date("Subscription Valid Till", compute="_compute_subscription", store=True,
                                   help='Access to Simulation is valid till date.')
    subscription_period = fields.Char("Subscription Validity", related='course_id.subscription_period', store=True)

    price = fields.Monetary("Price", currency_field='company_currency',
                            related='course_id.price', readonly=1, store=True)
    discounted_price = fields.Monetary(currency_field='company_currency',
                                       related='course_id.discounted_price', readonly=1,
                                       store=True)
    special_price_desc = fields.Char(string="Special Price", compute='_compute_speical_price',
                                     store=True, readonly=True)
    purchased_price = fields.Monetary("Special Price", currency_field='company_currency')
    price_desc = fields.Char(readonly=1, related='course_id.price_desc', store=True)

    total_price = fields.Monetary("Class Price", currency_field='company_currency',
                                  compute='_compute_bulk_price', store=True,
                                  help='Price for whole class students', copy=False)

    total_purchased = fields.Integer(related="course_id.purchased_count")

    company_currency = fields.Many2one("res.currency", string='Currency',
                                       related='company_id.currency_id', readonly=True)

    active = fields.Boolean('Active', default=True)
    simulab_id = fields.Char('Simulab Id', readonly=1, copy=False)

    count_exp_completed = fields.Integer('Experiment Completed')
    count_exp_in_progress = fields.Integer('Experiment in Progress')
    count_exp_not_started = fields.Integer('Experiment not Started')
    total_exp_count = fields.Integer('Experiment Count')

    enrolled_count = fields.Integer(string='Enrolled Count', compute='_compute_enrolled_stats', store=True,
                                    help="Enrolled Count in given class", copy=False)
    purchased_count = fields.Integer(string='Purchased Count', compute='_compute_enrolled_stats', store=True,
                                     help="Purchased Count in given class", copy=False)

    sku_id = fields.Char('SKU Id', copy=False, help="In app purchase price id for this product")

    subscription_ids = fields.One2many('simulab.subscription', 'course_id', string='Transactions',
                                       help="Transactions done for this course", copy=False)

    expired = fields.Boolean('Expired', default=False,copy=False, store=True)

    planned_start_date = fields.Date("Planned Start Date", copy=False)
    purchase_reminder_sent = fields.Boolean("Purchase reminder sent", default=False, copy=False)
    create_date = fields.Datetime(string="View Date")

    def update_enrolled_course_expiry(self):
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        courses = self.search([('expired','=', False), ('price_valid_date','<',today)])
        if courses:
            courses.write({'expired':True})
            
        again_purchased_course = self.search([('expired', '=', True), ('price_valid_date', '>', today)])
        if again_purchased_course:
            again_purchased_course.write({'expired':False})

    def update_enrolled_stats(self):
        self._compute_enrolled_stats()
        self.update_record()

    @api.depends('child_ids', 'is_purchased')
    def _compute_enrolled_stats(self):
        for record in self:
            purchased_count = 0
            record.enrolled_count = len(record.child_ids) if record.child_ids else 1
            for child in record.child_ids:
                if child.is_purchased:
                    purchased_count = purchased_count + 1

            if purchased_count == 0:
                if record.is_purchased:
                    purchased_count = 1
            record.purchased_count = purchased_count
            if record.child_ids:
                if record.enrolled_count != record.purchased_count:
                    record.is_purchased = False

    def update_experiment_stats(self):
        count_exp_completed = 0
        count_exp_in_progress = 0
        count_exp_not_started = 0
        experiment_ids = self.env['student.experiment'].search([('enrolled_course_id', '=', self.id)])
        for exp in experiment_ids:
            if exp.simulation_progress == 100:
                count_exp_completed = count_exp_completed + 1
            elif exp.simulation_progress > 0 and exp.simulation_progress < 100:
                count_exp_in_progress = count_exp_in_progress + 1
            else:
                count_exp_not_started = count_exp_not_started + 1
        total_exp_count = count_exp_completed + count_exp_in_progress + count_exp_not_started
        super().write({'count_exp_completed': count_exp_completed, 'count_exp_in_progress': count_exp_in_progress,
                       'count_exp_not_started': count_exp_not_started, 'total_exp_count': total_exp_count})

    def buy_now(self):
        self.write({'is_purchased': True, 'purchased_date': datetime.today()})


    def write_in_batch(self, vals):
        res = super().write(vals)
        return res

    def set_experiment_due_dates(self, vals={}):
        experiment_ids = [exp for exp in self.enrolled_experiments]
        experiment_ids.sort(key=lambda x: (x.sequence))

        if not self.is_purchased:
            return {"http_status":200, "message":"Course must be purchased for experiment dates to be updated."}

        days_count = 0
        if vals.get('planned_start_date', False):
            planned_start_date = datetime.strptime(vals.get('planned_start_date', False), "%d-%m-%Y")
        else:
            planned_start_date= self.purchased_date

        if not planned_start_date:
            return {"http_status":200, "message":"Could not updated planned start date. Either purchase date is missing or date is not provided."}

        self.write({'planned_start_date':planned_start_date.strftime('%Y-%m-%d')})
        experiments_due_dates={}
        for experiment in experiment_ids:
            if experiment.planned_start_date and experiment.planned_end_date and not vals.get('planned_start_date', False):
                continue

            planned_start_date = planned_start_date + timedelta(days=days_count)
            days_count = vals.get(str(experiment.id), False) or experiment.completion_days
            days_count=days_count-1
            end_date = planned_start_date + timedelta(days=days_count)
            days_count=days_count+1
            experiments_due_dates[experiment.experiment_id] ={'planned_start_date':planned_start_date.strftime('%Y-%m-%d'), 'end_date':end_date.strftime('%Y-%m-%d')}
            experiment.write({'planned_start_date':planned_start_date.strftime('%Y-%m-%d'), 'planned_end_date':end_date.strftime('%Y-%m-%d'),
                              'completion_days': vals.get(str(experiment.id), False) or experiment.completion_days})
            self._cr.commit()
        if self.active and self.is_purchased and self.enrolled_experiments:
            for student_exp in self.enrolled_experiments:
                if student_exp.planned_start_date and student_exp.planned_end_date and not vals.get('planned_start_date', False):
                    continue
                student_exp.write(
                        {'planned_start_date': experiments_due_dates[student_exp.experiment_id]['planned_start_date'],
                         'planned_end_date': experiments_due_dates[student_exp.experiment_id]['end_date']})
                self._cr.commit()
        for child_course in self.child_ids:
            if child_course.active and child_course.is_purchased and child_course.enrolled_experiments:
                for student_exp in child_course.enrolled_experiments:
                    if student_exp.planned_start_date and student_exp.planned_end_date and not vals.get('planned_start_date', False):
                        continue

                    student_exp.write(
                        {'planned_start_date': experiments_due_dates[student_exp.experiment_id]['planned_start_date'],
                         'planned_end_date': experiments_due_dates[student_exp.experiment_id]['end_date']})
                    self._cr.commit()
        return {"http_status":200, "message":"Successfully updated start and end dates"}

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_purchased', False):
            purchase_params = {'is_purchased': True, 'purchased_date': vals.get('purchased_date', datetime.today())}
            super().write(purchase_params)
            if self.child_ids:
                notification_obj = self.env['simulab.notification']
                purchased_childs = []
                for child_course in self.child_ids:
                    if child_course.active and not child_course.is_purchased:
                        purchased_childs.append(child_course)

                self.child_ids.write_in_batch(purchase_params)

                for child in purchased_childs:                    
                    res = self.call_get_new_subscription(child)
                    notification_obj.create_bulk_buy_notification_to_student(child) #SUBODH:: Commented for Buy Now option in My Enrolled Courses

        return res

    def student_purchase_count(self):
        return True

    @api.depends('owner_id')
    def _compute_owner_string(self):
        for line in self:
            line.owner = line.school_id.name if line.owner_id else "Self"

    @api.model
    def fields_get_queried_keys(self):
        fields = '{expired,enrolled_count,purchased_count,class_id{id,name,standard_id{id,name},division_id{id,name}},id,sku_id,purchased_price,special_price_desc,total_exp_count,count_exp_completed,count_exp_in_progress,count_exp_not_started,enrolled_experiments{id,sequence, name, exp_id, simulation_progress, simulation_time, simulation_days, simulation_quiz_score, simulation_milestone, enrolled_course_id{id,name,course_id{id,name,experiment_lines{exp_id,sequence,name, simulation_name},experiment_ids{id,sequence,name, simulation_name}}}},school_id{id,name},owner,student_id{id,name},is_purchased,course_id{id,name,grade_id{id,name},subject_id{id,name},learning_details,trial_package,price,discounted_price,subscription_period,price_valid_date,price_desc,sequence,description, user_id{id,name}, nbr_quiz, total_experiments,total_time,marks_ids{id,name},members_count, image_url, experiment_ids{id,sequence,name, simulation_name,image_url,subject_id{id,name}, marks_ids{id,name}, completion_time, description}}}'
        return fields

    def search(self, args, offset=0, limit=None, order=None, count=False):
        view_type = self.env.context.get('enrolment_view', False)
        if view_type and view_type == 'school_class_view':
            args = args + [('owner_id', '=', False)]
        res = super().search(args, offset, limit, order, count)
        return res

    @api.depends('purchased_price', 'discounted_price', 'child_ids')
    def _compute_bulk_price(self):
        for line in self:
            if line.trial_package:
                line.total_price = 0
                continue

            discounted_price = line.discounted_price
            if discounted_price > line.purchased_price:
                discounted_price = line.purchased_price
            line.total_price = len(line.child_ids) * discounted_price

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        return res

    @api.model
    def create(self, vals):
        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school.courses')
        res = super().create(vals)

        if res.course_id.trial_package:
            res.buy_now()
            self.env['simulab.subscription'].create_subscription(res.id)
        else:
            if res.school_id and res.purchased_price > 0 and res.discounted_price > res.purchased_price:
                sku_id = str(res.course_id.id) + "-COURSE-" + str(res.school_id.id) + "-SCH-SKU"
            else:
                sku_id = str(res.course_id.id) + "-COURSE-SKU"
            res.write({"sku_id": sku_id})

        return res

    def get_school_purchased_courses(self, params=[]):
        params = params + [('is_purchased', '=', True), ('student_id', '=', False)]

        logged_user = self.env.user
        teacher_id = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
        if teacher_id:
            params = params+[('school_id', '=', teacher_id.school_id.id)]

        enrolled_courses = self.env['enrolled.course'].search(params)        
        return {'return_data_as_record_set': True, 'records': enrolled_courses,
                'model': self.env['enrolled.course']}

    def get_school_enrolled_courses(self, params=[]):
        params = params + [('is_purchased', '=', False), ('student_id', '=', False)]

        logged_user = self.env.user
        teacher_id = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
        if teacher_id:
            params = params+[('school_id', '=', teacher_id.school_id.id)]

        enrolled_courses = self.env['enrolled.course'].search(params)
        return {'return_data_as_record_set': True, 'records': enrolled_courses,
                'model': self.env['enrolled.course']}

    def get_all_school_enrolled_courses(self, params=[]):
        params = params + [[('student_id', '=', False)]]

        logged_user = self.env.user
        teacher_id = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
        if teacher_id:
            params = params+[('school_id', '=', teacher_id.school_id.id)]

        enrolled_courses = self.env['enrolled.course'].search(params)
        return {'return_data_as_record_set': True, 'records': enrolled_courses,
                'model': self.env['enrolled.course']}

    def get_all_school_student_enrolled_courses(self, params={}):
        search_term = [('student_id', '!=', False)]
        if params:
            search_term = params

        logged_user = self.env.user
        teacher_id = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
        if teacher_id:
            search_term = search_term+[('school_id', '=', teacher_id.school_id.id)]
        enrolled_courses = self.env['enrolled.course'].search(search_term)

        return {'return_data_as_record_set': True, 'records': enrolled_courses,
                'model': self.env['enrolled.course']}
        
    def student_completed_courses(self, *args):
        student_id = args[0][2]
        completed_course = self.env['enrolled.course'].search([('student_id', '=', student_id), ('active', '=', True), ('school_id', '!=', 'NULL'), ('count_exp_completed', '>', 0), ('expired', '=', False)])
        return {'return_data_as_record_set': True, 'records': completed_course,
                'model': self.env['enrolled.course']}
        
    def student_ongoing_courses(self, *args):
        student_id = args[0][2]
        inprogress_courses = self.env['enrolled.course'].search([('student_id', '=', student_id), ('active', '=', True), ('school_id', '!=', 'NULL'), ('count_exp_in_progress', '>', 0), ('expired', '=', False)])
        return {'return_data_as_record_set': True, 'records': inprogress_courses,
                'model': self.env['enrolled.course']}
        
    def enroll_student(self, vals):
        course_id = vals.get('course_id', False)
        class_id = vals.get('class_id', False)

        logged_user = self.env.user
        student_ids = self.env['student.student'].sudo().search([('user_id', '=', logged_user.id)])
        if not student_ids:
            return False
        student = student_ids[0]
        enrolled_object = self.env['enrolled.course']
        context = {}
        context.update(self.env.context)
        context.update({'active_test': False, 'enrolment_view': False})

        if class_id:
            search = [('student_id', '=', student.id),
                      ('course_id', '=', course_id), ('class_id', '=', class_id)]
        else:
            search = [('student_id', '=', student.id),
                      ('course_id', '=', course_id)]

        enrolled_course = False
        enrolled_courses = enrolled_object.with_context(**context).search(search)
        for c in enrolled_courses:
            if not class_id and c.class_id:
                continue
            enrolled_course = c
            break


        if enrolled_course:
            if enrolled_course.active:
                return self.env['simulab.course'].get_simulab_courses({'course_id': course_id})
            else:
                enrolled_course.write({'active': True})
                return self.env['simulab.course'].get_simulab_courses({'course_id': course_id})

        if not vals.get('student_id', False):
            vals['student_id']=student.id

        if 'school_id' not in vals:
            vals['company_id'] = int(self.env['ir.config_parameter'].sudo().get_param('default.student.company'))
        enrolled_course = self.create(vals)
        self.create_student_experiments(enrolled_course)

        return self.env['simulab.course'].get_simulab_courses({'course_id': course_id})

    def create_student_experiments(self, student_enrolment_line=False):
        if not student_enrolment_line:
            student_enrolment_line=self

        master_experiment=False
        if not student_enrolment_line.student_id.id:
            master_experiment=True

        name= student_enrolment_line.student_id.name if student_enrolment_line.student_id else "parent course"

        student_experiments_obj = self.env['student.experiment']
        for experiment in student_enrolment_line.course_id.experiment_lines:
            res = student_experiments_obj.search(
                [('student_id', '=', student_enrolment_line.student_id.id),
                 ('master_experiment', '=', master_experiment),
                 ('enrolled_course_id', '=', student_enrolment_line.id),
                 ('experiment_id', '=', experiment.experiment_id.id)])
            if res:
                _logger.info("Experiment for the student: "+name+" aready created: "+experiment.name)
                continue
            vals={'master_experiment':master_experiment, 'student_id': student_enrolment_line.student_id.id,
                  'sequence': experiment.sequence,'completion_days':experiment.experiment_id.completion_days,
                  'enrolled_course_id': student_enrolment_line.id, 'experiment_id': experiment.experiment_id.id}

            student_exp = student_experiments_obj.create(vals)
            if student_exp.quiz_ids:
                continue
            _logger.info("Experiment created for the student: "+name+", "+experiment.name)

            quiz_ids = [quiz.id for quiz in experiment.experiment_id.quiz_ids]
            student_quizzes=[]
            i=0
            for quiz in quiz_ids:
                i=i+1
                student_quizzes = student_quizzes+[(0,0,{'sequence':i,'quiz_id':quiz, 'student_experiment_id':student_exp.id})]
            student_exp.write({'quiz_ids': student_quizzes})
            student_exp._cr.commit()
            _logger.info("Quiz created created for the student: "+name+" for the exp "+experiment.name)

    def purchase_reminder_email_for_enrolled_courses(self, upcoming_days=-30):

        end_date = date.today() + timedelta(days= upcoming_days)
        end_date = end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        res = self.search([('is_purchased','=',False),('trial_package','=',False),('child_ids','=',[]),
                           ('create_date','<=',end_date),('purchase_reminder_sent','=',False)])

        student_courses={}
        for r in res:
            if r.student_id in student_courses.keys():
                student_courses[r.student_id]=student_courses[r.student_id]+[r]
            else:
                student_courses[r.student_id]=[r]

        notification_obj = self.env['simulab.notification']
        for student in student_courses.keys():
            notification_obj.create_enrolled_course_purchase_reminder(student, student_courses[student])

        return True
        
    def call_get_new_subscription(self, child_course):        
        subscription_obj = self.env['simulab.subscription']        
        price = child_course.price
        discounted_price = child_course.discounted_price
        course_display_name = str(child_course.display_name)
        enrolled_course_id = child_course.id        
        course_id = child_course.course_id.id       
        school_id = child_course.school_id.id  
        currency = child_course.company_currency.display_name
        
        server_pre_response = { "amount": price * 100, "discounted_price": discounted_price * 100, "currency": currency,"notes": {"enrolled_course_id": str(enrolled_course_id),"course_name":course_display_name ,"course_id": str(course_id),"school_id":school_id, "school": str(child_course.school_id.name if child_course.school_id else child_course.student_id.name if child_course.student_id else ""),}}
        params = {"payment_status":"success","payment_source":"offline_payment","course_id":child_course.id,"payment_order_id":child_course.simulab_id,"server_pre_response":str(server_pre_response),"server_post_response":""}
        res = subscription_obj.get_new_subscription(params)
        #print(res)
        return res    
    
    @api.model
    def expired_courses(self, args):
        class_id = args[2]
        records = self.env['enrolled.course'].search([('class_id', '=', class_id), ('expired', '=', True), ('is_purchased', '=', True)])
        distinct_records = []
        seen_names = set()
        for record in records:
            if record.name not in seen_names:
                distinct_records.append(record)
                seen_names.add(record.name)
        return {'return_data_as_record_set': True, 'records': distinct_records,
                'model': self.env['enrolled.course']}

class SchoolClassCoursePrice(models.Model):
    _name = 'school.course.price'
    _description = 'School Course Price'
    _rec_name = "name"

    school_id = fields.Many2one('simulab.school', 'School',
                                help='School which purchased this package')
    name = fields.Char('Name', related='school_id.name', store=True)
    course_id = fields.Many2one('simulab.course', 'Course')
    class_id = fields.Many2one('standard.standard', string="Grade",
                               related="course_id.grade_id")

    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this School''')
    company_currency = fields.Many2one("res.currency", string='Currency',
                                       related='company_id.currency_id', readonly=True)
    price = fields.Monetary("Price", currency_field='company_currency',
                            related='course_id.price', readonly=1, store=True)
    discounted_price = fields.Monetary(currency_field='company_currency',
                                       related='course_id.discounted_price', readonly=1,
                                       store=True)
    school_price = fields.Monetary("Price for Institute", currency_field='company_currency')
    price_valid_date = fields.Date(readonly=1, related='course_id.price_valid_date', store=True)
    simulab_id = fields.Char('Simulab Id', readonly=1)
    _sql_constraints = [
        ('school_id_course_id_uniq', 'unique(course_id, school_id)',
         'Price for selected Course and School Combination already exists!')
    ]

    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super().search(args, offset, limit, order, count)
        return res

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,course_id{id,name},class_id{id,name},price,discounted_price,school_price,price_valid_date,school_id{id,name}}'
        return fields

    @api.model
    def create(self, vals):
        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school.prices')
        res = super().create(vals)
        return res


class SimulabStudentExperiments(models.Model):
    _name = 'student.experiment'
    _description = 'Simulab Enrollment Course Experiments'
    _rec_name = "name"
    _order ="write_date desc"

    _inherit = [
        'simulab.notification',
    ]

    sequence = fields.Integer(default=1, help='Display order')
    student_id = fields.Many2one('student.student', string="Student")
    enrolled_course_id = fields.Many2one('enrolled.course', 'Enrolled Course', required=True)
    experiment_id = fields.Many2one('simulab.experiment', string='Experiment', required=True)
    exp_id = fields.Integer(related='experiment_id.id', store=True)

    name = fields.Char('Name', related='experiment_id.name', store=True)
    course_id = fields.Many2one('simulab.course', related='enrolled_course_id.course_id',
                                store=True)
    class_id = fields.Many2one('school.standard', related='enrolled_course_id.class_id', store=True)

    quiz_ids = fields.One2many('student.experiment.quiz', 'student_experiment_id', string='Student Experiment Quizes',
                               copy=False)

    school_id = fields.Many2one('simulab.school', related='enrolled_course_id.school_id',
                                help='School which enrolled this package', store=True)
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this Student''')

    status = fields.Selection(
        [('new', 'New'), ('started', 'Started'), ('in_progress', 'In Progress'),
         ('completed', 'Completed')],
        help='Select Experiment Status', default='new')

    active = fields.Boolean('Active', default=True)
    simulab_id = fields.Char('Simulab Id', readonly=1, copy=False)

    simulation_progress = fields.Float('Simulation Progress(%)', digits=(10, 2))
    simulation_time = fields.Float('Simulation Time(Min.)', digits=(10, 2))
    simulation_days = fields.Float('Simulation Days', digits=(10, 2))
    simulation_quiz_score = fields.Float('Simulation Quiz Scores', digits=(10, 2))
    simulation_milestone = fields.Integer(string="Simulation MileStone")

    simulation_ini_file = fields.Many2one('dms.file', string="Simulation JSON File")
    exp_setting_sound = fields.Boolean('Experiment Sound', default=True)

    planned_start_date = fields.Datetime("Planned Start Date")
    planned_end_date = fields.Datetime("Planned End Date")

    actual_start_date = fields.Datetime("Actual Start Date")
    actual_end_date = fields.Datetime("Actual End Date")

    master_experiment = fields.Boolean('Master Experiment', default=False, help='This experiment belongs to class enrolled course')
    completion_days = fields.Integer('Experiment Completion in Days',  help='No of days by when experiment should be completed from scheduled date.')

    reminder_email_sent = fields.Boolean('Reminder Email', default=False, help="Reminder email for upcoming experiment due date")

    _sql_constraints = [
        ('enrolled_course_id_experiment_id_unique', 'unique(enrolled_course_id, experiment_id)',
         'Same experiment can not be added more than once in one enrolled course!')
    ]

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id, simulation_progress, sequence, simulation_time, simulation_days, simulation_milestone, simulation_ini_file, student_id{id,name},course_id{id,name,tag_ids{id,name}}, experiment_id{id,name,sequence,tag_ids{id,name},completion_time,user_id{id,name},grade_id{id,name},subject_id{id,name},preview,summary,objective,description}}'
        return fields

    @api.onchange('enrolled_course_id')
    def _onchange_standard_id(self):
        for rec in self:
            experiment_id = False
            if rec.enrolled_course_id:
                allowed_exp_ids = [exp.id for exp in
                                   rec.enrolled_course_id.course_id.experiment_ids]
                return {'domain': {'experiment_id': [('id', 'in', allowed_exp_ids)]}}

    @api.model
    def create(self, vals):
        enrolled_course_id=vals['enrolled_course_id']
        experiment_id=vals['experiment_id']
        student_experiment_id = self.search([('experiment_id','=',experiment_id),('enrolled_course_id','=',enrolled_course_id)])
        if student_experiment_id:
            student_experiment_id[0].write(vals)
            return student_experiment_id[0]

        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('enrolled.course.experiment')
        student_id = vals.get('student_id',False)
        if not student_id:
            master_experiment = vals.get('master_experiment',False)
            if not master_experiment:
                raise ValidationError(
                    _('Student ID needed for all the enrolled courses other than the master enrolled course.'))
        res = super().create(vals)
        return res

    def write(self, values):
        simulation_progress = values.get("simulation_progress", False)
        if simulation_progress and isinstance(simulation_progress, str):
            try:
                simulation_progress = float(simulation_progress)
            except Exception:
                simulation_progress=False
                values['actual_start_date'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        if simulation_progress and not self.actual_start_date:
            values['actual_start_date'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        if simulation_progress and simulation_progress >= 100.0:
            values['actual_end_date'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        res = super().write(values)
        if values.get('simulation_ini_file', False):
            if self.student_id:
                company_id = self.student_id.user_id.company_id
                simulation_ini_file=self.simulation_ini_file
                if simulation_ini_file.company_id.id != company_id.id:
                    simulation_ini_file.write({'company_id':company_id.id})
        if 'simulation_progress' in values:
            self.enrolled_course_id.update_experiment_stats()

        if not self.student_id and not self.master_experiment:
            raise ValidationError(
                _('Student ID needed for all the enrolled courses other than the master enrolled course.'))
        return res

    def get_experiment_file(self, vals={}):
        student_experiment_id = vals.get('student_experiment_id', False)
        student_id = vals.get('student_id', False)
        extension = vals.get('file_ext', "json")
        file_id = vals.get('fileId', False)
        if file_id:
            exp_file = self.env['dms.file'].sudo().browse(file_id)
            return {"fileId": exp_file.id, "content": exp_file.content, "name":exp_file.name}
        else:
            base_directory = self.env.ref('dms.directory_root_student_experiments').id
            base_directory = self.env['dms.directory'].sudo().browse(base_directory)
            student_directory = self.env['dms.directory'].sudo().search(
            [('name', '=', str(student_id)), ('parent_id', '=', base_directory.id)])
            if not student_directory:
                return {"https_status": 200,
                        "message": "Could not fine requested file"}

            file_name = str(student_experiment_id) + '.' + extension
            experiment_file = self.env['dms.file'].sudo().search(
                [('name', '=', file_name), ('directory_id', '=', student_directory.id)])
            if not experiment_file:
                return {"https_status": 200,
                        "message": "Could not fine requested file"}
            return {"fileId": experiment_file.id, "content": experiment_file.content, "name":experiment_file.name}


    def add_experiment_file(self, vals={}):
        student_experiment_id = vals.get('student_experiment_id', False)
        student_id = vals.get('student_id', False)
        extension = vals.get('file_ext', "json")
        content = vals.get('content', False)

        if not (student_experiment_id and student_id):
            return {"https_status": 200,
                    "message": "Experiment Id and Student Id are required to process the request"}

        base_directory = self.env.ref('dms.directory_root_student_experiments').id
        base_directory = self.env['dms.directory'].sudo().browse(base_directory)
        student_directory = self.env['dms.directory'].sudo().search(
            [('name', '=', str(student_id)), ('parent_id', '=', base_directory.id)])
        if not student_directory:
            student_directory = self.env['dms.directory'].sudo().create(
                {'name': str(student_id), 'parent_id': base_directory.id})

        file_name = str(student_experiment_id) + '.' + extension
        experiment_file = self.env['dms.file'].sudo().search(
            [('name', '=', file_name), ('directory_id', '=', student_directory.id)])
        vals = {'name': file_name, 'directory_id': student_directory.id, 'extension': extension}
        if content:
            vals['content'] = content

        file_created=False
        if not experiment_file:
            file_created=True
            experiment_file = self.env['dms.file'].sudo().create(vals)
            self.browse(student_experiment_id).sudo().write({'simulation_ini_file': experiment_file.id})
        else:
            experiment_file.sudo().write(vals)

        message = ("Succesfully created file- "+file_name) if file_created else ("Succesfully updated file- "+file_name)
        return {"httpsStatus": 200, "message": message, "fileId":experiment_file.id}

    @api.model
    def create_file(self):
        import requests
        import base64
        session = requests.session()
        with open("/Users/sandeep/Downloads/healthcarePanCard.jpg", "rb") as file:
            binary_content = file.read()
            ImageBase64 = base64.b64encode(binary_content)
            content = ImageBase64.decode('ascii')

        headers = {"Content-Type": "application/json", "Cookie": "session_id=7d44abb3088f48b6f39427ce21f5f8846bfd1cfe"}
        session.headers = headers
        data = {"params": {"name": "Account Statement V1.1.postman_collection.json", "directory_id": 20,
                           "content": content}}
        response = session.post(url="http://localhost:8069/api/dms.file/create", json=data)
        print(response)
        print(response.text)
        return True

    @api.model
    def update_file(self):
        import requests
        import base64
        session = requests.session()
        with open("/Users/sandeep/Downloads/healthcarePanCard.jpg", "rb") as file:
            binary_content = file.read()
            ImageBase64 = base64.b64encode(binary_content)
            content = ImageBase64.decode('ascii')

        headers = {"Content-Type": "application/json", "Cookie": "session_id=7d44abb3088f48b6f39427ce21f5f8846bfd1cfe"}
        session.headers = headers
        data = {"params": {"args": [{"name": "healthcare Pan Card.jpg", "content": content}]}}
        response = session.post(url="http://localhost:8069/api/object/dms.file/7/write", json=data)
        print(response)
        print(response.text)
        return True

    def reminder_email_for_upcoming_experiments(self, upcoming_days=20):
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        end_date = date.today() + timedelta(days=upcoming_days)
        end_date = end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        res = self.search([('enrolled_course_id.is_purchased','=',True),('reminder_email_sent','=',False),
                     ('planned_start_date','>=',today),('planned_start_date','<=',end_date), ('sequence','in',[1,8,15,22,29])])

        student_experiments={}
        for r in res:
            if not r.student_id:
                continue

            if r.student_id in student_experiments.keys():
                student_experiments[r.student_id]=student_experiments[r.student_id]+[r]
            else:
                student_experiments[r.student_id]=[r]
            student_experiments[r.student_id].sort(key=lambda x: (x.sequence))

        notification_obj = self.env['simulab.notification']
        for student in student_experiments.keys():
            notification_obj.create_experiment_deadline_notifications_to_students(student, student_experiments[student])
        return True
