# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
import random
from odoo.http import request
from uuid import uuid4

import logging

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError, ValidationError
import re

EMAIL_TEMPLATES = {'student.student': 'simulab.email_template_student_email_verification',
                   'school.teacher': 'simulab.email_template_teacher_email_verification'}

EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")


class SimulabEmailService(models.Model):
    _name = 'simulab.email'
    _description = 'Simulab Email Service'
    _rec_name = 'name'

    def send_verification_email(self, vals={}):
        object_model = self
        reset_password = object_model._name == 'simulab.email'
        request.simulab_rest_api = True
        if not self.email and not vals.get('email', False):
            if request.simulab_rest_api:
                return {"message": "Invalid email-id. Please enter correct email-id!",
                        "http_response": 401}
            raise ValidationError(_("Invalid email-id. Please enter correct email-id!"))

        email_otp = random.randint(1000, 9999)

        user_id = object_model.user_id
        if not user_id:
            user = object_model.env['res.users'].search([('login', '=', vals['email'])])
            if user:
                user_id = user[0]

        email = object_model.email or vals.get('email', False)
        name = object_model.name or vals.get('name', "")

        if not self.id:
            otp_obj = self.env['login.otp'].sudo()
            user_otp = otp_obj.search([('login', '=', email)])
            email_ref = uuid4().hex
            email_ref = 'email-' + email_ref[0:6]

            if user_otp:
                user_otp = user_otp[0]
                user_otp.sudo().write({'name': name, 'login': email, 'otp': email_otp, 'user_id': user_id,
                                       'sms_ref': email_ref})
            else:
                user_otp = otp_obj.create(
                    {'name': name, 'login': email, 'otp': email_otp, 'user_id': user_id.id,
                     'sms_ref': email_ref})

            vals['id'] = user_otp.id
        else:
            super().write({'email_otp': email_otp, 'user_id': user_id.id})

        if user_id:
            teacher = self.env['school.teacher'].search([('user_id', '=', user_id.id)])
            if not teacher:
                student = self.env['student.student'].search([('user_id', '=', user_id.id)])
                if student:
                    vals['simulab_user'] = 'student'
                    vals['student_ids'] = [s.id for s in student]
                    object_model = student[0]
            else:
                vals['simulab_user'] = 'teacher'
                vals['teacher_id'] = teacher.id
                object_model = teacher[0]

            email = object_model.email or vals.get('email', False)
            name = object_model.name or vals.get('name', "")

        self.emailvalidation(email)
        notification_template_object = self.env['notification.template']
        context = {}
        context.update(self.env.context)

        if user_id:
            simulab_user = user_id.simulab_user
            vals['user_id'] = user_id.id

            if simulab_user == 'school_admin':

                if reset_password:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'pass_reset_otp_admin'), ('channel_id', '=', 'email')])
                else:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'admin_verify_email'), ('channel_id', '=', 'email')])

                email_template_parameters = {'email_to': email, 'name': name, 'otp': email_otp}
                email_template.email_template_id['email_to'] = email
                email_template.email_template_id.with_context(email_template_parameters).send_mail(object_model.id,
                                                                                                   email_values=None,
                                                                                                   force_send=True)
            elif simulab_user == 'teacher':

                if reset_password:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'pass_reset_otp_teacher'), ('channel_id', '=', 'email')])
                else:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'teacher_verify_email'), ('channel_id', '=', 'email')])

                email_template_parameters = {'email_to': email, 'name': name, 'otp': email_otp}
                email_template.email_template_id['email_to'] = email
                email_template.email_template_id.with_context(email_template_parameters).send_mail(object_model.id,
                                                                                                   email_values=None,
                                                                                                   force_send=True)
            elif simulab_user == 'student':

                if reset_password:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'pass_reset_otp_student'), ('channel_id', '=', 'email')])
                else:
                    email_template = notification_template_object.with_context(**context).search(
                        [('event_name', '=', 'student_verify_email'), ('channel_id', '=', 'email')])

                email_template_parameters = {'email_to': email, 'name': name, 'otp': email_otp}
                email_template.email_template_id['email_to'] = email
                email_template.email_template_id.with_context(email_template_parameters).send_mail(object_model.id,
                                                                                                   email_values=None,
                                                                                                   force_send=True)
        else:
            email_template = notification_template_object.with_context(**context).search(
                [('event_name', '=', 'send_email_otp'), ('channel_id', '=', 'email')])
            email_template_parameters = {'email_to': email, 'name': name, 'otp': email_otp}
            email_template.email_template_id['email_to'] = email
            email_template.email_template_id.with_context(email_template_parameters).send_mail(object_model.id,
                                                                                               email_values=None,
                                                                                               force_send=True)

        v = self.post_message("OTP sent on your email-id, please use email OTP to verify your email-id")
        vals['email_otp'] = email_otp
        vals.update(v)

        _logger.info(vals)

        return vals

    def send_email(self, res_id, email_template, email, email_template_custom_parameters):
        if not email:
            if request.simulab_rest_api:
                return {"message": "Invalid email-id. Please enter correct email-id!",
                        "http_response": 401}
            raise ValidationError(_("Invalid email-id. Please enter correct email-id!"))

        self.emailvalidation(email)

        email_template['email_to'] = email
        if email_template_custom_parameters:
            email_template.with_context(email_template_custom_parameters).send_mail(res_id, email_values=None,
                                                                                    force_send=True)

        else:
            email_template.send_mail(res_id, email_values=None, force_send=True)

        _logger.info("Email sent on your email-id.")

        return

    def verify_email_otp(self, user_otp=False):
        user_otp = (user_otp and user_otp['user_otp']) or self.user_email_otp
        if self.email_otp == str(user_otp):
            super().write({'email_verified': 1})
            message = "Email verification successful."
            http_status = 200
            notification_obj = self.env['simulab.notification']
            notification_obj.email_verified_notification(self.id, self.user_id, self.email, self.name)
        else:
            super().write({'user_email_otp': False})
            message = "OTP sent on email and entered OTP do not match, please try again.."
            http_status = 401

        return self.post_message(message, http_status)

    def post_message(self, message, http_status=200):
        if request.simulab_rest_api:
            return {"message": message,
                    "http_status": http_status}

        view = self.env.ref('sh_message.sh_message_wizard')
        context = dict(self._context or {})
        context['message'] = message
        return {
            'name': 'Email OTP Verification',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'context': context,
            'target': 'new',
        }

    def emailvalidation(self, email):
        """Check valid email."""
        if email:
            email_regex = re.compile(EM)
            if not email_regex.match(email):
                raise ValidationError(_("Invalid email-id. Please enter correct email-id!"))

    def write(self, vals):
        if vals.get('email', False):
            new_email = vals.get('email').strip()
            if new_email != self.email:
                vals['email_verified'] = False
                vals['user_email_otp'] = False
                vals['email_otp'] = False
        res = super().write(vals)
        return res

    name = fields.Char('Name', help='email from name')
    email = fields.Char('E-Mail', help='Enter student email')
    email_verified = fields.Boolean('Email Verified')
    user_email_otp = fields.Char('Email OTP')
    email_otp = fields.Char('Sent Email OTP')
    user_id = fields.Many2one('res.users')
