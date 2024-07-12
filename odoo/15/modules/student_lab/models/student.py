# See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, fields, models
from odoo.modules import get_module_resource
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base_import.models.base_import import ImportValidationError
from datetime import datetime

#SUBODH:: Newly added for session
from odoo.http import request

import re

import logging
_logger = logging.getLogger(__name__)

# from lxml import etree
# added import statement in try-except because when server runs on
# windows operating system issue arise because this library is not in Windows.
try:
    from odoo.tools import image_colorize
except:
    image_colorize = False

class FintecQuickImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.model
    def _convert_import_data(self, fields, options):
        # Override base method
        # Called when actual/test import start

        if self.res_model == 'student.student':
            options.pop('name_create_enabled_fields', {})
            _file_length, rows_to_import = super(FintecQuickImport, self)._read_file(options)
            return self._process_student_import(options, _file_length, rows_to_import)

        return super()._convert_import_data(fields, options)

    def _process_student_import(self, options, file_length, rows_to_import):
        data_headers = ['name', 'dob',
                        'gender', 'school', 'class', 'section', 'city','board','medium'] #SUBODH:: added - 'board', 'medium']

        index = 0
        available_header_in_file = []
        for data in rows_to_import:
            index = index + 1
            if index > 20:  # max depth for headers
                break
            data = [x.strip().lower() for x in data]
            if set(data_headers).issubset(data):
                available_header_in_file = data
                break

        if not available_header_in_file:
            raise ImportValidationError(
                _(
                    "Invalid format for student export"))

        data_rows = rows_to_import[index:len(rows_to_import)]
        user = self.env.user
        data_source = "Imported " + str(len(data_rows)) + " records via xls file by " + user.name

        data_to_import = []

        header_in_file = []
        for col in available_header_in_file:
            header_in_file = header_in_file + [col.lower()]

        name_index = header_in_file.index('name')
        dob_index = header_in_file.index('dob')
        gender_index = header_in_file.index('gender')
        school_index = header_in_file.index('school')
        class_index = header_in_file.index('class')
        section_index = header_in_file.index('section')
        city_index = header_in_file.index('city')
        board_index = header_in_file.index('board') #SUBODH:: Newly added
        medium_index = header_in_file.index('medium') #SUBODH:: Newly added

        try:
            password_index = header_in_file.index('password')
        except Exception as e:
            password_index=-1

        try:
            login_index = header_in_file.index('login')
        except Exception as e:
            login_index=-1

        try:
            mobile_index = header_in_file.index('mobile')
        except Exception as e:
            mobile_index=-1

        try:
            email_index = header_in_file.index('email_index')
        except Exception as e:
            email_index=-1

        dryrun = options.get("dryrun", False)
        row_count = 0
        class_id = False
        student_ids = []
        _logger.info("totoal rows count to be imported: "+ str(len(data_rows) ))
        for d in data_rows:
            row_count = row_count + 1
            name = d[name_index].strip()
            mobile = d[mobile_index].strip()  if mobile_index > 0 else False
            school = d[school_index].strip()
            class_name = d[class_index].strip()
            section = d[section_index].strip()
            password = d[password_index].strip() if password_index > 0 else False
            login = d[login_index].strip() if login_index > 0 else False

            school_id = self.env['simulab.school'].search(
                [('name', '=', school)])
            if not school_id:
                raise ImportValidationError(_("data row " + str(
                    row_count) + ": School \"" + school + "\" is not configured! Please create school and try again."))

            school_id = school_id[0]
            if password and not school_id.email:
                raise ImportValidationError(_(
                    "For managed password, school email id is required to be configured. Please configure shool email where user reset password email will be sent."))

            class_name = "Class " + class_name + '[' + section + ']'
            class_id = self.env['school.standard'].search(
                [('name', '=', class_name), ('school_id', '=', school_id.id)])
            if not class_id:
                raise ImportValidationError(_("data row " + str(
                    row_count) + ": Class " + class_name + " is not configured for the school \"" + school + "\"! Please create class and try again."))

            city = d[city_index].strip()
            if city:
                city_id = self.env['res.city'].search(
                    [('name', '=', city)])
                if not city_id:
                    raise ImportValidationError(
                        _("data row " + str(row_count) + ": City \"" + city + "\" not found."))
                city = city_id[0]

            gender = d[gender_index].strip()
            email = d[email_index].strip() if email_index > 0 else False
            dob = d[dob_index].strip()
            
            #SUBODH:: check added for board and medium
            board = d[board_index].strip()
            if board:
                board_id = self.env['edu.boards'].search(
                    [('id', '=', board)])
                if not board_id:
                    validation_errors.append(f"Error {error_count}: {board} board Not found, Plz Configure it")
                    error_count+=1
                board_id_name = board_id[0]['name'] if board_id else False
                
            medium = d[medium_index].strip()
            if medium:
                medium_id = self.env['edu.medium'].sudo().search(
                    [('id', '=', medium)])
                if not medium_id:
                    validation_errors.append(f"Error {error_count}: {medium} medium Not found, Plz Configure it")
                    error_count+=1
                medium_id_name = medium_id[0]['name'] if medium_id else False

            vals = {}
            vals["name"] = name
            vals["mobile"] = mobile
            vals["school_id"] = school_id.id
            if email:
                vals["email"] = email

            if city:
                vals["city_id"] = city.id
            vals["class_id"] = class_id.id
            if gender:
                vals["gender"] = gender.lower()
            if dob:
                vals["date_of_birth"] = dob
                
            #SUBODH:: board and medium added
            if board_id_name:
                vals["board_id_name"] = board_id_name
                vals["board_id"] = board
                
            if medium_id_name:
                vals["medium_id_name"] = medium_id_name
                vals["medium_id"] = medium

            vals["standard_id"] = class_id.standard_id.id
            vals["remark"] = data_source
            vals["other_info"] = str({"header": available_header_in_file, "values": d})
            vals["login"] = login
            user_login= login or mobile or email
            student_user = self.env['res.users'].search(
                [('login', '=', user_login)])

            if password:
                vals["email"] = school_id.email
                vals["email_verified"] = True
                vals["password"] = password
                vals["managed_user"] = True

            student=False
            if student_user:
                student = self.env['student.student'].search(
                    [('user_id', '=', student_user[0].id)])
            elif mobile:
                student = self.env['student.student'].search(
                [('mobile', '=', mobile)])
            if student:
                student_ids = student_ids + [student.id]
                if not student.school_id:
                    if student.remark:
                        if student.remark != data_source:
                            vals[
                                "remark"] = data_source + ", Student was already added: " + student.remark
                    del vals["mobile"]
                    student.write(vals)
                continue

            data_to_import = data_to_import + [vals]
        if not data_to_import and not student_ids:
            raise ImportValidationError(_("Data available in file are already imported"))

        _logger.info("total students to be imported: "+ str(len(data_to_import)) )
        if not dryrun:
            if student_ids:
                for student in class_id.student_ids:
                    if student.id in student_ids:
                        student_ids.remove(student.id)

            if not data_to_import:
                raise ImportValidationError(_("Data available in file are already imported"))

            i=1
            for data in data_to_import:
                _logger.info("Creating new student called with data: "+ str(data))
                student = self.env['student.student'].create(data)
                student._cr.commit()
                _logger.info("Creating new student done "+str(i)+"/"+str(len(data_to_import))+" : "+ data["name"]+"\n")
                student_ids = student_ids + [student.id]
                i=i+1

            for student in class_id.student_ids:
                student_ids = student_ids + [student.id]

            student_ids = [(6, 0, student_ids)]
            class_id.write({'student_ids': student_ids})
            class_id._cr.commit()
        # all created run time, nothing to import
        import_fields = []
        import_fields.append('name')
        import_fields.append('mobile')
        import_fields.append('user_id')
        return [], import_fields
    
    @api.model
    def extract_file_length_and_rows(self, *args, **kwargs):
        try:
            data_list = kwargs['data']
    
            file_length = len(data_list)
        
            rows_to_import = data_list
        
            return self._process_student_import_android(file_length, rows_to_import)
        except Exception as e:
            result = {'error' : True, 'result':e, "status":200}
            return result
    
    def _process_student_import_android(self, file_length, rows_to_import):
        logged_user = self.env.user
        error_count = 0
        validation_errors = []
        messages = []
        data_headers = ['name', 'dob',
                        'gender', 'school', 'class', 'section', 'city','board','medium'] #SUBODH:: added - 'board', 'medium'
        

        index = 0
        available_header_in_file = []
        try:
            if logged_user.simulab_user=='teacher' or logged_user.simulab_user=='school_admin':
                logged_user_name = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
                logged_user_name = logged_user_name.name
                messages.append(f'Action Performed by {logged_user_name}')
                    
                
            else:
                validation_errors.append(f"Error {error_count}: Unauthorized access! Warning: Wrong user or unauthorized action.")
                error_count+=1
                
                if validation_errors:
                        result = {
                        'error' : True,
                        'result':[{'message': validation_errors}],
                "status": 200
                }
                        return result
            
            datas = [data.keys() for data in rows_to_import][0]
            datas = list(datas)
            for index in range(0, 21):
                index = index + 1
                if index > 20:  # max depth for headers
                    break
                datas = [x.strip().lower() for x in datas]
                if set(data_headers).issubset(datas):
                    available_header_in_file = datas
                    break

            if not available_header_in_file:
                validation_errors.append(f"Error {error_count}: Invalid login number format. It should be a 10-digit number.")
                error_count+=1

            data_rows = [[str(value) if isinstance(value, int) else value for value in d.values()] for d in rows_to_import]
            data_rows = list(data_rows)
                
            user = self.env.user
            data_source = "Imported " + str(len(data_rows)) + " records via xls file by " + user.name

            data_to_import = []

            header_in_file = []
            for col in available_header_in_file:
                header_in_file = header_in_file + [col.lower()]

            name_index = header_in_file.index('name')
            dob_index = header_in_file.index('dob')
            mobile_index = header_in_file.index('mobile')
            gender_index = header_in_file.index('gender')
            school_index = header_in_file.index('school')
            class_index = header_in_file.index('class')
            section_index = header_in_file.index('section')
            city_index = header_in_file.index('city')
            board_index = header_in_file.index('board') #SUBODH:: Newly added
            medium_index = header_in_file.index('medium') #SUBODH:: Newly added

            try:
                password_index = header_in_file.index('password')
            except Exception as e:
                password_index=-1

            try:
                login_index = header_in_file.index('login')
            except Exception as e:
                login_index=-1

            try:
                mobile_index = header_in_file.index('mobile')
            except Exception as e:
                mobile_index=-1

            try:
                email_index = header_in_file.index('email')
            except Exception as e:
                email_index=-1

            # dryrun = options.get("dryrun", False)     #We are not testing the file
            row_count = 0
            class_id = False
            student_ids = []
            _logger.info("totoal rows count to be imported: "+ str(len(data_rows) ))
            for d in data_rows:
                row_count = row_count + 1
                name = d[name_index].strip()
                mobile = d[mobile_index].strip()  if mobile_index >= 0 else False
                school = d[school_index].strip()
                class_name = d[class_index].strip()
                section = d[section_index].strip()
                password = d[password_index].strip() if password_index > 0 else False
                login = d[login_index].strip() if login_index > 0 else False
                dob = d[dob_index].strip()
                email = d[email_index].strip()
                
                
                if mobile:
                    if [i for i in mobile if i.isalpha()]:
                        validation_errors.append(f"Error {error_count}: Invalid login number format. It should be a 10-digit number.")
                        error_count+=1
                    if not len(mobile)==10:
                        validation_errors.append(f"Error {error_count}: Invalid mobile number format. It should be a 10-digit number.")
                        error_count+=1

                if dob:
                    try:
                        dob = datetime.strptime(dob, '%Y-%m-%d')
                    except ValueError:
                        validation_errors.append(f"Error {error_count}: Invalid date of birth format. It should be in 'Y-M-D' format.")
                        error_count+=1
                
                if login:
                    if [i for i in login if i.isalpha()]:
                        validation_errors.append(f"Error {error_count}: Invalid login number format. It should be a 10-digit number.")
                        error_count+=1
                    elif len(login)!=10:
                        validation_errors.append(f"Error {error_count}: Invalid login number format. It should be a 10-digit number.")
                        error_count+=1
                
                if email:
                    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+'
                    if not re.match(email_pattern, email):
                        validation_errors.append(f"Error {error_count}: Invalid email format. Please provide a valid email address.")
                        error_count += 1
                    
                school_id = self.env['simulab.school'].search(
                    [('name', '=', school)])
                if not school_id:
                    validation_errors.append(f"Error {error_count}: {school} is not configured, Please create and try again")
                    error_count+=1

                # check if loggedIn user's school id and schoolId of school passed in hearder's match
            
                loggedUser_Id = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])
                loggedUser_schoolId = loggedUser_Id.school_id
                
                if school_id and school_id == loggedUser_schoolId:
                    school_id = school_id[0]
                else:
                    validation_errors.append(f"Error {error_count}:  You Do Not Have the Correct Access Rights")
                    error_count+=1
                
                if validation_errors:
                    result = {
                        'error' : True,
                        'result':[{"message":validation_errors}],
                "status": 200
                }
                    return result
                    
                if password and not school_id.email:
                    validation_errors.append(f"Error {error_count}: For managed password, school email id is required to be configured. Please configure shool email where user reset password email will be sent.")
                    error_count+=1
                    
                class_name = "Class " + class_name + '[' + section + ']'
                class_id = self.env['school.standard'].search(
                    [('name', '=', class_name), ('school_id', '=', school_id.id)])
                if not class_id:
                    validation_errors.append(f"Error {error_count}: {class_name} is not configured for the school  + {school} + ! Please create class and try again.")
                    error_count+=1
                    
                    
                city = d[city_index].strip()
                if city:
                    city_id = self.env['res.city'].search(
                        [('name', '=', city)])
                    if not city_id:
                        validation_errors.append(f"Error {error_count}: {city} city Not found, Plz Configure it")
                        error_count+=1
                    city = city_id[0] if city_id else False

                gender = d[gender_index].strip()
                email = d[email_index].strip() if email_index > 0 else False
                dob = d[dob_index].strip()
                
                #SUBODH:: check added for board and medium
                board = d[board_index].strip()
                if board:
                    board_id = self.env['edu.boards'].search(
                        [('id', '=', board)])
                    if not board_id:
                        validation_errors.append(f"Error {error_count}: {board} board Not found, Plz Configure it")
                        error_count+=1
                    board_id_name = board_id[0]['name'] if board_id else False
                    
                medium = d[medium_index].strip()
                if medium:
                    medium_id = self.env['edu.boards'].search(
                        [('id', '=', board)])
                    if not medium_id:
                        validation_errors.append(f"Error {error_count}: {medium} medium Not found, Plz Configure it")
                        error_count+=1
                    medium_id_name = medium_id[0]['name'] if medium_id else False

                vals = {}
                vals["name"] = name
                vals["mobile"] = mobile
                vals["school_id"] = school_id.id
                if email:
                    vals["email"] = email

                if city_id:
                    vals["city_id"] = city_id.id
                
                vals["class_id"] = class_id.id
                if gender:
                    vals["gender"] = gender.lower()
                if dob:
                    vals["date_of_birth"] = dob
                
                #SUBODH:: board and medium added
                if board_id_name:
                    vals["board_id_name"] = board_id_name
                    vals["board_id"] = board
                    
                if medium_id_name:
                    vals["medium_id_name"] = medium_id_name
                    vals["medium_id"] = medium

                vals["standard_id"] = class_id.standard_id.id
                vals["remark"] = data_source
                vals["other_info"] = str({"header": available_header_in_file, "values": d})
                vals["login"] = login
                user_login= login or mobile or email
                student_user = self.env['res.users'].search(
                    [('login', '=', user_login)])

                if password:
                    vals["email"] = school_id.email
                    vals["email_verified"] = True
                    vals["password"] = password
                    vals["managed_user"] = True

                student=False
                if student_user:
                    student = self.env['student.student'].search(
                        [('user_id', '=', student_user[0].id)])
                elif mobile:
                    student = self.env['student.student'].search(
                    [('mobile', '=', mobile)])
                if student:
                    student_ids = student_ids + [student.id]
                    if not student.school_id:
                        if student.remark:
                            if student.remark != data_source:
                                vals[
                                    "remark"] = data_source + ", Student was already added: " + student.remark
                        del vals["mobile"]
                        student.write(vals)
                    continue

                data_to_import = data_to_import + [vals]
            if not data_to_import and not student_ids:
                validation_errors.append(f"Error {error_count}: Data available in file are already imported")
                error_count+=1

            _logger.info("total students to be imported: "+ str(len(data_to_import)) )
            dryrun = False
            if not dryrun:
                if student_ids:
                    for student in class_id.student_ids:
                        if student.id in student_ids:
                            student_ids.remove(student.id)

                if not data_to_import:
                    validation_errors.append(f"Error {error_count}: Data available in file are already imported")
                    error_count+=1
                
                if validation_errors:
                    result = {
                        'error' : True,
                        'result':[{'message': validation_errors}],
                "status": 200
                }
                    return result

                i=1
                for data in data_to_import:
                    _logger.info("Creating new student called with data: "+ str(data))
                    student = self.env['student.student'].create(data)
                    student._cr.commit()
                    _logger.info("Creating new student done "+str(i)+"/"+str(len(data_to_import))+" : "+ data["name"]+"\n")
                    student_ids = student_ids + [student.id]
                    i=i+1

                for student in class_id.student_ids:
                    student_ids = student_ids + [student.id]

                student_ids = [(6, 0, student_ids)]
                class_id.write({'student_ids': student_ids})
                class_id._cr.commit()
                
            import_fields = []
            import_fields.append('name')
            import_fields.append('mobile')
            import_fields.append('user_id')
            
            messages.append('Data Imported Successfully !!')
                
        except Exception as e:
            raise ValidationError(f"An error occurred: {e}")
        result = {'result':[{'message': messages}], 'status':200}
        return result
    

class StudentStudent(models.Model):
    '''Defining a student information.'''

    _name = 'student.student'
    _table = "student_student"
    _description = 'Student Information'
    _rec_name = 'name'
    _inherit = [
        'simulab.email',
        'mail.thread',
        'mail.activity.mixin',
        'image.mixin',
    ]

    @api.model
    def _default_image(self):
        '''Method to get default Image'''
        image_path = get_module_resource('hr', 'static/src/img',
                                         'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    user_id = fields.Many2one('res.users', 'Login Id', ondelete="cascade", delegate=True,
                              help='Select related user of the student')
    login = fields.Char("Login Id", related='user_id.login', store=True, copy=False)

    name = fields.Char('Name', required=True)
    phone = fields.Char('Phone no.', help='Enter student phone no.')
    mobile = fields.Char('Mobile', help='Enter student mobile no.', required=False)
    photo = fields.Binary('Photo', default=_default_image,
                          help='Attach student photo')

    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              help='Select student gender')
    date_of_birth = fields.Date('Birth Date',
                                help='Enter student date of birth')

    remark = fields.Text('Remark', help='Remark can be entered if any')
    school_id = fields.Many2one('simulab.school', string="School")

    standard_id = fields.Many2one('standard.standard', string='Grade',
                                  help='Select student standard')
    class_id = fields.Many2one('school.standard', string='Class',
                               help='Select student Class')
    class_ids = fields.Many2many('school.standard', 'class_student_rel', 'student_id', 'class_id',
                                 'Class Students')
    active = fields.Boolean(default=True,
                            help='Activate/Deactivate student record')

    school_ids = fields.One2many('simulab.school', 'student_id',
                                 'Student Institues',
                                 help='Students can be part of multiple institutes'
                                 )

    course_lines = fields.One2many('enrolled.course', 'student_id',
                                   'Enrolled Courses',
                                   help='Student enrolled to courses'
                                   )

    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this Student''')

    exams_id = fields.Many2one('student.exams', "Preparing For")
    city_id = fields.Many2one('res.city', string="City")
    institute_id = fields.Many2one('student.institute', string="Institute")
    board_id = fields.Many2one('edu.boards', string="Education Board")
    
    #SUBODH:: New field for medium for Odhisha board changes
    medium_id = fields.Many2one('edu.medium', string="Education Medium")
    medium_id_name = fields.Char("medium_id_name", store=True)
    
    city_name = fields.Char(related="city_id.name", store=True)
    institute_id_name = fields.Char(related="institute_id.name", store=True)
    board_id_name = fields.Char(related="board_id.name", store=True)

    other_city = fields.Char("Student City")
    other_institute = fields.Char("Student Institute")
    other_board = fields.Char("Student Education Board")
    subscription_ids = fields.One2many('simulab.subscription', 'student_id', 'My Subscriptions',
                                       help='Student subscriptions')

    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=False, readonly=1, store=True)

    state = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('alumni', 'Alumni')],
        'Status', readonly=True, default="enrolled",
        help='State of the student registration form')

    simulab_id = fields.Char('Simulab Id', readonly=1)

    quiz_correct_answers = fields.Integer("Correct Answers")
    quiz_attempted_questions = fields.Integer("Attempted Questions")

    quiz_attempted = fields.Integer("Quiz Attempted")
    total_quizes = fields.Integer("Total Quizes")

    total_experiments = fields.Integer("Experiments")
    enrolled_course_count = fields.Integer("Experiments",compute='_compute_enrolled_course_count',store=True)

    country_id = fields.Many2one('res.country', 'Country')

    experiment_completed = fields.Integer("Experiment Completed", compute="compute_exp_stats", store=True)
    exp_completed_ontime = fields.Integer("Experiment Completed On Time",
                                          compute="compute_exp_stats", store=True)
    exp_overdue = fields.Integer("Experiment Overdue", compute="compute_exp_stats", store=True)
    quiz_completed = fields.Integer("Quiz Completed", compute="compute_quiz_status", store=True)
    quiz_completed_ontime = fields.Integer("Quiz Completed Ontime", compute="compute_quiz_status",
                                           store=True)
    quiz_passed = fields.Integer("Quiz Completed", compute="compute_quiz_status", store=True)
    quiz_failed = fields.Integer("Quiz Failed", compute="compute_quiz_status", store=True)
    quiz_overdue = fields.Integer("Quiz Overdue", compute="compute_quiz_status", store=True)

    other_info = fields.Text('Other Information', help='Other information if any')

    
    @api.depends('course_lines')
    def _compute_enrolled_course_count(self):   
        for student in self:
            student.enrolled_course_count = len(student.course_lines)   
    
    def compute_exp_stats(self):
        for record in self:
            record.experiment_completed = 0
            record.exp_completed_ontime = 0
            record.exp_overdue = 0

    def compute_quiz_status(self):
        for record in self:
            record.quiz_completed = 0
            record.quiz_completed_ontime = 0
            record.quiz_passed = 0
            record.quiz_failed = 0
            record.quiz_overdue = 0

    def compute_stat_for_all_students(self):
        students = self.search([])
        for student in students:
            self.compute_stat(student)

    def compute_stat(self, student=False, student_id=False):
        if student_id:
            student = self.browse(student_id)

        quiz_answers = self.env['student.quiz.answer'].search([('student_id', '=', student.id)])
        questions_attempted = []
        correct_answers = []
        quiz_attempted = []

        for quiz_answer in quiz_answers:
            questions_attempted = questions_attempted + [quiz_answer.question_id.id]
            if quiz_answer.answer_id.is_correct:
                correct_answers = correct_answers + [quiz_answer.answer_id.id]
            quiz_attempted = quiz_attempted + [quiz_answer.student_quiz_id.id]

        enrolled_courses = self.env['enrolled.course'].sudo().search(
            [('student_id', '=', student.id)])
        quizes_list = []

        for enrolled_course in enrolled_courses:
            for exp in enrolled_course.course_id.experiment_ids:
                for quiz in exp.quiz_ids:
                    if quiz not in quizes_list:
                        quizes_list = quizes_list + [quiz]

        quiz_correct_answers = len(list(set(correct_answers)))
        quiz_attempted_questions = len(list(set(questions_attempted)))
        quiz_attempted = len(list(set(quiz_attempted)))
        total_quizes = len(quizes_list)

        experiment_completed = []
        experiment_list = self.env['student.experiment'].search([('student_id', '=', student.id)])
        for exp in experiment_list:
            if exp.simulation_progress == 100:
                experiment_completed = experiment_completed + [exp.id]
        experiment_completed = len(experiment_completed)
        total_experiments = len(experiment_list)

        student.update_record(
            {'quiz_correct_answers': quiz_correct_answers, 'quiz_attempted_questions': quiz_attempted_questions,
             'quiz_attempted': quiz_attempted, 'total_quizes': total_quizes,
             'experiment_completed': experiment_completed,
             'total_experiments': total_experiments, 'enrolled_course_count': len(student.course_lines)})
        return

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=student.student&id=' + str(
                    record.id) + '&field=image_1024'

    @api.model
    def fields_get_queried_keys(self):
        fields = '{experiment_completed, exp_completed_ontime, exp_overdue, quiz_completed, quiz_completed_ontime, quiz_passed, quiz_failed, quiz_overdue,id,name, enrolled_course_count, country_id{id,name,code,phone_code}, other_city,other_institute, other_board, image_url, user_id{id,name}, class_ids{id,name,standard_id{id,name},division_id{id,name}}, class_id{id,name,standard_id{id,name},division_id{id,name}}, phone, mobile,email_verified,email,simulab_id, gender, city_id{id,name}, exams_id{id,name}, institute_id{id,name},board_id{id,name}, date_of_birth, remark, school_id{id,name}, standard_id{id,name}, school_ids{id,name},quiz_correct_answers,quiz_attempted_questions,quiz_attempted,total_quizes,total_experiments,medium_id{id,name}}'
        return fields

    @api.model
    def create(self, vals):

        is_student_new_profile = False
        vals['login'] = vals.get('login', vals.get('mobile', vals.get('email', False)))
        if not vals['login']:
            vals['login'] = vals.get('email', False)
        user_id = vals.get('user_id', False)
        if not user_id:
            is_student_new_profile = True
            user_id = self.create_student_login(vals).id

        logged_user = self.env.user
        school_id = vals.get('school_id', False)

        if not school_id:
            school_id = self.env['simulab.school'].search([('company_id', '=', int(logged_user.company_id.id))])
            vals['school_id'] = school_id.id

        vals['user_id'] = user_id
        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school.student')
        res = super().create(vals)

        if is_student_new_profile:
            notification_obj = self.env['simulab.notification']
            notification_obj.create_student_added_notification(res)

        #if school_id:
        #    self.env['simulab.homepage'].refresh_school_dashboard(self.env['simulab.school'].browse(school_id))
        return res

    def write(self, vals):
        if 'mobile' in vals:
            user_id = self.env['res.users'].search([('login', '=', vals['mobile'])])
            if user_id:
                raise UserError(_("Student with mobile no %s already added.") % vals['mobile'])

        res = super().write(vals)
        if 'mobile' in vals:
            self.user_id.write({'login': vals['mobile']})

        if 'email' in vals:
            notification_obj = self.env['simulab.notification']
            notification_obj.email_add_notification(self.id, self.user_id, self.email, self.name)

        if 'school_id' in vals:
            self.add_company(self.user_id, False)

        return res

    def create_student_login(self, vals):
        logged_user = self.env.user
        company_id = vals.get('company_id', False)
        school_id = vals.get('school_id', False)
        if not school_id:
            school_id = self.env['simulab.school'].sudo().search([('company_id', '=', int(logged_user.company_id.id))])
            school_id = school_id[0] if school_id else False
        else:
            school_id = self.env['simulab.school'].browse(school_id)
        if school_id:
            company_id = school_id.company_id.id
        if not company_id:
            company_id = int(self.env['ir.config_parameter'].sudo().get_param('default.student.company'))
        if not company_id:
            raise ValueError("Default School for Students is not set")

        login = vals['login']
        user_id = self.env['res.users'].sudo().search([('login', '=', login)])
        if user_id:
            user_id = user_id[0]
            if user_id.simulab_user != 'student':
                raise ValueError(
                    ("Different User Profile is already created with mobile no %s " % login))
            company_ids = [comp.id for comp in user_id.company_ids]
            if company_id in company_ids:
                raise ValueError("Student already registered for this school.")
            self.add_company(user_id, company_id)
            return user_id

        ctx_vals = {'student_create': True,
                    'company_id': company_id}

        user_vals = {}
        user_vals['company_ids'] = [(4, int(company_id))]
        user_vals['company_id'] = int(company_id)
        user_vals['simulab_user'] = 'student'
        user_vals['login'] = vals['login']
        user_vals['name'] = vals['name']
        password = vals.get('password', False)
        if password:
            user_vals['password'] = password
        user_id = self.env['res.users'].sudo().with_context(ctx_vals).create(user_vals)
        return user_id

    def add_company(self, user_id, company_id):
        students = self.env['student.student'].sudo().search([('user_id', '=', user_id.id)])
        company_ids = []
        for student in students:
            if student.school_id and student.school_id.company_id.id not in company_ids:
                company_ids = company_ids + [student.school_id.company_id.id]
        if company_id:
            company_ids = company_ids + [company_id]

        company_id = self.env['ir.config_parameter'].sudo().get_param('default.student.company')
        company_ids = company_ids + [int(company_id)]
        company_ids = [(6, 0, company_ids)]
        user_id.write({'company_ids': company_ids})

    def get_enrolled_courses(self, params={}):
        # status => all (expired+active)
        # status => active_enrolled
        # status => active_purchased
        # status => active
        simulab_courses = False
        logged_user = self.env.user
        student_ids = self.env['student.student'].search([('user_id', '=', logged_user.id)])
        student_ids = [student.id for student in student_ids]
        enrolled_args = [('student_id', 'in', student_ids)]
        
        enrolled_courses = self.env['enrolled.course'].search(enrolled_args)        

        return {'return_data_as_record_set': True, 'records': enrolled_courses, 'model': self.env['enrolled.course']}
    
    @api.model
    def bulk_import(self, *vals, **kw):
        # Get the request body as JSON         
        try:
            args = vals[0]
        except KeyError:
            msg = "`school_id` parameter is not found on POST request body"
            raise exceptions.ValidationError(msg)
        result = kw['result']
        data = kw['data']
        if result:
            if result=='success':
                result = { "result": "success", "message": "Data imported successfully."}
            if result=='error':
                result = { "result": "fail", "message": "Error while importing data.", "error_code": 1000}
        

        return {
            "school_id": args[2],
            "result": result,
            "data": data,
            "status": 200   
        }
        
    @api.model
    def get_student_list(self, *args, prev_page = None, next_page = None, total_page_number = 1, current_page = 1):
        logged_user = self.env.user
        teacher_ids = self.env['school.teacher'].search([('user_id', '=', logged_user.id)])

        if logged_user.simulab_user == 'teacher' and teacher_ids:
            teacher_id = teacher_ids.id
            school_id = args[0][2]

        try:
            if teacher_id and school_id:
                        query = "SELECT class_id FROM school_class_rel WHERE teacher_id = %s"
                        self._cr.execute(query, (teacher_id,))
                        result = self._cr.fetchall()
                        class_ids = [row[0] for row in result]
                        
                        standard_id = None
                        for arg in args:
                            if arg[0] == 'standard_id':
                                standard_id = arg[2]
                                break
                        
                        if standard_id:
                            
                            class_idss = self.env['school.standard'].search([  
                            ('id', '=', class_ids),                     
                            ('school_id', '=', school_id),
                            ('standard_id', '=', standard_id),
                            ('active', '=', True),
                            ('total_students', '>', 0)
                            ])
                        else:
                            class_idss = self.env['school.standard'].search([
                            ('id', 'in', class_ids),
                            ('school_id', '=', school_id),
                            ('active', '=', True),
                            ('total_students', '>', 0)
                            ])
                            
                        active_class_ids = class_idss.ids
                        query = "SELECT student_id FROM class_student_rel WHERE class_id IN %s"
                        
                        self._cr.execute(query, (tuple(active_class_ids),))
                        result = self._cr.fetchall()
                        student_ids = [row[0] for row in result]

                        student_list = self.env['student.student'].sudo().search([
                        ('id', 'in', student_ids),
                        ('active', '=', True)
                        ])
        except Exception as e:
            student_list = []
            response = {
        "count": len(student_list),
        "prev": prev_page,
        "current": current_page,
        "next": next_page,
        "total_pages": total_page_number,
        "result": student_list,
        "status": 200
        }       
            return response

        return {'return_data_as_record_set': True, 'records': student_list, 'model': self}
    
    def student_in_class(self, *args, prev_page = None, next_page = None, total_page_number = 1, current_page = 1):
        class_id = args[0][2]
        
        standard_id = None
        for arg in args:
            if arg[0] == 'standard_id':
                standard_id = arg[2]
                break
        try:                
            if standard_id:
                class_ids = self.env['school.standard'].search([  
                                ('id', '=', class_id),
                                ('standard_id', '=', standard_id),
                                ('active', '=', True)
                                ])
            else:
                class_ids = self.env['school.standard'].search([
                                ('id', '=', class_id),
                                ('active', '=', True)
                                ])
            class_idss = class_ids.ids
            query = "SELECT student_id FROM class_student_rel WHERE class_id = %s"
                            
            self._cr.execute(query, (class_idss),)
            result = self._cr.fetchall()
            student_ids = [row[0] for row in result]

            student_list = self.env['student.student'].sudo().search([
                        ('id', 'in', student_ids),
                        ('active', '=', True)
                        ])
        
        except Exception as e:
            student_list = []
            response = {
        "count": len(student_list),
        "prev": prev_page,
        "current": current_page,
        "next": next_page,
        "total_pages": total_page_number,
        "result": student_list,
        "status": 200
        }       
            return response
        
        return {'return_data_as_record_set': True, 'records': student_list, 'model': self}       