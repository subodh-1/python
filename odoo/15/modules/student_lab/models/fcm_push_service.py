import firebase_admin
from firebase_admin import credentials, messaging
from odoo import tools
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

cred = credentials.Certificate(tools.config['fcm_key_path']) # Use this key in config file with value as path of .json
firebase_admin.initialize_app(cred)

simulab_push_templates={}
simulab_push_templates['student_added']="Dear %s your profile has been added on Simulab by %. Please login using mobile no %s to access your practicals."
simulab_push_templates['student_enrolled']="Dear %s, your enrolment for the simulab practical course \"%s\" was successful. To access it.  Tap to view practicals."
simulab_push_templates['teacher_added']="Dear %s your profile has been added on Simulab by %. Please login on Simulab Admin App or on simulab.com using your mobile no %s. to manage students, classes & more."

class FirebasePushNotifications(models.Model):

    _name = 'firebase.push'
    _description = 'Firebase Push'
    _rec_name = "message"


    name = fields.Char(string="Title")
    from_user = fields.Many2one('res.users', "From User")
    from_user_id=fields.Char(string="From Mobile", related="from_user.login")

    to_user = fields.Many2one('res.users', "To User")
    to_user_id=fields.Char(string="To Mobile", related="to_user.login")

    message=fields.Char(string="Message")
    payload=fields.Char(string="Payload")
    create_date = fields.Datetime(string="Notification Date")
    write_date = fields.Datetime(string="Update Date")

    app_name = fields.Selection([
        ('com_simulab_admin', 'Android Simulab Admin'),
        ('com_simulab_student', 'Android Simulab Student'),
    ], string="Simulab App")

    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('not_delivered', 'Not Delivered'),
    ], string="Status")

    api_status=fields.Char(string="API Status")

    def action_send_notification(self):
        res = self.send_push(self.to_user, self.name, self.message)
        self.write({'api_status':res, 'from_user':self.env.user.id})
        return True

    def send_push(self, user_id,title, msg, dataObject=None):
        device_details = self.env['login.otp'].search([('user_id','=',user_id.id)])
        if device_details:
            registration_token = device_details[0].device_id
            if not registration_token:
                return "device is not registered"
            return self.send_push_notification(title, msg, [registration_token], dataObject)
        _logger.info('device not registered for user %s'%user_id.name)
        return "device is not registered"

    def send_push_notification(self, title, msg, registration_token, dataObject=None):
        # See documentation on defining a message payload.
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=msg
            ),
            data=dataObject,
            tokens=registration_token,
        )

        # Send a message to the device corresponding to the provided
        # registration token.

        response = messaging.send_multicast(message)
        # Response is a message ID string.
        _logger.info('Successfully sent message:', response)
        return response

    def get_fcm_templates(self, template_id):
        return simulab_push_templates[template_id]

    #tokens = ["cQ3roEoOTZ6ZcFORNrc1Yi:APA91bFnqbg0zQKu0cPcMaMuRsrokvEHYvVCyABXJJ0Wi5X1H-JMUMbhjUd_d9FZ55s0EdoJ9zS5TmkttYJ_CoiKvk-74hRIsSO013OO-L_t7jlDNfpRwyEarq1fWJK2XtaXjatIV3_-"]
    #sendPush("Hi", "This is my next msg", tokens)


