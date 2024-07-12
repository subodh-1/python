# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class SimulabStudentExperimentQuiz(models.Model):
    _name = "student.experiment.quiz"
    _rec_name = "name"
    _description = "Student Experiment Quiz"
    _order = "create_date desc"

    sequence = fields.Integer("Sequence", defualt=1)
    quiz_id = fields.Many2one('experiment.quiz', required=True, ondelete='cascade')
    student_experiment_id = fields.Many2one('student.experiment', required=True, ondelete='cascade')
    class_id = fields.Many2one('school.standard', related='student_experiment_id.class_id', store=True)

    name = fields.Char(related="quiz_id.name", store=True)
    experiment_id = fields.Many2one('simulab.experiment', related="student_experiment_id.experiment_id", store=True)
    student_id = fields.Many2one('student.student', related='student_experiment_id.student_id', store=True)
    student_quiz_question_ids = fields.One2many('student.quiz.question', 'student_quiz_id', string="Questions")

    quiz_completed = fields.Boolean(default=False)
    quiz_status = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'),
         ('completed', 'Completed')],
        help='Select Quiz Status', default='new')

    completion_time = fields.Float(related='quiz_id.completion_time', store=True)
    time_left = fields.Float('Time Left', digits=(10, 4),
                                   help="Time left for this quiz.")

    start_date = fields.Datetime("Planned Start Date")
    end_date = fields.Datetime("Planned End Date")

    marks_obtained = fields.Float(compute="_compute_marks", digits=(6, 2), store=True, default=0.00)
    max_marks_obtained = fields.Float(compute="_compute_marks", digits=(6, 2), store=True, default=0.00)
    av_marks_obtained = fields.Float(compute="_compute_marks", digits=(6, 2), store=True, default=0.00)

    write_date = fields.Datetime()
    create_date = fields.Datetime()

    def correct_experiments_attempt_sequence(self):
        quizzes_query = 'select distinct(quiz_id) from  student_experiment_quiz order by quiz_id'
        self._cr.execute(quizzes_query)
        quizzes_ids = self._cr.fetchall()
        quizzes_ids = [id[0] for id in quizzes_ids]

        students_query = 'select distinct(student_id) from  student_experiment_quiz order by student_id'
        self._cr.execute(students_query)
        students_ids = self._cr.fetchall()
        students_ids = [id[0] for id in students_ids]

        for quiz in quizzes_ids:
            for student in students_ids:
                student_quizzes = self.search([('quiz_id','=',quiz),('student_id','=',student)], order= 'create_date asc, id')
                sequence=0
                for squiz in student_quizzes:
                    sequence=sequence+1
                    squiz.update_record({'sequence':sequence})
                    self._cr.commit()


    def correct_experiments_quiz_start_end_dates(self):
        quizzes_query = 'select id from  student_experiment_quiz where (start_date is null or end_date is null ) order by quiz_id '
        self._cr.execute(quizzes_query)
        quizzes_ids = self._cr.fetchall()
        quizzes_ids = [id[0] for id in quizzes_ids]
        for quiz in self.browse(quizzes_ids):
            val={}
            if quiz.quiz_status=='completed':
                if not quiz.end_date:
                    val['end_date']= quiz.write_date.strftime('%Y-%m-%d %H:%M:%S')
            elif quiz.quiz_status=='in_progress':
                if not quiz.start_date:
                    val['start_date']= quiz.create_date.strftime('%Y-%m-%d %H:%M:%S')
            quiz.update_record(val)

    @api.model
    def create(self, value_list):

        if not isinstance(value_list, list):
            value_list=[value_list]

        for values in value_list:
            quiz_id = values.get('quiz_id')
            student_experiment_id = values.get('student_experiment_id')
            student_quiz_id = self.search([('quiz_id','=',quiz_id),('student_experiment_id','=',student_experiment_id),
                                           ('quiz_status','=',"new")])
            if student_quiz_id:
                student_quiz_id[0].write(values)
                return student_quiz_id[0]

            values['time_left'] = self.env['experiment.quiz'].browse(quiz_id).completion_time
        print("Subodh: Debuggin on ")
        print(value_list)
        return super().create(value_list)

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence,quiz_completed,time_left,completion_time,quiz_status,student_experiment_id{id,name},student_quiz_question_ids{id, time_spent, attempted, student_quiz_answer_ids{answer_id{id,is_correct}},question_id{id,sequence, marks, image_url, question, question_desc, answer_ids{id,text_value, is_correct, comment,image_url},explanation_ids{description,image_url}}}}'
        return fields

    def write(self, values):
        # if self.quiz_status=='completed':
        #     return True

        quiz_id = values.get('quiz_id', False)
        if quiz_id and self.quiz_id.id != quiz_id:
            values['time_left'] = self.env['experiment.quiz'].browse(quiz_id).completion_time

        if values.get('quiz_status', False):
            if self.quiz_status=='completed' and values.get('quiz_status', False) !='completed':
                return True

            if values.get('quiz_status', False) =='completed':
                values['end_date']= datetime.today().strftime('%Y-%m-%d %H:%M:%S')

            elif values.get('quiz_status', False) =='in_progress':
                if not self.start_date:
                    values['start_date']= datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        return super().write(values)

    def _compute_quiz_completion(self):
        for record in self:
            record.quiz_completed = False

    def update_score(self):
        for record in self.search([('quiz_status','=','completed'), ('id', '=', 56682)]):
            marks_obtained=0
            for question in record.student_quiz_question_ids:
                for answer in question.student_quiz_answer_ids:
                    if answer.is_correct or 1:
                        marks_obtained=marks_obtained+question.question_id.marks
            record.update({'marks_obtained':marks_obtained})

    def _compute_marks(self):
        for record in self:
            marks_obtained=0
            for question in record.student_quiz_question_ids:
                for answer in question.student_quiz_answer_ids:
                    if answer.is_correct:
                        marks_obtained=marks_obtained+question.question_id.marks
            record.marks_obtained = marks_obtained

    def update_student_quiz_question_attempted(self, params={}):
        student_quiz_id = params.get('student_quiz_id', False)
        student_quiz_question_id = params.get('student_quiz_question_id', False)
        student_answer_id = params.get('student_answer_id', False)
        quiz_status = params.get('quiz_status', "in_progress")
        time_spent = params.get('time_spent', False)

        if not (student_quiz_id or student_quiz_question_id):
            return {"http_status":200, "message": "Student Quiz or Student Quiz Question was not provided."}

        if self.browse(student_quiz_id).quiz_status=='completed':
           return {"http_status":200, "message": "This quiz is already completed."}

        time_left = params.get('time_left', self.completion_time)
        self.browse(student_quiz_id).write({'quiz_status':quiz_status, 'time_left':time_left})
        self.env['student.quiz.question'].browse(student_quiz_question_id).write({'attempted':True, 'time_spent':time_spent})
        if student_answer_id:
            student_answer_id=self.env['student.quiz.answer'].create({'answer_id':student_answer_id, 'student_question_id':student_quiz_question_id})
            student_answer_id = student_answer_id.id
        return {"http_status":200, "message": "Updated successfully", "student_answer_id":student_answer_id}

    def create_new_student_quiz(self, params={}):
        ret=self.get_attempt_quiz_by_student(params)
        return self.env['experiment.quiz'].get_experiment_quizes(params)

    def get_attempt_quiz_by_student(self, params={}):
        student_id = params.get('student_id', False)
        if not student_id:
            logged_user = self.env.user
            student_ids = self.env['student.student'].search([('user_id', '=', logged_user.id)])
            student_ids = [student.id for student in student_ids]
            if student_ids:
                student_id=student_ids[0]

        student_quiz_id = params.get('student_quiz_id', False)
        if student_quiz_id:
            student_quiz=self.browse(student_quiz_id)
            if not student_quiz.student_quiz_question_ids:
                for question_id in student_quiz.quiz_id.question_ids:
                    student_questions = [question_id.question_id for question_id in student_quiz.student_quiz_question_ids]
                    if question_id not in student_questions:
                        self.env['student.quiz.question'].create({'question_id':question_id.id, 'student_quiz_id':student_quiz.id,
                                                              'student_id':  student_quiz.student_id.id})

            return {'return_data_as_record_set': True, 'records': self.browse(student_quiz_id), 'model': self.env['student.experiment.quiz']}

        quiz_id = params.get('quiz_id', False)
        student_experiment_id = params.get('student_experiment_id', False)

        if not (quiz_id and student_experiment_id):
            return {'return_data_as_record_set': True, 'records': [], 'model': self.env['student.experiment.quiz']}

        quizzes = self.env['student.experiment.quiz'].search([('student_id', '=', student_id), ('quiz_id','=',quiz_id),  ('student_experiment_id','=',student_experiment_id)])
        quiz_to_attempt=False
        for quiz in quizzes:
            if quiz.quiz_status != 'completed':
                quiz_to_attempt=quiz
                break
                
        if not quiz_to_attempt:
            quiz_to_attempt = self.create({'sequence':len(quizzes)+1, 'quiz_id':quiz_id, 'time_left':round(self.env['experiment.quiz'].browse(quiz_id).completion_time,2), 'student_experiment_id':student_experiment_id})
            for question_id in self.env['experiment.quiz'].browse(quiz_id).question_ids:
                student_questions = [question_id.question_id for question_id in quiz_to_attempt.student_quiz_question_ids]
                if question_id not in student_questions:
                    self.env['student.quiz.question'].create({'question_id':question_id.id, 'student_quiz_id':quiz_to_attempt.id,
                                                        'student_id':  student_id})
        for question_id in self.env['experiment.quiz'].browse(quiz_id).question_ids:
            student_questions = [question_id.question_id for question_id in quiz_to_attempt.student_quiz_question_ids]
            if question_id not in student_questions:
                self.env['student.quiz.question'].create({'question_id':question_id.id, 'student_quiz_id':quiz_to_attempt.id,
                                                          'student_id':  student_id})

        return {'return_data_as_record_set': True, 'records': quiz_to_attempt, 'model': self.env['student.experiment.quiz']}

class SimulabExperimentQuiz(models.Model):
    _name = "experiment.quiz"
    _rec_name = "name"
    _description = "Simulab Experiment Quiz"
    _order = "sequence DESC"
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'image.mixin',
    ]

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=experiment.quiz&id=' + str(
                    record.id) + '&field=image_1024'

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence,image_url,students_completed_count,school_completed_count, school_enrolled_count, quiz_completed, name,student_experiment_quizzes{id,sequence,name,quiz_completed, quiz_status, student_experiment_id{id,name}, student_quiz_question_ids{id, student_quiz_answer_ids{answer_id{id,is_correct}}}},school_id{id,name},marks_ids{id,name},experiment_id{id,name},quiz_comment,tag_ids{id,name},question_count,question_comment,completion_time, completion_comment, marks, marks_comment, students_count,student_count_comment,student_instruction,quiz_instruction,question_ids{id,sequence, marks, image_url, question, question_desc, answer_ids{id,text_value, is_correct, comment,image_url},explanation_ids{description,image_url}}}'
        return fields

    sequence = fields.Integer("Sequence")
    name = fields.Char("Name", required=True, translate=True)

    quiz_comment = fields.Char("Quiz Comment", translate=True)
    create_uid = fields.Many2one('res.users')

    question_count = fields.Integer(compute='_compute_question_count')
    question_comment = fields.Char("Question Comment", translate=True)
    completion_time = fields.Float('Duration', digits=(10, 4),
                                   help="The estimated completion time for this quiz")
    completion_comment = fields.Char("Completion Comment", translate=True)
    marks = fields.Integer("Marks")
    marks_comment = fields.Char("Marks Comment", translate=True)

    students_count = fields.Integer(compute='_compute_student_count', store=True)

    student_count_comment = fields.Char("Student Count Comment", translate=True)
    quiz_completed = fields.Boolean(default=False, compute='_compute_quiz_completion', store=True)
    students_completed_count = fields.Integer(compute='_compute_student_count', store=True)

    school_enrolled_count = fields.Integer(compute='_compute_school_enrolled_count')
    school_completed_count = fields.Integer(compute='_compute_school_completed_count')

    student_instruction = fields.Char("Student Instruction", translate=True)
    quiz_instruction = fields.Html('Quiz Instruction', translate=True)
    active = fields.Boolean(default=True, tracking=100)
    date_published = fields.Datetime('Publish Date', readonly=True, tracking=1)
    is_published = fields.Boolean(string="Publish", default=False)
    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=False, readonly=1, store=True)
    quiz_details = fields.Html('Quiz Details', translate=True)

    tag_ids = fields.Many2many('simulab.experiment.tag', 'rel_experiment_quiz_tag', 'quiz_id',
                               'tag_id', string='Tags')
    marks_ids = fields.Many2many(
        'student.exams.marks', 'exam_marks_simulab_quiz_rel', 'exam_id', 'quiz_id', string='Marks')

    question_ids = fields.One2many('quiz.question', 'quiz_id', string="Questions")

    experiment_id = fields.Many2one('simulab.experiment', required=True, ondelete='cascade')
    grade_id = fields.Many2one('standard.standard', related='experiment_id.grade_id', store=True)
    subject_id = fields.Many2one('subject.subject', related='experiment_id.subject_id', store=True)

    school_id = fields.Many2one('simulab.school', string="School")
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True)

    student_experiment_quizzes = fields.One2many('student.experiment.quiz', 'quiz_id', compute='_compute_current_student_quiz')

    simulab_id = fields.Char('Simulab Id', readonly=1)

    def _compute_current_student_quiz(self):
        student_id=False
        logged_user = self.env.user
        student_ids = self.env['student.student'].search([('user_id', '=', logged_user.id)])
        student_ids = [student.id for student in student_ids]
        if student_ids:
            student_id=student_ids[0]
        for quiz in self:
            student_quizess = self.env['student.experiment.quiz'].search([('student_id', '=', student_id),('quiz_id', '=', quiz.id)])
            if student_quizess:
                quiz.student_experiment_quizzes = student_quizess
            else:
                quiz.student_experiment_quizzes = False

    def search(self, args, offset=0, limit=None, order=None, count=False):
        logged_user = self.env.user
        res = super().search(args, offset, limit, order, count)
        return res

    def _compute_school_enrolled_count(self):
        for quiz in self:
            quiz.school_enrolled_count = 0

    def _compute_school_completed_count(self):
        for quiz in self:
            quiz.school_completed_count = 0

    def _compute_student_count(self):
        for quiz in self:
            quiz.students_count = 0
            quiz.students_completed_count = 0

    def compute_student_count(self):
        for quiz in self:
            student_exp = self.env['student.experiment'].search([('experiment_id','=',quiz.experiment_id.id)])
            students_count = len(student_exp)
            student_exp = self.env['student.experiment.quiz'].search([('experiment_id','=',quiz.experiment_id.id), ('quiz_id', '=', quiz.id), ('quiz_status','=','completed')])
            students_completed_count = len(student_exp)
            quiz.write({'students_count':students_count,'students_completed_count':students_completed_count})

    def _compute_question_count(self):
        for quiz in self:
            quiz.question_count = 0

    def _compute_student_completion_count(self):
        for quiz in self:
            quiz.students_completed_count = 0

    def _compute_quiz_completion(self):
        for quiz in self:
            quiz.quiz_completed = 0

    def action_publish(self):
        return True

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        logged_user = self.env.user
        school_id = self.env['simulab.school'].search(
            [('company_id', '=', int(logged_user.company_id.id))])
        if school_id:
            defaults['school_id'] = school_id.id
        return defaults

    @api.model
    def create(self, values):
        school_id = values.get('school_id', False)
        if not school_id:
            logged_user = self.env.user
            school_id = self.env['simulab.school'].search(
                [('company_id', '=', int(logged_user.company_id.id))])
            if school_id:
                values['school_id'] = school_id.id

        school_id = values.get('school_id', False)
        #if school_id:
        #    self.env['simulab.homepage'].refresh_school_dashboard(self.env['simulab.school'].browse(school_id))
        # SUBODH :: Below commented for testing
        #values['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.experiment.quiz')
        #return super().create(values)
        return True

    @api.model
    def add_questions(self, quiz_id, values):
        questions = self.env['quiz.question'].create(values)
        questions = [q.id for q in questions]
        res = {'https_status': 200, 'id': questions}
        return res

    def write(self, values):
        return super().write(values)

    def school_quizzes(self, school_id):
        enrolled_courses = self.env['enrolled.course'].sudo().search([('school_id', '=', school_id)])
        quizes_list = []
        for enrolled_course in enrolled_courses:
            for exp in enrolled_course.course_id.experiment_ids:
                for quiz in exp.quiz_ids:
                    if quiz not in quizes_list:
                        quizes_list = quizes_list + [quiz]

        quiz_ids = [quiz.id for quiz in quizes_list]
        res = super().search_records([('id', 'in', quiz_ids)])
        return res

    def get_experiment_quizes(self, params={}):
        experiment_id = params.get("experiment_id", False)
        student_id = params.get("student_id", False)
        quiz_id = params.get("quiz_id", False)
        school_id = params.get("school_id", False)
        only_simulab_quiz = params.get("only_simulab_quiz", True)
        get_quiz_questions = params.get("get_quiz_questions", False)        
        offset = params.get("offset", 0)
        limit = params.get("limit", 80)
        grade_id = params.get("grade_id", False)
        subject_id = params.get("subject_id", False)
        name = params.get("name", False)

        if quiz_id:
            exp_quizzes = self.browse(quiz_id)
        else:
            search_term=[]
            if experiment_id:
                search_term = search_term+[('experiment_id','=',experiment_id)]
            if grade_id:
                search_term = search_term+[('grade_id','=',grade_id)]
            if subject_id:
                search_term = search_term+[('subject_id','=',subject_id)]
            if name:
                search_term = search_term+[('name','ilike',name)]
            if school_id:
                #search_term = search_term+ ['|',('school_id','=',school_id),(('school_id','=',False))]
                search_term = search_term+ ['|',('school_id','=',school_id),(('company_id','=',school_id))]
            exp_quizzes = self.search(search_term, offset=offset, limit=limit, order=" experiment_id desc, id")

        result = []
        for quiz in exp_quizzes:
            result_val = {"id": quiz.id, "name": quiz.name, "sequence": quiz.sequence,
                          "gradeId": quiz.grade_id.id,
                          "gradeName": quiz.grade_id.name,
                          "subjectId": quiz.subject_id.id,
                          "subjectName": quiz.subject_id.name,
                          "imageUrl": quiz.image_url,
                          "completionTime": quiz.completion_time, "marks": quiz.marks,
                          "quizComment": quiz.quiz_comment,
                          "quizInstruction": quiz.quiz_instruction,
                          "questionCounts": len(quiz.question_ids),
                          "studentsCount": quiz.students_count,
                          "studentsCompletedCount": quiz.students_completed_count,
                          "experimentId": quiz.experiment_id.id,
                          "experimentName": quiz.experiment_id.name                          
                          }

            question_ids=[]
            if get_quiz_questions:
                for question in quiz.question_ids:
                    explanation_ids=[]
                    for explanation in question.explanation_ids:
                        explanation_ids = explanation_ids+[{"id":explanation.id, "description":explanation.description, "imageUrl":explanation.image_url,}]
                    answer_ids=[]
                    for answer in question.answer_ids:
                        answer_ids = answer_ids+[{"id":answer.id,"questionId":question.id, "textValue":answer.text_value, "isCorrect":answer.is_correct,
                                                  "comment":answer.comment, "imageUrl":answer.image_url}]

                    question_ids = question_ids+[{"id":question.id,"marks":question.marks,
                                   "imageUrl":question.image_url,"question": question.question,
                                   "questionDesc": question.question_desc, "answerIds":answer_ids, "explanationIds":explanation_ids}]

                result_val["questionIds"]=question_ids
            if only_simulab_quiz:
                result=result+[result_val]
                continue

            student_quizzes = self.env['student.experiment.quiz'].search([('quiz_id','=',quiz.id), ('student_id','=',student_id)], order="sequence desc")
            stu_quizzes = []
            sequence=0
            for stu_quiz in student_quizzes:
                vals = {
                    "id": stu_quiz.id,
                    "name":quiz.name,
                    "sequence": len(student_quizzes)-sequence,
                    "quizId":quiz.id,
                    "studentExperimentId": stu_quiz.student_experiment_id.id,
                    "experimentId": stu_quiz.experiment_id.id,
                    "quizStatus": stu_quiz.quiz_status,
                    "completionTime": stu_quiz.completion_time,
                    "marksObtained": stu_quiz.marks_obtained,
                    "totalMarks": quiz.marks,
                    "timeLeft":stu_quiz.time_left
                }
                sequence=sequence+1

                if stu_quiz.start_date:
                    vals["startDate"]=stu_quiz.start_date.strftime('%d.%m.%Y %H:%M:%S')
                if stu_quiz.end_date:
                    vals["endDate"]=stu_quiz.end_date.strftime('%d.%m.%Y %H:%M:%S')
                student_quiz_question_ids=[]
                if not stu_quiz.student_quiz_question_ids:
                    r = self.env['student.experiment.quiz'].get_attempt_quiz_by_student({'student_id':student_id,'student_quiz_id': stu_quiz.id})
                    stu_quiz = r['records']
                for student_question in stu_quiz.student_quiz_question_ids:
                    student_quiz_answer_id={}
                    for student_quiz_answer in student_question.student_quiz_answer_ids:
                        student_quiz_answer_id = {"studentAnsId":student_quiz_answer.id, "isCorrect":student_quiz_answer.is_correct, "simulabAnsId":student_quiz_answer.answer_id.id}
                        break
                    student_quiz_answer_id["sequence"]=student_question.sequence
                    student_quiz_answer_id["simulabQuestionId"]=student_question.question_id.id
                    student_quiz_answer_id["studentQuestionId"]=student_question.id
                    student_quiz_answer_id["attempted"]=student_question.attempted
                    student_quiz_answer_id["timeSpent"]=student_question.time_spent
                    student_quiz_question_ids = student_quiz_question_ids +[student_quiz_answer_id]

                vals["studentQuizAnswerIds"]=student_quiz_question_ids
                stu_quizzes = stu_quizzes + [vals]

            result_val["studentExperimentQuizzes"]=stu_quizzes
            result = result+[result_val]
        if quiz_id:
            return result[0]       
        return {"experimentQuizzes":result}

class SimulabExperimentQuizQuestion(models.Model):
    _name = "quiz.question"
    _rec_name = "question_desc"
    _description = "Simulab Experiment Quiz Question"
    _order = "sequence"
    _inherit = [
        'mail.thread',
        'image.mixin',
    ]

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=quiz.question&id=' + str(
                    record.id) + '&field=image_1024'

    sequence = fields.Integer("Sequence")
    marks = fields.Float(string="Marks", digits=(12, 2))
    question = fields.Char("Question Name", required=True, translate=True)
    answer_ids = fields.One2many('quiz.answer', 'question_id', string="Answer")
    explanation_ids = fields.One2many('quiz.image.model', 'question_id', string="Question Explanation")
    quiz_id = fields.Many2one('experiment.quiz', string="Experiment Quiz", required=True,
                              ondelete='cascade')
    question_desc = fields.Html('Question Description', translate=True)
    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=False, readonly=1, store=True)

    # statistics
    attempts_count = fields.Integer(compute='_compute_statistics')
    attempts_avg = fields.Float(compute="_compute_statistics", digits=(6, 2))
    done_count = fields.Integer(compute="_compute_statistics")

    marks_ids = fields.Many2many(
        'student.exams.marks', 'exam_marks_quiz_question_rel', 'exam_id', 'question_id', string='Exam Years')

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence, question, marks, tag_ids{id,name}, answer_ids{id,sequence,text_value,is_correct,comment,image_url},explanation_ids{description,image_url},quiz_id{id,name}, attempts_count, attempts_avg, done_count}'
        return fields

    def _check_answers_integrity(self):
        for question in self:
            if len(question.answer_ids.filtered(lambda answer: answer.is_correct)) != 1:
                raise ValidationError(
                    _('Question "%s" must have 1 correct answer', question.question))
            if len(question.answer_ids) < 2:
                raise ValidationError(
                    _('Question "%s" must have 1 correct answer and at least 1 incorrect answer',
                      question.question))

    def _compute_statistics(self):
        self.attempts_avg = 0
        self.done_count = 0
        self.attempts_count = 0

    @api.model
    def create(self, values):
        return super().create(values)

    def write(self, values):
        return super().write(values)


class SimulabQuizImageModel(models.Model):
    _name = 'quiz.image.model'
    _description = "Quiz answer explanation Object Having Single Image and One Description"
    _inherit = [
        'image.mixin',
    ]

    question_id = fields.Many2one('quiz.question', string="Question", ondelete='cascade')
    answer_id = fields.Many2one('quiz.answer', string="Answer", ondelete='cascade')

    description = fields.Html("Description", translate=True)
    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=True,
                             store=True)

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=quiz.image.model&id=' + str(
                    record.id) + '&field=image_1024'

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,description,image_url,answer_id{id,sequence,text_value,is_correct,comment},question_id{id,question}}'
        return fields


class SimulabExperimentQuizAnswer(models.Model):
    _name = "quiz.answer"
    _rec_name = "text_value"
    _description = "Experiment Question's Answer"
    _order = 'question_id, sequence'
    _inherit = [
        'mail.thread',
        'image.mixin',
    ]

    sequence = fields.Integer("Sequence")
    question_id = fields.Many2one('quiz.question', string="Question", required=True,
                                  ondelete='cascade')
    text_value = fields.Html("Answer", required=True, translate=True)
    is_correct = fields.Boolean("Is correct answer")
    comment = fields.Html("Comment", translate=True,
                          help='This comment will be displayed to the user if he selects this answer')
    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=False, readonly=1, store=True)
    explanation_ids = fields.One2many('quiz.image.model', 'answer_id', string="Answer Explanation")

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            #record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=quiz.answer&id=' + str(
                    record.id) + '&field=image_1024'

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence,text_value,is_correct,comment,question_id{id,question}}'
        return fields

    @api.model
    def create(self, values):
        return super().create(values)

class SimulabStudentExperimentQuizQuestion(models.Model):
    _name = "student.quiz.question"
    _rec_name = "name"
    _description = "Students Experiment Quiz Question"
    _order = 'sequence'

    question_id = fields.Many2one('quiz.question', required=True)
    student_id = fields.Many2one('student.student', string="Student")
    student_quiz_id = fields.Many2one('student.experiment.quiz', "Quiz")
    attempted = fields.Boolean(default=False)
    time_spent = fields.Float("Time Spent", digits=(10, 4))

    quiz_id = fields.Many2one('experiment.quiz', related="question_id.quiz_id", store=True)
    experiment_id = fields.Many2one('simulab.experiment', related="quiz_id.experiment_id", store=True)
    student_quiz_answer_ids = fields.One2many('student.quiz.answer', 'student_question_id', string="Answers")
    name = fields.Char(related='question_id.question', store=True)
    sequence = fields.Integer(related='question_id.sequence', store=True)
    av_time = fields.Float(compute="_compute_time", digits=(10, 4), store=True, default=0.00)
    active = fields.Boolean(default=True, tracking=100)

    def _compute_time(self):
        for record in self:
            record.av_time = 0.0

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence,question_id{id,sequence, question, time_spent, av_time, tag_ids{id,name}, answer_ids{id,sequence,text_value,is_correct,comment,image_url},explanation_ids{description,image_url},quiz_id{id,name}, attempts_count, attempts_avg, done_count}}'
        return fields


class SimulabStudentExperimentQuizAnswer(models.Model):
    _name = "student.quiz.answer"
    _rec_name = "name"
    _description = "Students Experiment Quiz Answer"
    _order = 'name, student_quiz_id'

    answer_id = fields.Many2one('quiz.answer', required=True)
    student_question_id = fields.Many2one('student.quiz.question', "Question")

    sequence = fields.Integer(related='answer_id.sequence', store=True)
    question_id = fields.Many2one('quiz.question', related='answer_id.question_id', store=True)
    quiz_id = fields.Many2one('experiment.quiz', related="question_id.quiz_id", store=True)
    experiment_id = fields.Many2one('simulab.experiment', related="quiz_id.experiment_id", store=True)
    is_correct = fields.Boolean(related="answer_id.is_correct", store=True)
    student_quiz_id = fields.Many2one('student.experiment.quiz', related='student_question_id.student_quiz_id', store=True)
    student_id = fields.Many2one('student.student', related='student_question_id.student_id', store=True)
    name = fields.Html("Name", related='answer_id.text_value', store=True)

    @api.model
    def create(self, values):
        answer_id = values.get('answer_id', False)
        student_question_id = values.get('student_question_id', False)
        res = self.search([('answer_id','=',answer_id),('student_question_id', '=', student_question_id)])
        if res:
            return res[0]
        res = self.search([('student_question_id', '=', student_question_id)])
        if res:
            res[0].write({'answer_id':answer_id})
            return res
        return super().create(values)

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,sequence,quiz_id{id,name}, experiment_id{id,name}, student_quiz_id{id,name},student_id{id,name}, answer_id{id,sequence,text_value,is_correct,comment,image_url,explanation_ids{description,image_url},question_id{id,question}},question_id{id,sequence, question,  answer_ids{id,sequence,text_value,is_correct,comment},quiz_id{id,name}, attempts_count, attempts_avg, done_count}}'
        return fields
