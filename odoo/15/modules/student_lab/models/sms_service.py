# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import random
from uuid import uuid4
import requests

from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl

import logging

_logger = logging.getLogger(__name__)
from odoo import tools

simulab_sms_templates = {}
simulab_sms_templates[
    'login_otp'] = "Please use OTP %s for mobile verification for the SimuLab account %s valid for 10 min. Do not share this with anyone.Reference no %s Immersivevision technology private Limited"
simulab_sms_templates[
    'student_added'] = "Dear %s, you were enrolled for course %s by %s, Please use mobile no %s to perform your science experiments at %s. Ref No %s. Immersivevision Technology Private Limited."
simulab_sms_templates[
    'student_enrolled'] = "Dear %s, your enrolment for the simulab practical course \"%s\" was successful. To access it, please login on student Simulab App using your mobile no %s. Immersivevision technology private Limited"
simulab_sms_templates[
    'teacher_added'] = "Dear %s, Your account got activated successfully for %s. Please use mobile no %s to access your account at %s. Ref No. %s. Immersivevision Technology Pvt Ltd."


class CustomAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,maxsize=maxsize,block=block,ssl_version=ssl.PROTOCOL_TLSv1_2)

class UserOTP(models.Model):
    _name = 'login.otp'
    _description = 'OTP handling for user login'
    _rec_name = 'mobile'
    _order = 'write_date desc'

    name = fields.Char(string="Name")
    mobile = fields.Char(string="Mobile")
    otp = fields.Char(string="OTP")
    login = fields.Char(string="login")
    email = fields.Char(string="email")
    sms_ref = fields.Char(string="SMS Ref")
    user_id = fields.Many2one("res.users", string="Registered User")
    create_date = fields.Datetime(string="Register Date")
    write_date = fields.Datetime(string="Update Date")
    opt_in = fields.Boolean(default=True, string="Opt-In", help="Checked opt-in, Uncheck opt-out")
    device_id = fields.Text(string="Device Id")
    device_details = fields.Text(string="Device Details")
    device_type = fields.Char(string="Device Type")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def update_device_details(self, **args):
        if not args:
            return {'http_code': 200, 'message': "Nothing to save."}
        mobile = args.get('mobile', False)
        if not mobile:
            return {'http_code': 200, 'message': "Nothing to save."}

        res = self.search([('mobile', '=', mobile)])
        if not res:
            return {'http_code': 200, 'message': "Mobile no found/registered"}

        result = res.write({'device_id': args.get('device_id', False),
                            'device_details': args.get('device_details', False),
                            'device_type': args.get('device_type', False)})
        return {'http_code': 200, 'message': "Saved", 'result': result, "id": res[0].id}

    def get_sms_templates(self, template_id):
        return simulab_sms_templates[template_id]

    def send_sms(self, vals):

        try:
            mobile = vals.get("mobile", False)
            message = vals.get("message", False)
            user_id = tools.config['sms_account']
            pwd = tools.config['sms_account_password']
            url = 'http://enterprise.smsgupshup.com/GatewayAPI/rest?v=1.1&userid=' + user_id + '&password=' + pwd + '&msg_type=text&method=sendMessage&send_to=' + mobile + '&msg=' + message + '&format=text&auth_scheme=plain'

            s = requests.Session()
            s.mount('https://', CustomAdapter())
            response = s.post(url, data={})
            _logger.info(response.text)
            return response.text
        except Exception as e:
            _logger.info(e)
            _logger.error("Could not send sms: " + str(vals))

        return ""

    @api.model
    def send_otp_on_student_added(self, student):
        school = student.school_id
        if not school:
            return True

        app = 'dev.immersivelabz.com'
        sms_ref = uuid4().hex
        sms_ref = sms_ref[0:10]
        message = simulab_sms_templates['student_added'] % (
            student.name, "12 B", school.name, student.login, app, sms_ref)
        self.send_sms({"mobile": student.login, "message": message})
        return True

    @api.model
    def send_otp_on_teacher_added(self, teacher):
        school = teacher.school_id
        if not school:
            return True

        app = 'dev.immersivelabz.com'
        sms_ref = uuid4().hex
        sms_ref = sms_ref[0:10]
        message = simulab_sms_templates['teacher_added'] % (teacher.name, school.name, teacher.login, app, sms_ref)
        self.send_sms({"mobile": teacher.login, "message": message})
        return True

    @api.model
    def send_otp(self, name, mobile):
        response = {}
        otp_obj = self.env['login.otp'].sudo()
        user_otp = otp_obj.search([('mobile', '=', mobile)])
        otp = random.randint(1000, 9999)

        user_id = self.env['res.users'].sudo().search([('login', '=', str(mobile))])
        if not user_id:
            user_id = False
        else:
            user_id = user_id.id

        sms_ref = uuid4().hex
        sms_ref = sms_ref[0:10]

        if user_otp:
            user_otp.sudo().write({'name': name, 'mobile': mobile, 'otp': otp, 'user_id': user_id,
                                   'sms_ref': sms_ref})
        else:
            user_otp = super().sudo().create(
                {'name': name, 'mobile': mobile, 'otp': otp, 'user_id': user_id,
                 'sms_ref': sms_ref})

        account_no = 'IMM-SIMU' + str(user_otp.id)
        message = simulab_sms_templates['login_otp'] % (str(otp), account_no, sms_ref)
        res = self.send_sms({"mobile": mobile, "message": message})

        response['id'] = user_otp.id
        if name:
            response['name'] = name
        response['mobile'] = mobile

        if res:
            response['http_status'] = 200
            response['message'] = "OTP sent to mobile %s and is valid for 30 mins." % (str(mobile))
        else:
            response['http_status'] = 500
            response['message'] = 'Problem in sending OTP, please try again.'
        response['otp'] = otp

        if name:
            _logger.info("otp for %s mobile %s is %d" % (name, str(mobile), otp))
        else:
            _logger.info("otp for mobile %s is %d" % (str(mobile), otp))
        return response

    @api.model
    def verify_otp(self, vals={}):
        name = vals.get("name", False)
        login_type = vals.get("login_type", False)
        mobile = vals.get("mobile", False)
        login = vals.get("login", False)
        school_id = vals.get("school_id", False)
        otp = vals.get("otp", False)
        password = vals.get("password", self._generate_auth_code())

        response = {}
        response['http_status'] = 200
        response['code'] = 200
        response['otp'] = otp

        otp_search = [('mobile', '=', mobile)] if mobile else [('login', '=', login)]
        user_otp = self.env['login.otp'].sudo().search(otp_search)
        if not user_otp or user_otp[0].otp != str(otp):
            response['http_status'] = 404
            response['code'] = 404
            response['message'] = "Invalid otp, please try again."
            return response

        if user_otp:
            user_search = [('login', '=', mobile)] if mobile else [('login', '=', login)]
            user_id = self.env['res.users'].sudo().search(user_search)
            vals = {}

            if mobile:
                response['mobile'] = str(mobile)

            response['login'] = login or str(mobile)

            if not name:
                if user_id:
                    response['name'] = user_id.name
                    response['login'] = login or str(mobile)
                    response['auth_token'] = password
                    response['message'] = "Registered user"
                    user_id.sudo().write({"password": password})
                response['http_status'] = 200
                response['code'] = 200
                return response

            if not user_id:
                return self.register_user(
                    {"name": name, "login_type": login_type, "login": login, "password": password, "mobile": mobile,
                     "otp": otp,
                     "school_id": school_id}, user_otp)

            vals['name'] = name
            response['auth_token'] = password
            response['login'] = login or mobile

            vals['password'] = password
            user_id.sudo().write(vals)
            message = "Registered user"
            response["message"] = message
            user_otp.write({'user_id': user_id.id})

            response['user_id'] = user_id.id
            if login_type == 'student':
                user_search = ('mobile', '=', mobile) if mobile else ('login', '=', login)
                student_id = self.env['student.student'].sudo().search(
                    ['|', user_search, ('user_id', '=', user_id.id)])
                if not student_id:
                    vals = {}
                    vals['name'] = name
                    vals['user_id'] = user_id.id
                    vals['mobile'] = mobile
                    self.env['student.student'].sudo().create(vals)
                else:
                    student_id.sudo().write({'user_id': user_id.id, 'mobile': mobile, 'name': name})

                    if vals.get('password', False):
                        notification_template_object = self.env['notification.template']
                        context = {}
                        context.update(self.env.context)
                        email_template = notification_template_object.with_context(**context).search(
                            [('event_name', '=', 'reset_pass_confirmation_student'), ('channel_id', '=', 'email')])
                        email_template_parameters = {'email_to': student_id.email, 'name': name}
                        email_template.email_template_id['email_to'] = student_id.email
                        email_template.email_template_id.with_context(email_template_parameters).send_mail(
                            student_id.id,
                            email_values=None,
                            force_send=True)

            else:
                user_search = ('mobile', '=', mobile) if mobile else ('login', '=', login)
                teacher_id = self.env['school.teacher'].sudo().search(
                    ['|', user_search, ('user_id', '=', user_id.id)])
                if not teacher_id:
                    vals = {}
                    vals['name'] = name
                    vals['mobile'] = mobile
                    self.env['school.teacher'].sudo().create(vals)
                else:
                    teacher_id.sudo().write({'user_id': user_id.id, 'mobile': mobile, 'name': name})

                    if vals.get('password', False):
                        notification_template_object = self.env['notification.template']
                        context = {}
                        context.update(self.env.context)
                        simulab_user = user_id.simulab_user
                        email_template = None

                        if simulab_user == 'school_admin':
                            email_template = notification_template_object.with_context(**context).search(
                                [('event_name', '=', 'reset_pass_confirmation_admin'), ('channel_id', '=', 'email')])
                        elif simulab_user == 'teacher':
                            email_template = notification_template_object.with_context(**context).search(
                                [('event_name', '=', 'reset_pass_confirmation_teacher'), ('channel_id', '=', 'email')])

                        if email_template:
                            email_template_parameters = {'email_to': teacher_id.email, 'name': name}
                            email_template.email_template_id['email_to'] = teacher_id.email
                            email_template.email_template_id.with_context(email_template_parameters).send_mail(
                                teacher_id.id,
                                email_values=None,
                                force_send=True)

            response['http_status'] = 200
            response['code'] = 200
            response['message'] = message

        return response

    def register_user(self, data, user_otp=False):
        response = {}
        response['http_status'] = 200
        response['code'] = 200

        mobile = data.get("mobile", False)
        login = data.get("login", False)
        password = data.get("password", self._generate_auth_code())

        if not user_otp:
            otp_search = [('mobile', '=', mobile)] if mobile else [('login', '=', login)]
            user_otp = self.env['login.otp'].sudo().search(otp_search)
        if not user_otp or user_otp[0].otp != str(data["otp"]):
            response['http_status'] = 404
            response['code'] = 404
            response['message'] = "Invalid otp, please try again."
            return response

        response['auth_token'] = password
        response['login'] = login or str(data["mobile"])

        school_id = data.get('school_id', False)
        company_id = False
        if school_id:
            school = self.env['student.student'].sudo().browse(school_id)
            company_id = school.company_id

        if data.get("login_type") == 'student':
            vals = {}
            vals['name'] = data["name"]
            vals['login'] = login or str(mobile)
            vals['password'] = password
            user_id = self.env['student.student'].sudo().create_student_login(vals)
            vals = {}
            vals['name'] = data["name"]
            vals['user_id'] = user_id.id
            vals['mobile'] = mobile
            student_id = self.env['student.student'].sudo().create(vals)
            response["message"] = "New student login added"
            response["student_ids"] = [student_id.id]
        else:
            vals = {}
            vals['name'] = data["name"]
            vals['login'] = login or str(mobile)
            vals['password'] = password
            if company_id:
                vals['company_id'] = company_id.id

            user_id = self.env['school.teacher'].sudo().create_teacher_login(False, vals)
            vals = {}
            vals['name'] = data["name"]
            vals['user_id'] = user_id.id
            vals['mobile'] = mobile
            if company_id:
                vals['company_id'] = company_id.id
            vals['school_id'] = school_id
            teacher_id = self.env['school.teacher'].sudo().create(vals)
            response["message"] = "New Teacher login added"
            response["teacher_id"] = teacher_id.id
        response['user_id'] = user_id.id

        user_otp.write({'user_id': user_id.id})
        return response

    def _generate_auth_code(self):
        return uuid4().hex
