# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, tools, _
from odoo.tools import is_html_empty
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

class SimulabCoursesExperiments(models.Model):
    _name = 'simulab.experiment.line'
    _description = 'Simulab Course Experiment Line'
    _order = 'sequence, id'

    experiment_id = fields.Many2one("simulab.experiment", string='Experiment', required=True)
    sequence = fields.Integer(default=10, help='Display order')
    name = fields.Char(related='experiment_id.name', store=True)
    simulation_name = fields.Char(related='experiment_id.simulation_name', store=True)
    exp_id = fields.Integer(related='experiment_id.id', store=True)

    grade_id = fields.Many2one('standard.standard', related='experiment_id.grade_id', store=True)
    subject_id = fields.Many2one('subject.subject', related='experiment_id.subject_id', store=True)
    completion_time = fields.Float(related='experiment_id.completion_time', store=True)
    course_id = fields.Many2one("simulab.course", string='Simulab Course')

class SimulabCourses(models.Model):
    _name = 'simulab.course'
    _description = 'Simulab Course'
    _order = 'id desc'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'image.mixin',
    ]

    @api.model
    def fields_get_queried_keys(self):
        fields ='{id,name,is_subscribed,is_enrolled,simulab_quizes_count,simulab_views,grade_id{id,name},subject_id{id,name},learning_details,trial_package,price,discounted_price,subscription_period,price_valid_date,price_desc,' \
                'sequence,description, user_id{id,name}, nbr_quiz, total_experiments,total_time,marks_ids{id,name},' \
                'members_count, image_url, experiment_lines{experiment_id, sequence}, experiment_ids{id,sequence,name, simulation_name,image_url,subject_id{id,name}, marks_ids{id,name}, completion_time, description}}'
        return fields

    grade_id = fields.Many2one('standard.standard', string='Grade', required=True)
    subject_id = fields.Many2one('subject.subject', string='Subject', required=True)
    trial_package = fields.Boolean(string='Trial Package', default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True)
    price=fields.Monetary("Price", currency_field='company_currency')
    discounted_price=fields.Monetary("Offer Price", currency_field='company_currency')
    price_valid_date=fields.Date("Subscription Valid Till", help='Access to Simulation is valid till date.')
    price_desc=fields.Char("Note")
    validity_days = fields.Integer('Subscription Validity(In Days)',  help='Access to this course is valid for number of  days from the date of purchase.')
    subscription_period=fields.Char("Subscription Validity", compute="_compute_subscription", store=True)

    # description
    name = fields.Char('Name', translate=True, required=True)
    sequence = fields.Integer(default=10, help='Display order')

    active = fields.Boolean(default=True, tracking=100)
    description = fields.Html('Description', translate=True, help="The description that is displayed on top of the course page, just below the title")
    description_short = fields.Html('Short Description', translate=True, help="The description that is displayed on the course card")
    description_html = fields.Html('Detailed Description', translate=tools.html_translate, sanitize_attributes=False, sanitize_form=False)
    learning_details = fields.Html('What you will learn', translate=True, help="Point by details of learning from this course")

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid)
    color = fields.Integer('Color Index', default=0, help='Used to decorate kanban view')
    tag_ids = fields.Many2many(
        'simulab.course.tag', 'simulab_course_tag_rel', 'course_id', 'tag_id',
        string='Tags', help='Used to categorize and filter displayed courses')
    experiment_ids = fields.Many2many('simulab.experiment', 'simulab_experiment_rel','course_id', 'experiment_id', string="Simulab Experiments")
    experiment_lines = fields.One2many('simulab.experiment.line', 'course_id', string="Simulab Experiments")

    nbr_quiz = fields.Integer("Number of Quizs", compute='_compute_slides_statistics', store=True)
    total_experiments = fields.Integer('Experiments', compute='_compute_slides_statistics', store=True)
    total_time = fields.Float('Duration', compute='_compute_slides_statistics', digits=(10, 2), store=True)
    members_count = fields.Integer('Enrolled Student', compute_sudo=True, store=True)
    is_published = fields.Boolean(string="Publish", default=False)  # make the inherited field copyable

    simulab_quizes_count = fields.Integer(string="Simulab Quizes Count", store=True, readonly=True)
    simulab_views = fields.Integer(string="Simulab Views", store=True, readonly=True)

    simulab_id = fields.Char('Simulab Id', readonly=1)

    marks_ids = fields.Many2many(
        'student.exams.marks', 'exam_marks_simulab_course_rel', 'exam_id', 'course_id', string='Marks')


    image_url = fields.Char('Course Image Url', compute='_compute_course_image_url', compute_sudo=False, readonly=1, store=True)


    purchased_count = fields.Integer("Purchased Count",store=True, readonly=True,
                                 help='Total students who has purchased in this class')

    is_subscribed = fields.Boolean("Is Subscribed", compute='_compute_course_status', store=False, default=False)
    is_enrolled = fields.Boolean("Is Enrolled", compute='_compute_course_status', store=False, default=False)
    
    medium_id = fields.Many2one('edu.medium', string="Education Medium", required=True)    
    parent_id = fields.Many2one('simulab.course', string='Parent Course', optional=True)


    def _compute_course_status(self):
        user = self.env.user
        student_ids = self.env['student.student'].search([('user_id','=',user.id)])
        student_id=False
        if student_ids:
            student_id=student_ids[0].id
        for record in self:
            subscribed=record.env['enrolled.course'].search_count([('student_id','=',student_id),('course_id','=',record.id),('is_purchased','=',True)])
            record.is_subscribed=False
            record.is_enrolled=False
            if subscribed>0:
                record.is_subscribed=True
                record.is_enrolled=True
                continue
            enrolled=record.env['enrolled.course'].search_count([('student_id','=',student_id),('course_id','=',record.id)])
            if enrolled>0:
                record.is_enrolled=True


    def compute_simulab_course_stat(self):
        for record in self:
            purchased_count=record.env['enrolled.course'].search_count([('child_ids','=',False),('course_id','=',record.id),('is_purchased','=',True)])
            members_count=record.env['enrolled.course'].search_count([('child_ids','=',False),('course_id', '=', record.id)])
            views = self.env['simulab.course.view.line'].search_count([('course_id','=',record.id)])

            quizes_list=[]
            for exp in record.experiment_ids:
                for quiz in exp.quiz_ids:
                    if quiz.school_id:
                        continue
                    if quiz not in quizes_list:
                        quizes_list = quizes_list+[quiz]
            record.update_record({'simulab_quizes_count':len(quizes_list),'simulab_views':views, 'members_count':members_count, 'purchased_count':purchased_count})


    def simulab_courses(self, params={'subject_id':'phy'}):
        search_term=[]
        for p in params.keys():
            search_term=search_term+[(p,'ilike',params[p])]

        courses = self.env['simulab.course'].search(search_term)
        return {'return_data_as_record_set': True, 'records': courses,
                'model': self.env['simulab.course']}

    @api.depends('price_valid_date', 'validity_days')
    def _compute_subscription(self):
        for record in self:
            record.subscription_period=''
            if not record.price_valid_date and not record.validity_days>0:
                continue
            if record.validity_days>0:
                record.subscription_period= str(record.validity_days)+ ' days from date of purchase.'
                continue
            if record.price_valid_date:
                validity=record.price_valid_date.strftime('%d/%m/%Y')
                record.subscription_period= 'Subscription valid till '+ validity

    @api.depends('image_1920')
    def _compute_course_image_url(self):
        for record in self:
            record.image_url=False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=simulab.course&id=' + str(record.id) + '&field=image_1024'

    def unlink(self):
        super().unlink()

    def _compute_slide_last_update(self):
        for record in self:
            record.slide_last_update = fields.Date.today()

    def _compute_rating_stats(self):
        for record in self:
            record.rating_avg_stars = 0

    def compute_views_count(self):
        for record in self:
            views = self.env['simulab.course.view.line'].search_count([('course_id','=',record.id)])
            record.update_record({'simulab_views':views})

    def compute_quiz_count(self):
        for record in self:
            quizes_list=[]
            for exp in record.experiment_ids:
                for quiz in exp.quiz_ids:
                    if quiz.school_id:
                        continue
                    if quiz not in quizes_list:
                        quizes_list = quizes_list+[quiz]
                        record.update_record({'simulab_quizes_count':len(quizes_list)})

    def action_publish(self):
        if not self.price_valid_date and not self.validity_days:
            raise UserError(_("Please update valid subscription period for this course."))
        self.write({'is_published':True})

    def action_published(self):
        return True

    def _compute_members_done_count(self):
        for channel in self:
            channel.members_done_count = 0

    def _compute_is_member(self):
        for channel in self:
            channel.is_member = False

    @api.depends('experiment_ids','parent_id','medium_id')
    def _compute_slides_statistics(self):
        for record in self:
            record.total_experiments= len(record.experiment_ids)
            total_time=0.0
            for experiment in record.experiment_ids:
                total_time=total_time+experiment.completion_time
            record.total_time=total_time
        return True

    def _compute_user_statistics(self):
        return True


    def action_count_members(self):
        return True


    def action_view_experiments(self):
        return True

    @api.model
    def create(self, vals):
        if not is_html_empty(vals.get('description')) and  is_html_empty(vals.get('description_short')):
            vals['description_short'] = vals['description']

        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.courses')
        channel = super().create(vals)
        channel.update_experiment_ids(vals)
        return channel

    def write(self, vals):
        if not is_html_empty(vals.get('description')) and is_html_empty(vals.get('description_short')) and self.description == self.description_short:
            vals['description_short'] = vals.get('description')

        res = super().write(vals)
        self.update_experiment_ids(vals)
        return res

    def rebuild_course_images(self):
        courses = self.env['simulab.course'].sudo().search([])
        for course in courses:
            course._compute_course_image_url()
            for exp in course.experiment_ids:
                exp._compute_exp_image_url()
                for fun in exp.fun_fcts:
                    fun._compute_exp_image_url()
                for sim in exp.simulation_stories:
                    sim._compute_exp_image_url()
                for fun in exp.theory_details:
                    fun._compute_exp_image_url()
                for fun in exp.theory_techniques:
                    fun._compute_exp_image_url()

    def build_experiment_lines(self):
        for rec in self:
            exp_lines = []
            line_exp = [line.experiment_id for line in rec.experiment_lines]
            i = 0
            for exp in rec.experiment_ids:
                if exp in line_exp:
                    i=i+1
                    continue
                exp_lines = exp_lines + [exp]
            if not exp_lines:
                continue

            experiment_lines = []
            for line in exp_lines:
                i = i + 1
                experiment_lines = experiment_lines + [
                    [0, 0, {'experiment_id': line.id, 'sequence': i, 'course_id':rec.id}]]
            rec.update_record({'experiment_lines':experiment_lines})

    def update_experiment_ids(self, vals):
        experiment_lines = vals.get('experiment_lines', False)
        if experiment_lines:
            line_exps = [line.experiment_id.id for line in self.experiment_lines]
            self.update_record({'experiment_ids': [[6, False, line_exps]]})

    def get_simulab_courses(self, params={}):
        course_id = params.get("course_id", False)
        course_type = params.get("course_type", "all")
        
        medium_id = False   
        course_experiment_lines = False

        args = [('id','=',course_id)] if course_id else []       
        if 'current_medium_id' in request.session:
            medium_id = int(request.session['current_medium_id'])
            if medium_id != 1:
                args = [('parent_id','=',course_id)] if course_id else []
                args.append(('medium_id', '=', medium_id))
                #simulab_courses = self.env['simulab.course'].search(args)
            else:
                args.append(('medium_id', '=', medium_id))
                #simulab_courses = self.env['simulab.course'].search(args)
                
        simulab_courses = self.env['simulab.course'].search(args)

        logged_user = params.get("user_id", self.env.user.id)
        student_ids = self.env['student.student'].search([('user_id', '=', logged_user)])
        student_ids = [student.id for student in student_ids]
        enrolled_courses = {}
        if student_ids:
            course_clause= ""
            if course_id:
                course_clause = " and course_id="+str(course_id)
            where = "where student_id = " + str(student_ids[0])+course_clause
            if len(student_ids) > 1:
                where = "where student_id in " + str(student_ids[0])+course_clause
            query = "select id, course_id, is_purchased,name, owner_id, owner, sku_id from enrolled_course " + where
            self._cr.execute(query)
            enrolled_courses = self._cr.fetchall()
            enrolled_courses = {en[1]: (en[0], en[2], en[3], en[4], en[5], en[6]) for en in enrolled_courses}

        enrolled = []
        purchased_course = []
        others = []
        line_details = {}
        for course in simulab_courses:            
            if medium_id and medium_id != 1:
                find_course_id = course.parent_id.id
            else:
                find_course_id = course.id
            if course_type=="enrolled":
                if course.id not in enrolled_courses.keys():
                    continue

            marks_ids = []
            for mark in course.marks_ids:
                marks_ids = marks_ids + [{"id": mark.id, "name": mark.name}]
                
            totalExperiments =  course.total_experiments
            totalTime =  course.total_time
            membersCount =  course.members_count
            #SUBODH Added for getting count of parent course experiment   
            if medium_id and medium_id != 1:
                if course.parent_id:
                    totalExperiments =  course.parent_id.total_experiments
                    totalTime =  course.parent_id.total_time
                    membersCount =  course.parent_id.members_count
                
            enrolled_course = {}
            if find_course_id in enrolled_courses.keys():
                is_enrolled = True
                enrolled_id = enrolled_courses[find_course_id][0]
                is_subscribed = enrolled_courses[find_course_id][1]
                owner_id=enrolled_courses[find_course_id][3]
                skuId=enrolled_courses[find_course_id][5]
                enrolled_course = {"isEnrolled": is_enrolled, "isPurchased": is_subscribed,"skuId":skuId,
                                   "enrolledId": enrolled_id, "owner":enrolled_courses[find_course_id][4]}
                if owner_id:
                    enrolled_course["ownerId"]=owner_id
                
            course_details = {"id": find_course_id, "name": course.name,
                              "simulabQuizesCount": course.simulab_quizes_count,
                              "simulabViews": course.simulab_views,
                              "gradeId": {"id": course.grade_id.id, "name": course.grade_id.name},
                              "subjectId": {"id": course.subject_id.id,
                                             "name": course.subject_id.name},
                              "learningDetails": course.learning_details, "price": course.price,
                              "discountedPrice": course.discounted_price,
                              "trialPackage": course.trial_package,
                              "subscriptionPeriod": course.subscription_period,
                              "sequence": course.sequence,
                              "description": course.description,
                              "totalExperiments": totalExperiments,
                              "totalTime": totalTime,
                              "membersCount": membersCount, 
                              "imageUrl": course.image_url,
                              "marksIds": marks_ids}

            course_details.update(enrolled_course)
            if course_id:
                experiments = []
                student_experiments={}
                if course_id in enrolled_courses.keys():
                    enrolled_id = enrolled_courses[course_id][0]
                    is_subscribed = enrolled_courses[course_id][1]
                    if is_subscribed:
                        student_experiments = self.env['student.experiment'].search(
                            [('enrolled_course_id', '=', enrolled_id)])
                        student_experiments = {student_exp.exp_id: {
                            "studentExperimentId": student_exp.id,
                            "status": student_exp.status,
                            "simulationProgress": student_exp.simulation_progress,
                            "plannedStartDate": student_exp.planned_start_date,
                            "plannedEndDate": student_exp.planned_end_date}
                            for student_exp in student_experiments}
                #experiments = course.experiment_lines   
                course_experiment_lines = course.experiment_lines
                #SUBODH:: For specific course id and medium get course experiment lines
                if medium_id and medium_id !=1:
                    course_experiment_lines = course.parent_id.experiment_lines
                                        
                for line in course_experiment_lines:
                    marks_ids = []
                    for mark in line.experiment_id.marks_ids:
                        marks_ids = marks_ids + [{"id": mark.id, "name": mark.name}]

                    studentExperiment = {}
                   
                    if line.experiment_id.id in student_experiments: 
                        studentExperiment = student_experiments[line.experiment_id.id]

                    line_details = {"id": line.experiment_id.id, "name": line.experiment_id.name,
                                    "sequence": line.sequence,
                                    "simulationName": line.experiment_id.simulation_name,
                                    "imageUrl": line.experiment_id.image_url,
                                    "marksIds": marks_ids,
                                    "completionTime": line.experiment_id.completion_time,
                                    "description": line.experiment_id.description }

                    line_details.update(studentExperiment)
                    experiments = experiments + [line_details]
                    
                    if experiments:
                        if medium_id and medium_id != 1:
                            for experiment in experiments:                            
                                experiment_id = experiment["id"]
                                child_experiment = self.env['simulab.experiment'].search(
                                     [ ('parent_id', '=', experiment_id), ('medium_id', '=', medium_id)])  
                                if child_experiment.exists():
                                    experiment['name'] = child_experiment.name
                                    experiment['description'] = child_experiment.description
                                    experiment['imageUrl'] = child_experiment.image_url
                       
                
                course_details["simulabExperiments"] = experiments               
    
            if enrolled_course.get('isSubscribed', False):
                purchased_course = purchased_course + [course_details]
            elif enrolled_course.get('isEnrolled', False):
                enrolled = enrolled + [course_details]
            else:
                others = others + [course_details]

        result = purchased_course + enrolled + others
        if course_id:
            if result:
                return result[0]
        return {"simulabCourseList":result}
    
    @api.model
    def get_courses(self, args):
        subject_id = args['subject_id']
        grade_id = args['grade_id']
        course_list = self.env['simulab.course'].search([('subject_id', '=', subject_id), ('grade_id', '=', grade_id)])
        return {'return_data_as_record_set': True, 'records': course_list,
                'model': self.env['simulab.course']}
