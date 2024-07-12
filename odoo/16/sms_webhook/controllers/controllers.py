# -*- coding: utf-8 -*-
from odoo import http, tools
import jwt
import requests
import logging
from odoo import http, tools
from odoo.http import request
import json  # Import the json module

SECRET_KEY = 'immersive-helpdesk-2024'  # Replace with your actual secret key

_logger = logging.getLogger(__name__)

template_type_stack = {'reopened':'reopened',
    'Ticket_Add':'record-created',
    'assigned':'assigned',
    'reassigned':'reassigned',
    'closed':'closed',
    'training_record-created':'training_record-created',
    'training_assigned': 'training_assigned',
    'training_reassigned':'training_reassigned',
    'training_closed':'training_closed',
    'training_reopened':'training_reopened',
    'installation_record-created':'installation_record-created',
    'installation_assigned':'installation_assigned',
    'installation_reassigned':'installation_reassigned',
    'installation_closed':'installation_closed',
    'installation_reopened':'installation_reopened'
}
service_desk_sms_templates = {
    'reopened': """Hello! Your ticket %s has been re-opened. Visit %s for more information. Thanks, Immersive Labz""",
    'record-created': """Hello! Your service request %s has been generated. Visit %s for more information. Thanks, Immersive Labz""",
    'assigned': """Hello! Your ticket %s has been assigned to the concerned expert. Visit %s for more information. Thanks, Immersive Labz""",
    'reassigned': """Hello! Your ticket %s has been re-assigned for quick support. Visit %s for more information. Thanks, Immersive Labz""",
    'closed': """Hello! Your issue has been resolved. Hence, closing the ticket %s. Visit %s for more information. Thanks, Immersive Labz""",
    'training_record-created': """Hello! Your %s request %s has been generated. Visit %s for more information. Thanks, Immersive Labz""",
    'training_assigned': """Hello! Your %s ticket %s has been assigned to an expert. Visit %s for more information. Thanks, Immersive Labz""",
    'training_reassigned': """Hello! Your %s ticket %s has been re-assigned for quick support. Visit %s for more information. Thanks, Immersive Labz""",
    'training_closed': """Hello! Your %s request has been addressed. Hence, closing the ticket %s. Thanks, Immersive Labz""",
    'training_reopened': """Hello! Your %s ticket %s has been re-opened. Visit %s for more information. Thanks, Immersive Labz""",
    'installation_record-created': """Hello! Your %s request %s has been generated. Visit %s for more information. Thanks, Immersive Labz""",
    'installation_assigned': """Hello! Your %s ticket %s has been assigned to an expert. Visit %s for more information. Thanks, Immersive Labz""",
    'installation_reassigned': """Hello! Your %s ticket %s has been re-assigned for quick support. Visit %s for more information. Thanks, Immersive Labz""",
    'installation_closed': """Hello! Your %s request has been addressed. Hence, closing the ticket %s. Thanks, Immersive Labz""",
    'installation_reopened': """Hello! Your %s ticket %s has been re-opened. Visit %s for more information. Thanks, Immersive Labz"""
}


class SmsWebhook(http.Controller):
    @http.route('/sms_webhook/sms_webhook', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/sms_webhook/sms_webhook/objects', auth='public')
    def list(self, **kw):
        return http.request.render('sms_webhook.listing', {
            'root': '/sms_webhook/sms_webhook',
            'objects': http.request.env['sms_webhook.sms_webhook'].search([]),
        })

    @http.route('/sms_webhook/sms_webhook/objects/<model("sms_webhook.sms_webhook"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('sms_webhook.object', {
            'object': obj
        })
    
    # SUBODH :: Customized code for webhook with zohodesk
    @http.route('/api/v1', type='json', auth='public', methods=['POST'], csrf=False)
    def sms_webhook(self, **kwargs):
        jsondata = json.loads(request.httprequest.data.decode('utf-8'))
        _logger.info(f"Json Request: {jsondata}")
        print(f"JSON Request: {json.dumps(jsondata, indent=4)}")
        token = request.httprequest.headers.get('Authorization')  
            
        if not token:
            return {"error": "Authorization header missing"}, 401

        try:
            token = token.split(" ")[1]  # Remove 'Bearer' prefix
            _logger.info(f"Token: {token}")
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            _logger.info(f"Payload: {payload}")
        except jwt.ExpiredSignatureError:
            return {"error": "Token has expired"}, 401
        except jwt.InvalidTokenError as e:
            _logger.error(f"JWT decoding error: {e}")
            return {"error": "Invalid token"}, 401
        data = jsondata
        #data = kwargs    
        # for key, value in data.items():
        #     print ("Key - {key}" , "value - {value}" )  
        #data = request.jsonrequest
        _logger.info(f"Request data: {data}")
        mobile = data.get('mobile')
        phone = data.get('phone')
        if not mobile and phone:
            mobile = phone
        eventType = data.get('eventType')       
        template = self.get_template_type_value(eventType)
        if not mobile or not template:
            return {"error": "Missing mobile or template data"}, 400
        
        if not template:
            template = 'record-created'
        ticketCategory = data.get('ticketCategory')
        if ticketCategory:
            if 'training' in ticketCategory or 'installation' in ticketCategory:
                template = 'training_record-created' if 'training' in template else 'installation_record-created'
        response_text = self.send_sms_notification(mobile, template, data)
        return {"status": "success", "response": response_text}

    def send_sms_notification(self, mobile, template, data):
        domain = 'helpdesk.immersivelabz.com'
        ticket_number = ""
        
        try:
            if mobile:
                user_id = tools.config['sms_account']
                pwd = tools.config['sms_account_password']
                msg = self.get_sms_templates(template)
                if data.get('ticketNumber'):
                    ticket_number = data.get('ticketNumber')
                
                if 'training' in template or 'installation' in template:
                    request_type = 'training' if 'training' in template else 'installation'
                    if 'closed' in template:
                        message = msg % (request_type, ticket_number)
                    else:
                        message = msg % (request_type, ticket_number, domain)
                else:
                    message = msg % (ticket_number, domain)

                url = f'http://enterprise.smsgupshup.com/GatewayAPI/rest?v=1.1&userid={user_id}&password={pwd}&msg_type=text&method=sendMessage&send_to={mobile}&msg={message}&format=text&auth_scheme=plain'

                response = requests.post(url)
                _logger.info("SMS Request: %s", url)
                _logger.info("SMS Response: %s", response.text)
                return response.text
            else:
                _logger.info("No mobile number provided.")
                return "SMS Sending Failed."
        except Exception as e:
            _logger.error(e)
        return "SMS Sending Failed."

    def get_sms_templates(self, template_id):
        return service_desk_sms_templates.get(template_id, "")
    
    def get_template_type_value(self, key):
        return template_type_stack.get(key, None) 
