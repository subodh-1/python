import logging
import ast
import re
from uuid import uuid4

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class SimulabNotification(models.Model):
    _name = 'simulab.notification'
    _description = 'SimuLab Notification'
    _order = 'write_date desc'
    _rec_name = 'to_user'

    to_user = fields.Many2one('res.users', 'To User', help='To User', readonly=True)
    message_title = fields.Char("Message Title", help='Notification subject or title', readonly=True)
    message = fields.Text("Message", readonly=True)
    phone_number = fields.Char('Phone Number', readonly=True)
    email = fields.Char('Email', readonly=True)
    message_reference = fields.Char("Message Reference", readonly=True)
    retry_counts = fields.Integer("Retry count", default=3, readonly=True)
    notification_response = fields.Text("Notification Response", readonly=True)
    channel_id = fields.Selection([
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('notification', 'Notification'),
    ],
        'Notification Channel', default="email", readonly=True)

    status = fields.Selection([
        ('new', 'New'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ],
        'Notification Status', default="New", readonly=True)

    template_id = fields.Many2one('notification.template', 'Template ID', help='Notification Template', readonly=True)
    email_template_res_id = fields.Integer("Email Template Resource ID")
    template_parameters = fields.Text("Template Parameters")
    scheduled_date = fields.Datetime("Scheduled Date")
    write_date = fields.Datetime("Edit Date")
    create_date = fields.Datetime(string="Create Date")

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id, message_title, message, write_date}'
        return fields

    def get_notifications(self, params=[]):
        logged_user = self.env.user
        if logged_user:
            params = params + [('to_user', '=', logged_user.id), ('status', '=', "success")]

        notifications = self.env['simulab.notification'].search(params)
        return {'return_data_as_record_set': True, 'records': notifications,
                'model': self.env['simulab.notification']}

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    @api.model
    def write(self, vals):
        res = super().write(vals)
        return res

    def validate_mobile_number(self, mobile_number):
        mobile_number_pattern = r"^(\+\d{1,3}[- ]?)?\d{10}$"
        mobile_number_regex = re.compile(mobile_number_pattern)
        match = mobile_number_regex.search(mobile_number)
        return bool(match)

    def email_add_notification(self, res_id, user_id, email, name):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)
        simulab_user = user_id.simulab_user

        if simulab_user == 'school_admin':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'email_add_admin'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')
        elif simulab_user == 'teacher':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'email_add_teacher'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')

        elif simulab_user == 'student':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'email_add_student'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')

    def email_verified_notification(self, res_id, user_id, email, name):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)
        simulab_user = user_id.simulab_user

        if simulab_user == 'school_admin':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'admin_email_verified'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')
        elif simulab_user == 'teacher':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'teacher_email_verified'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')
        elif simulab_user == 'student':
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_email_verified'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name}
            self.create_email_notification(user_id=user_id.id, message=None, email=email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=res_id,
                                           template_parameters=email_template_parameters,
                                           status='new')

    def create_student_added_notification(self, student):
        school = student.school_id
        if not school:
            return

        school_name = school.name
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(student.login):
            sms_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_added'), ('channel_id', '=', 'sms')])
            message = sms_notification_template.message_body % ( student.login )
            self.create_sms_notification(student.user_id.id, message, student.login, 'new')

    def create_teacher_added_notification(self, teacher):
        school = teacher.school_id
        if not school:
            return True

        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(teacher.login):
            sms_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'teacher_added'), ('channel_id', '=', 'sms')])

            message = sms_notification_template.message_body % (teacher.login)
            self.create_sms_notification(teacher.user_id.id, message, teacher.login, 'new')

    def create_teacher_class_assignment_notification(self, teacher, assigned_class):
        school_id = teacher.school_id
        if not school_id:
            return

        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(teacher.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'teacher_class_assigned'), ('channel_id', '=', 'sms')])
            if notification_template:
                message = notification_template.message_body % (assigned_class.name)
                self.create_sms_notification(teacher.user_id.id, message, teacher.login, 'new')

        # Send FCM notification to the teacher device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'teacher_class_assigned'), ('channel_id', '=', 'notification')])

        if notification_template:
            message = notification_template.message_body % assigned_class.name
            self.create_fcm_notification(teacher.user_id.id, notification_template.message_title, message, 'new')

        if teacher.email and teacher.email_verified:
            # Send email notification to the teacher device
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'teacher_class_assigned'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': teacher.email, 'name': teacher.name,
                                         'class_name': assigned_class.name,
                                         'school_name': school_id.name}

            self.create_email_notification(user_id=teacher.user_id.id, message=None, email=teacher.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=teacher.id,
                                           template_parameters=email_template_parameters,
                                           status='new')

        return True

    def create_student_class_assignment_notification(self, student, assigned_class):
        school_id = student.school_id
        if not school_id:
            return

        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        # Send FCM notification to the student device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'student_assigned_class'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % assigned_class.name
        self.create_fcm_notification(student.user_id.id, notification_template.message_title, message, 'new')

        if student.email and student.email_verified:
            # Send email notification to the student email
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_assigned_class'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': student.email, 'name': student.name,
                                         'class_name': assigned_class.name,
                                         'school_name': school_id.name,
                                         'login': student.login}

            self.create_email_notification(user_id=student.user_id.id, message=None, email=student.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=student.id,
                                           template_parameters=email_template_parameters,
                                           status='new')
        elif self.validate_mobile_number(student.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_assigned_class'), ('channel_id', '=', 'sms')])
            if notification_template.message_body:
                message = notification_template.message_body % (student.name, school_id.name, student.login)
                self.create_sms_notification(student.user_id.id, message, student.login, 'new')

        return True

    def create_course_enrolled_by_school_notification_to_student(self, student, course_name, class_name):
        school_id = student.school_id
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        # Send SMS notification to the student mobile number
        if self.validate_mobile_number(student.login):
            sms_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_assigned_course'), ('channel_id', '=', 'sms')])

            if len(course_name) > 30:
                first_30_characters = course_name[0:30]
                message = sms_notification_template.message_body % (
                    first_30_characters, student.login)
            else:
                message = sms_notification_template.message_body % (
                    course_name, student.login)

            self.create_sms_notification(student.user_id.id, message, student.login, 'new')

        # Send FCM notification to the student device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'student_assigned_course'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % course_name
        self.create_fcm_notification(student.user_id.id, notification_template.message_title, message, 'new')

        if student.email and student.email_verified:
            # Send email notification to the student's email
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'student_assigned_course'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': student.email, 'name': student.name,
                                         'course_name': course_name,
                                         'class_name': class_name,
                                         'school_name': school_id.name}

            self.create_email_notification(user_id=student.user_id.id, message=None, email=student.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=student.id,
                                           template_parameters=email_template_parameters,
                                           status='new')

        return True

    def create_course_enrolled_by_school_notification_to_school_admin(self, teacher, course_name, enrolled_count):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        # Send FCM notification to the school admin device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'course_enrolled_admin'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % (course_name, enrolled_count)

        self.create_fcm_notification(teacher.user_id.id, notification_template.message_title, message, 'new')

        return True

    def create_bulk_buy_success_notification_to_admin(self, teacher, enrolled_course, total_amount,
                                                      number_of_students):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(teacher.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'bulk_buy_success_admin'), ('channel_id', '=', 'sms')])

            if len(enrolled_course.name) > 30:
                first_30_characters = enrolled_course.name[0:30]
                """ message = notification_template.message_body % (
                    teacher.name, str(total_amount), first_30_characters, str(number_of_students),
                    enrolled_course.class_id.name) """
                
                message = notification_template.message_body % (
                    str(total_amount), first_30_characters, str(number_of_students),
                    enrolled_course.class_id.name)
            else:
                """ message = notification_template.message_body % (
                    teacher.name, str(total_amount), enrolled_course.name, str(number_of_students),
                    enrolled_course.class_id.name) """
                
                message = notification_template.message_body % (
                    str(total_amount), enrolled_course.name, str(number_of_students),
                    enrolled_course.class_id.name)

            self.create_sms_notification(teacher.user_id.id, message, teacher.login, 'new')

        # Send FCM notification to the school admin device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'bulk_buy_admin'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % (enrolled_course.name, str(number_of_students))

        self.create_fcm_notification(teacher.user_id.id, notification_template.message_title, message, 'new')

        if teacher.email and teacher.email_verified:
            # Send email notification to the school admin device
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'bulk_buy_admin'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': teacher.email, 'name': teacher.name, 'total_amount': total_amount,
                                         'total_students': number_of_students}

            self.create_email_notification(user_id=teacher.user_id.id, message=None, email=teacher.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=enrolled_course.id,
                                           template_parameters=email_template_parameters,
                                           status='new')

        return True

    def create_bulk_buy_failed_notification_to_admin(self, user_id, amount):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(user_id.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'bulk_buy_failed_admin'), ('channel_id', '=', 'sms')])

            message = notification_template.message_body % (str(amount))

            sms_obj = self.env['login.otp']
            self.create_sms_notification(user_id.id, message, user_id.login, 'new')
            return True

    def create_bulk_buy_notification_to_student(self, enrolled_course):
        student = enrolled_course.student_id
        school = enrolled_course.school_id

        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if student.email and student.email_verified:
            email_notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'bulk_buy_students'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': student.email, 'name': student.name}
            self.create_email_notification(user_id=student.user_id.id, message=None, email=student.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=enrolled_course.id,
                                           template_parameters=email_template_parameters,
                                           status='new')
        else:
            if self.validate_mobile_number(student.login):
                notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'bulk_buy_students'), ('channel_id', '=', 'sms')])

                if len(enrolled_course.name) > 30:
                    first_30_characters = enrolled_course.name[0:30]
                    message = notification_template.message_body % (school.name, first_30_characters)
                else:
                    message = notification_template.message_body % (school.name, enrolled_course.name)

                self.create_sms_notification(student.user_id.id, message, student.login, 'new')

        # Send FCM notification to the students device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'bulk_buy_students'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % enrolled_course.name

        self.create_fcm_notification(student.user_id.id, notification_template.message_title, message, 'new')

        return True

    def create_course_buy_student_success_notification(self, enrolled_course, total_amount, is_b2b_course):
        student = enrolled_course.student_id
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(student.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'course_buy_student_success'), ('channel_id', '=', 'sms')])

            if len(enrolled_course.name) > 30:
                first_30_characters = enrolled_course.name[0:30]
                """ message = notification_template.message_body % (
                    student.name, str(total_amount), first_30_characters) """
                
                message = notification_template.message_body % (
                    str(total_amount), first_30_characters)
            else:
                message = notification_template.message_body % (
                    student.name, str(total_amount), enrolled_course.name)

            self.create_sms_notification(student.user_id.id, message, student.login, 'new')

        # Send FCM notification to the student device
        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'course_buy_student'), ('channel_id', '=', 'notification')])

        message = notification_template.message_body % enrolled_course.name

        self.create_fcm_notification(student.user_id.id, notification_template.message_title, message, 'new')

        if student.email and student.email_verified:
            # Send email notification to the student email id
            if is_b2b_course:
                email_notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'b2b_course_buy_student'), ('channel_id', '=', 'email')])
            else:
                email_notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'course_buy_student'), ('channel_id', '=', 'email')])

            email_template_parameters = {'email_to': student.email, 'name': student.name, 'total_amount': total_amount}

            self.create_email_notification(user_id=student.user_id.id, message=None, email=student.email,
                                           template_id=email_notification_template.id,
                                           email_template_res_id=enrolled_course.id,
                                           template_parameters=email_template_parameters,
                                           status='new')

        return True

    def create_course_buy_student_failed_notification(self, user_id, amount):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if self.validate_mobile_number(user_id.login):
            notification_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'course_buy_student_fail'), ('channel_id', '=', 'sms')])

            message = notification_template.message_body % (str(amount))

            sms_obj = self.env['login.otp']
            self.create_sms_notification(user_id.id, message, user_id.login, 'new')
            return True

    def create_sms_notification(self, user_id, message, mobile_number, status):
        sms_ref = uuid4().hex
        sms_ref = sms_ref[0:10]

        user_vals = {'to_user': user_id, 'message': message, 'phone_number': mobile_number,
                     'message_reference': sms_ref, 'channel_id': 'sms', 'status': status}
        self.create(user_vals)
        self.env.cr.commit()
        return True

    def create_fcm_notification(self, user_id, title, message, status):
        notification_ref = uuid4().hex
        notification_ref = notification_ref[0:10]

        user_vals = {'to_user': user_id, 'message_title': title, 'message': message,
                     'message_reference': notification_ref,
                     'channel_id': 'notification', 'status': status}
        self.create(user_vals)
        self.env.cr.commit()
        return True

    def create_email_notification(self, user_id, message, email, template_id, email_template_res_id,
                                  template_parameters, status):
        email_ref = uuid4().hex
        email_ref = email_ref[0:10]

        user_vals = {'to_user': user_id, 'message': message, 'message_reference': email_ref, 'channel_id': 'email',
                     'email': email, 'template_id': template_id, 'email_template_res_id': email_template_res_id,
                     'template_parameters': str(template_parameters), 'status': status}
        self.create(user_vals)
        self.env.cr.commit()
        return True

    def send_notifications(self):
        notifications_objs = self.search(
            [('status', 'in', ['new', 'failed']), ('retry_counts', '>', 0)])
        pass #SUBODH
        if notifications_objs:
            for notifications_obj in notifications_objs:
                if notifications_obj.retry_counts > 0:
                    channel_id = notifications_obj.channel_id
                    if channel_id == 'sms':
                        sms_obj = self.env['login.otp']
                        sms_response = sms_obj.send_sms(
                            {"mobile": notifications_obj.phone_number, "message": notifications_obj.message})
                        notifications_obj.notification_response = sms_response
                        if sms_response:
                            notifications_obj.status = 'success'
                            super().write(notifications_obj)
                            self.env.cr.commit()
                        else:
                            notifications_obj.retry_counts = notifications_obj.retry_counts - 1
                            notifications_obj.status = 'failed'
                            super().write(notifications_obj)
                            self.env.cr.commit()

                    elif channel_id == 'email':
                        email_template = notifications_obj.template_id.email_template_id
                        email_template_parameters = None
                        if notifications_obj.template_parameters:
                            email_template_parameters = ast.literal_eval(notifications_obj.template_parameters)

                        email_service_obj = self.env['simulab.email']
                        email_response = email_service_obj.send_email(notifications_obj.email_template_res_id,
                                                                      email_template=email_template,
                                                                      email=notifications_obj.email,
                                                                      email_template_custom_parameters=email_template_parameters)
                        notifications_obj.notification_response = email_response
                        notifications_obj.status = 'success'
                        super().write(notifications_obj)
                        self.env.cr.commit()

                    elif channel_id == 'notification':
                        fcm_obj = self.env['firebase.push']
                        fcm_response = fcm_obj.send_push(notifications_obj.to_user, notifications_obj.message_title,
                                                         notifications_obj.message)
                        notifications_obj.notification_response = fcm_response
                        notifications_obj.status = 'success'
                        super().write(notifications_obj)
                        self.env.cr.commit()

    def create_periodic_mail_reminder_notifications_to_students(self):
        student_ids = self.env['student.student'].search([('active', '=', True)])
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'periodic_mail_reminder_student'), ('channel_id', '=', 'sms')])

        if student_ids:
            for student_id in student_ids:
                if not student_id.email and self.validate_mobile_number(student_id.login):
                    """  message = notification_template.message_body % (
                        student_id.name, 'Update') """
                    
                    message = notification_template.message_body % (
                        'Update')
                    self.create_sms_notification(student_id.user_id.id, message, student_id.login, 'new')
                    self.env.cr.commit()

                elif not student_id.email_verified and self.validate_mobile_number(student_id.login):
                    """ message = notification_template.message_body % (
                        student_id.name, 'Verify') """
                    
                    message = notification_template.message_body % (
                        'Verify')
                    self.create_sms_notification(student_id.user_id.id, message, student_id.login, 'new')
                    self.env.cr.commit()

    def create_periodic_mail_reminder_notifications_to_teachers(self):
        teacher_ids = self.env['school.teacher'].search([('active', '=', True)])
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'periodic_mail_reminder_admin_or_teacher'), ('channel_id', '=', 'sms')])

        if teacher_ids:
            for teacher_id in teacher_ids:
                if not teacher_id.email and self.validate_mobile_number(teacher_id.login):
                    message = notification_template.message_body % ('Update')
                    self.create_sms_notification(teacher_id.user_id.id, message, teacher_id.login, 'new')
                    self.env.cr.commit()

                elif not teacher_id.email_verified and self.validate_mobile_number(teacher_id.login):
                    """ message = notification_template.message_body % (
                        teacher_id.name, 'Verify') """
                    
                    message = notification_template.message_body % (
                        'Verify')
                    self.create_sms_notification(teacher_id.user_id.id, message, teacher_id.login, 'new')                    
                    self.env.cr.commit()

    def create_experiment_deadline_notifications_to_students(self, student, experiments):

        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if experiments:
            if student.email and student.email_verified:
                due_experiments = []
                for exp in experiments:
                    due_experiment = {'sequence': exp.sequence, 'name': exp.experiment_id.name,
                                      'due_date': exp.planned_end_date.strftime('%d-%m-%y')}
                    due_experiments.append(due_experiment)

                email_notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'experiment_completion_reminder'), ('channel_id', '=', 'email')])

                email_template_parameters = {'email_to': student.email, 'name': student.name,
                                             'due_experiments': due_experiments}
                notification_created = self.create_email_notification(user_id=student.user_id.id, message=None,
                                                                      email=student.email,
                                                                      template_id=email_notification_template.id,
                                                                      email_template_res_id=student.id,
                                                                      template_parameters=email_template_parameters,
                                                                      status='new')
                if notification_created:
                    for exp in experiments:
                        exp.sudo().write({'reminder_email_sent': True})

            elif self.validate_mobile_number(student.login):
                notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'experiment_completion_reminder'), ('channel_id', '=', 'sms')])
                message = notification_template.message_body
                notification_created = self.create_sms_notification(student.user_id.id, message, student.login, 'new')
                if notification_created:
                    for exp in experiments:
                        exp.sudo().write({'reminder_email_sent': True})

            # FCM notification
            for exp in experiments:
                notification_template = notification_template_object.with_context(**context).search(
                    [('event_name', '=', 'experiment_completion_reminder'), ('channel_id', '=', 'notification')])
                message = notification_template.message_body % exp.name
                self.create_fcm_notification(student.user_id.id, notification_template.message_title, message, 'new')

    def create_enrolled_course_purchase_reminder(self, student, enrolled_courses):
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        notification_template = notification_template_object.with_context(**context).search(
            [('event_name', '=', 'enrolled_course_purchase_reminder'),
             ('channel_id', '=', 'notification')])

        for course in enrolled_courses:
            message = notification_template.message_body % enrolled_courses[0].name
            notification_created = self.create_fcm_notification(student.user_id.id, notification_template.message_title,
                                                                message, 'new')
            if notification_created:
                course.sudo().write({'purchase_reminder_sent': True})
