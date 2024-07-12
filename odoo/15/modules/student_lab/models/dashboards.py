# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SimulabStudentDashboard(models.Model):
    _name = 'simulab.student.dashboard'
    _description = 'Student Dashboard'
    _rec_name = 'student_id'
    _order = "write_date"

    school_id = fields.Many2one('simulab.school', 'School',
                                help='School of the following standard')

    student_id = fields.Many2one('student.student', required=True)
    name = fields.Char(related="student_id.name")

    exp_completed = fields.Integer(string="Experiment Completed(%)",
                                   store=True)
    exp_inprocess = fields.Integer(string="Experiment In Process(%)",
                                   store=True)
    exp_not_started = fields.Integer(string="Experiment Not Started(%)",
                                     store=True)
    exp_completed_num = fields.Integer(string="Experiment Completed",
                                       store=True)
    exp_completed_on_time = fields.Integer(string="Experiment Completed On Time",
                                         store=True)
    exp_over_due = fields.Integer(string="Experiment Over Due",
                                  store=True)

    quiz_completed = fields.Integer(string="Quizzes Completed(%)",
                                    store=True)
    quiz_inprocess = fields.Integer(string="Quizzes In Process(%)",
                                    store=True)
    quiz_not_started = fields.Integer(string="Quizzes Not Started(%)",
                                      store=True)
    quiz_score_80 = fields.Integer(string="Quizzes Score More 80 (%)",
                                   store=True)
    quiz_score_50_80 = fields.Integer(string="Quizzes Score 50 to 80(%)",
                                      store=True)
    quiz_score_50 = fields.Integer(string="Quizzes Score Less 50(%)",
                                   store=True)
    quiz_completed_num = fields.Integer(string="Quizzes Completed",  store=True)
    quiz_completed_on_time = fields.Integer(string="Quizzes Completed On Time",
                                             store=True)
    quiz_passed = fields.Integer(string="Quizzes Passed",  store=True)
    quiz_failed = fields.Integer(string="Quizzes Failed",  store=True)
    quiz_over_due = fields.Integer(string="Quizzes Over Due",  store=True)
    quiz_90 = fields.Integer(string="Quizzes With More 90%",
                             store=True)

    @api.model
    def fields_get_queried_keys(self):
        fields = '{student_id{id, name}, exp_completed, exp_inprocess, exp_not_started, exp_completed_num, exp_completed_on_time, ' \
                 'exp_over_due, quiz_completed, quiz_inprocess, quiz_not_started, quiz_score_80, quiz_score_50_80, quiz_score_50, quiz_completed_num, quiz_completed_on_time, ' \
                 'quiz_passed, quiz_failed, quiz_over_due, quiz_90}'
        return fields


    #before this run
    # experiment due dates
    # quiz sequence correction
    # quiz marks
    # student dashboard

    def compute_experiments_statistics(self, student_id=False):
        search_term=[]
        if student_id:
            search_term = search_term+[('id', '=', student_id)]
        for student in self.env['student.student'].search(search_term, order='id desc'):
            all_exp = self.env['student.experiment'].search_count([('student_id', '=', student.id)])

            exp_completed = self.env['student.experiment'].search_count(
                [('student_id', '=', student.id), ('simulation_progress', '>=', 100)])

            exp_inprocess = self.env['student.experiment'].search_count(
                [('student_id', '=', student.id), ('simulation_progress', '>', 0),
                 ('simulation_progress', '<', 100)])

            exp_not_started = all_exp - (exp_completed + exp_inprocess)

            on_time_query = 'select count(id) from  student_experiment where student_id='+str(student.id)+' and planned_end_date >= actual_end_date '
            self._cr.execute(on_time_query)
            exp_completed_on_time = self._cr.fetchall()[0][0]

            overdue = 'select count(id) from  student_experiment where student_id='+str(student.id)+' and  planned_end_date < actual_end_date '
            self._cr.execute(overdue)
            exp_over_due = self._cr.fetchall()[0][0]

            all_exp = all_exp if all_exp>0 else 1
            # updated condition for handling division by zero exception
            vals = {"exp_completed": round(exp_completed / all_exp, 2) * 100 if all_exp > 0 else 0,
                "exp_inprocess": round(exp_inprocess / all_exp, 2) * 100 if all_exp > 0 else 0,
                "exp_not_started": round(exp_not_started / all_exp,2) * 100 if all_exp > 0 else 0,
                "exp_completed_num": exp_completed,
                "exp_completed_on_time": exp_completed_on_time,
                "exp_over_due": exp_over_due,
                "school_id": student.school_id.id if student.school_id.id else None,
                }
            
            quizzes = self.env['student.experiment.quiz'].search(
                [('student_id', '=', student.id)]) # Removed "sequence"=1 condition

            quiz_completed_num=0
            quiz_inprocess=0
            quiz_not_started=0
            quiz_score_80=0
            quiz_score_50_80=0
            quiz_score_50=0
            quiz_completed_on_time=0
            quiz_passed=0
            quiz_failed=0
            quiz_over_due=0
            quiz_90=0

            for quiz in quizzes:
                if quiz.quiz_status=='new':
                    quiz_not_started=quiz_not_started+1
                elif quiz.quiz_status=='in_progress':
                    quiz_inprocess=quiz_inprocess+1
                else:
                    quiz_completed_num=quiz_completed_num+1
                    total_marks = quiz.quiz_id.marks if quiz.quiz_id.marks > 0 else 1
                    marks_obtained = quiz.marks_obtained 
                    marks_percentage = round(marks_obtained/total_marks,2) * 100 if total_marks > 0 else 0
                    if marks_percentage >=90:
                        quiz_90=quiz_90+1
                    elif marks_percentage >=80:
                        quiz_score_80=quiz_score_80+1
                    elif marks_percentage >=50:
                        quiz_score_50_80=quiz_score_50_80+1
                    else:
                        quiz_score_50=quiz_score_50+1

                    if marks_percentage>=40:
                        quiz_passed=quiz_passed+1
                    else:
                        quiz_failed = quiz_failed+1

                    if quiz.student_experiment_id.planned_end_date and quiz.student_experiment_id.planned_end_date>=quiz.write_date:
                        quiz_completed_on_time=quiz_completed_on_time+1
                    else:
                        quiz_over_due=quiz_over_due+1

            quiz_count=len(quizzes) if len(quizzes)>1 else 1
            vals['quiz_completed_num']=quiz_completed_num
            vals['quiz_completed']=round(quiz_completed_num*100.0/quiz_count, 2) if quiz_count>0 else 0
            vals['quiz_inprocess']=round(quiz_inprocess*100.0/quiz_count, 2) if quiz_count>0 else 0
            vals['quiz_not_started']=round(quiz_not_started*100.0/quiz_count, 2) if quiz_count>0 else 0
            vals['quiz_score_80']=quiz_score_80
            vals['quiz_score_50_80']=quiz_score_50_80
            vals['quiz_score_50']=quiz_score_50
            vals['quiz_completed_on_time']=quiz_completed_on_time
            vals['quiz_passed']=quiz_passed
            vals['quiz_failed']=quiz_failed
            vals['quiz_over_due']=quiz_over_due
            vals['quiz_90']=quiz_90

            record = self.search([('student_id', '=', student.id)])
            if record:
                record.write(vals)
            else:
                vals["student_id"] = student.id
                record = self.create(vals)
            self._cr.commit()

        return True

class SchoolStandardDashboard(models.Model):
    _name = 'school.standard.dashboard'
    _description = 'School Standard Dashboard'
    _rec_name = 'class_id'
    _order = "write_date"


    class_id = fields.Many2one('school.standard', 'Class',
                               required=True, help='Section')

    school_id = fields.Many2one('simulab.school', related='class_id.school_id', store=True)

    exp_completed = fields.Integer(string="Experiment Completed Percentage",
                                   store=True)
    exp_inprocess = fields.Integer(string="Experiment In Process Percentage",
                                   store=True)
    exp_not_started = fields.Integer(string="Experiment Not Started Percentage",
                                     store=True)

    students_exp_completed = fields.Integer(string="Students Experiment Completed", store=True)
    students_exp_completed_80 = fields.Integer(string="Students Experiment Completed More Than 80%",
                                               store=True)
    students_exp_completed_50_80 = fields.Integer(string="Students Experiment Completed More Than 50%",
                                                  store=True)
    students_exp_completed_50 = fields.Integer(string="Students Experiment Completed Less Than 50%",
                                               store=True)
    students_exp_over_due = fields.Integer(string="Students Experiment Over Due", store=True)

    quiz_completed = fields.Integer(string="Quizzes Completed Percentage",
                                    store=True)
    quiz_inprocess = fields.Integer(string="Quizzes In Process Percentage",
                                    store=True)
    quiz_not_started = fields.Integer(string="Quizzes Not Started",
                                      store=True)
    quiz_score_80 = fields.Integer(string="Quizzes Score More 80 (%)",
                                   store=True)
    quiz_score_50_80 = fields.Integer(string="Quizzes Score 50 to 80(%)",
                                      store=True)
    quiz_score_50 = fields.Integer(string="Quizzes Score Less 50(%)",
                                   store=True)
    students_quiz_completed = fields.Integer(string="Quizzes Completed", store=True)
    students_quiz_completed_80 = fields.Integer(string="Students Quizzes Completed More Than 80%",
                                                store=True)
    students_quiz_completed_50_80 = fields.Integer(string="Students Quizzes Completed More Than 50%",
                                                   store=True)
    students_quiz_completed_50 = fields.Integer(string="Students Quizzes Completed Less Than 50%",
                                                store=True)
    students_quiz_failed = fields.Integer(string="Quizzes Failed", store=True)
    students_quiz_over_due = fields.Integer(string="Quizzes Over Due", store=True)
    students_quiz_score_90 = fields.Integer(string="Quizzes Top Performance",
                                            store=True)  # Students scored more than 90% percentage in atleast 10 quizzes

    @api.model
    def fields_get_queried_keys(self):
        fields = '{exp_completed, exp_inprocess, exp_not_started, students_exp_completed, students_exp_completed_80, ' \
                 'students_exp_completed_50_80, students_exp_completed_50, students_exp_over_due, quiz_completed, quiz_inprocess,' \
                 'quiz_not_started, quiz_score_80, quiz_score_50_80, quiz_score_50, students_quiz_completed, students_quiz_completed_80, students_quiz_completed_50_80, ' \
                 'students_quiz_completed_50, students_quiz_failed, students_quiz_over_due, students_quiz_score_90}'
        return fields
    #school.standard.dashboard
    def compute_experiments_statistics(self, class_id=False):
        search_term=[]
        #class_id = 80 # testing
        if class_id:
            search_term = search_term+[('id', '=', class_id)]

        for record in self.env['school.standard'].search(search_term, order='id desc'):
            exp_completed=0
            exp_inprocess=0
            exp_not_started=0
            students_exp_completed=0
            students_exp_completed_80=0
            students_exp_completed_50_80=0
            students_exp_completed_50=0
            students_exp_over_due=0

            all_exp = self.env['student.experiment'].search_count([('class_id', '=', record.id), ('master_experiment','=', False)])
            exp_inprocess = self.env['student.experiment'].search_count([('class_id', '=', record.id), ('master_experiment','=', False), ('simulation_progress', '>', 0),
                                                                         ('simulation_progress', '<', 100)])
            exp_completed = self.env['student.experiment'].search_count([('class_id', '=', record.id), ('master_experiment','=', False),
                                                                         ('simulation_progress', '>=', 100)])
            exp_not_started=all_exp-(exp_inprocess+exp_completed)

            for student in record.student_ids:
                student_dashboard = self.env['simulab.student.dashboard'].search([('student_id','=',student.id)])
                if student_dashboard.exp_completed_num>=all_exp:
                    students_exp_completed=students_exp_completed+1
                if student_dashboard.exp_completed_num>0:
                    students_exp_completed=students_exp_completed+1 #added for the count
                if student_dashboard.exp_over_due>0:
                    students_exp_over_due=students_exp_over_due+1

            percentage_student_completed=0
            if len(record.student_ids)>0:
                percentage_student_completed = round(students_exp_completed*1.0/len(record.student_ids),2) 
            if percentage_student_completed>=80 and percentage_student_completed <100:
                students_exp_completed_80=percentage_student_completed
            if percentage_student_completed>=50 and percentage_student_completed <80:
                students_exp_completed_50_80=percentage_student_completed
            if percentage_student_completed<50 :
                students_exp_completed_50=percentage_student_completed

            vals={}
            vals['exp_completed']=exp_completed
            vals['exp_inprocess']=exp_inprocess
            vals['exp_not_started']=exp_not_started
            vals['students_exp_completed']=students_exp_completed
            vals['students_exp_completed_80']=students_exp_completed_80
            vals['students_exp_completed_50_80']=students_exp_completed_50_80
            vals['students_exp_completed_50']=students_exp_completed_50
            vals['students_exp_over_due']=students_exp_over_due

            dashboard = self.search([('class_id', '=', record.id)])
            if dashboard:
                dashboard.write(vals)
            else:
                vals["class_id"] = record.id
                self.create(vals)
            self._cr.commit()
            self.compute_quizzes_statistics(record.id)

        return True

    def compute_quizzes_statistics(self, class_id=False):
        search_term=[]
        if class_id:
            search_term = search_term+[('id', '=', class_id)]

        for record in self.env['school.standard'].search(search_term, order='id desc'):
            quiz_completed=0
            quiz_inprocess=0
            quiz_completed=0
            quiz_not_started=0
            quiz_score_50_80=0
            quiz_score_80=0
            quiz_score_50=0
            students_quiz_completed=0
            students_quiz_completed_80=0
            students_quiz_completed_50_80=0
            students_quiz_completed_50=0
            students_quiz_failed=0
            students_quiz_score_90=0
            students_quiz_over_due=0
            vals={}
            for student in record.student_ids:                              
                student_dashboard = self.env['simulab.student.dashboard'].search([('student_id','=',student.id)])
                
                if student_dashboard.quiz_completed_num > 0:
                    students_quiz_completed += 1
                    quiz_completed += student_dashboard.quiz_completed_num
                    
                    if student_dashboard.quiz_score_80 > 0:
                        students_quiz_completed_80 += 1
                    elif student_dashboard.quiz_score_50_80 > 0:
                        students_quiz_completed_50_80 += 1
                    elif student_dashboard.quiz_score_50 > 0:
                        students_quiz_completed_50 += 1
                
                if student_dashboard.quiz_inprocess>0:
                    quiz_inprocess=quiz_inprocess+1

                if student_dashboard.quiz_not_started>0:
                    quiz_not_started=quiz_not_started+1

                if student_dashboard.quiz_score_80>0:
                    quiz_score_80=quiz_score_80+1

                if student_dashboard.quiz_score_50_80>0:
                    quiz_score_50_80=quiz_score_50_80+1

                if student_dashboard.quiz_score_50>0:
                    quiz_score_50=quiz_score_50+1

                if student_dashboard.quiz_90>0:
                    students_quiz_score_90=students_quiz_score_90+1

                if student_dashboard.quiz_failed>0:
                    students_quiz_failed=students_quiz_failed+1

                if student_dashboard.quiz_over_due>0:
                    students_quiz_over_due=students_quiz_over_due+1
            
            vals['quiz_completed']=quiz_completed
            vals['quiz_completed']=quiz_completed
            vals['quiz_inprocess']=quiz_inprocess
            vals['quiz_not_started']=quiz_not_started
            vals['quiz_score_80']=quiz_score_80
            vals['quiz_score_50_80']=quiz_score_50_80
            vals['quiz_score_50']=quiz_score_50
            vals['students_quiz_completed']=students_quiz_completed
            vals['students_quiz_completed_80']=students_quiz_completed_80
            vals['students_quiz_completed_50_80']=students_quiz_completed_50_80
            vals['students_quiz_completed_50']=students_quiz_completed_50
            vals['students_quiz_failed']=students_quiz_failed
            vals['students_quiz_over_due']=students_quiz_over_due
            vals['students_quiz_score_90']=students_quiz_score_90

            dashboard = self.search([('class_id', '=', record.id)])
            if dashboard:
                dashboard.write(vals)
            else:
                vals["class_id"] = record.id
                dashboard = self.create(vals)
            self._cr.commit()

        return True
